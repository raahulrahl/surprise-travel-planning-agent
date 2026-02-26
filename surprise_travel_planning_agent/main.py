# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""surprise-travel-planning-agent - A Bindu Agent for Surprise Trip Planning."""

import argparse
import asyncio
import json
import os
import re
import traceback
from pathlib import Path
from textwrap import dedent
from typing import Any

from bindu.penguin.bindufy import bindufy
from crewai import Agent, Crew, Process, Task
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Error constants
ERROR_NO_API_KEY = "No API key available"
ERROR_CREW_NOT_INITIALIZED = "Crew not initialized"

# Global variables
crew: Crew | None = None
llm_instance: Any = None  # Global reference to the LLM for parameter extraction
_initialized = False
_init_lock = asyncio.Lock()


def validate_and_correct_itinerary(itinerary: str, requested_days: int, destination: str) -> str:
    """Validate that itinerary has exactly requested days, correct if necessary."""
    if not itinerary:
        return f"ERROR: Could not generate itinerary for {destination}"

    # Count days in itinerary
    day_pattern = re.compile(r"Day\s+\d+:", re.IGNORECASE)
    days_found = list(day_pattern.finditer(itinerary))

    if not days_found:
        # No days found, return error
        return f"ERROR: Itinerary format incorrect for {destination}"

    num_days_found = len(days_found)

    if num_days_found == requested_days:
        return itinerary

    print(f"⚠️  CRITICAL ERROR: Itinerary has {num_days_found} days but requested {requested_days}")
    print(f"⚠️  Attempting to reconstruct itinerary for {requested_days} days...")

    # If we have too many days, truncate
    if num_days_found > requested_days:
        end_position = days_found[requested_days].start() if requested_days < num_days_found else len(itinerary)
        truncated = itinerary[:end_position].strip()

        # Remove any partial days or incomplete sections
        lines = truncated.split("\n")
        cleaned_lines = []
        in_day_section = True

        for line in lines:
            if re.match(r"Day\s+\d+:", line, re.IGNORECASE):
                # FIX: Explicitly check for match to satisfy type checker
                match = re.search(r"\d+", line)
                if match:
                    day_num = int(match.group())
                    if day_num <= requested_days:
                        cleaned_lines.append(line)
                        in_day_section = True
                    else:
                        in_day_section = False
            elif in_day_section:
                cleaned_lines.append(line)

        corrected = "\n".join(cleaned_lines).strip()

        # Add correction note
        corrected += (
            f"\n\n[NOTE: This itinerary has been corrected to show exactly {requested_days} days as requested.]"
        )
        return corrected

    # If we have too few days, we need to regenerate
    return f"ERROR: Could only generate {num_days_found} days for {requested_days}-day trip to {destination}"


def extract_travel_parameters_with_llm(input_text: str) -> dict:
    """
    Extract travel parameters using the LLM.

    This handles typos (budjet->budget) and semantic understanding (backpacking->adventure).
    """
    global llm_instance

    if not llm_instance:
        print("⚠️ LLM not initialized, falling back to defaults")
        return {
            "destination": "Unknown Destination",
            "age": "Not specified",
            "trip_duration": "3",
            "duration_text": "3 days",
            "trip_context": "general",
            "hotel_location": "Centrally located hotel",
            "flight_information": "Flight details",
            "origin": "",
        }

    prompt = dedent(f"""
    You are an AI Travel Assistant. Analyze the user's input and extract structured travel details.

    USER INPUT: "{input_text}"

    INSTRUCTIONS:
    1. Fix any typos in the input (e.g., "budjet" -> "budget", "srilanka" -> "Sri Lanka").
    2. Extract the Destination (City/Country).
    3. Extract Duration in NUMBER OF DAYS.
       - If they say "weekend", that is 2 days.
       - If they say "a week", that is 7 days.
       - If they say "fortnight", that is 14 days.
       - If not specified, default to 3.
    4. Infer the Context/Trip Type based on keywords:
       - "honeymoon", "anniversary", "couple" -> "Romantic Getaway"
       - "kids", "family", "children" -> "Family Vacation"
       - "backpack", "hike", "trek", "adventure" -> "Adventure Trip"
       - "budget", "cheap", "saving", "economy", "budjet" -> "Budget Travel"
       - "luxury", "5 star", "expensive" -> "Luxury Vacation"
    5. Suggest a hotel vibe based on the context (e.g., "Budget hostel" or "Luxury resort").

    OUTPUT FORMAT (JSON ONLY):
    {{
        "destination": "Corrected Destination Name",
        "trip_duration_numeric": "integer as string (e.g. '5')",
        "trip_duration_text": "readable string (e.g. '5 days')",
        "trip_context": "inferred context",
        "age": "inferred age or 'suitable for all ages'",
        "hotel_location": "suggested accommodation type",
        "origin": "origin city or empty string"
    }}

    Return ONLY the raw JSON string. No markdown formatting.
    """)

    try:
        # We use a temporary agent to process this extraction to ensure clean output
        extractor_agent = Agent(
            role="Travel Data Extractor",
            goal="Extract clean JSON data from user input, fixing typos.",
            backstory="You are a data processing expert who cleans messy text inputs.",
            llm=llm_instance,
            verbose=False,
        )

        # Determine how to call the LLM based on available methods
        # CrewAI agents don't have a direct 'predict' method in all versions,
        # so we run a mini-task which is safer
        extraction_task = Task(description=prompt, expected_output="Valid JSON string", agent=extractor_agent)

        # Execute extraction
        crew_mini = Crew(agents=[extractor_agent], tasks=[extraction_task], verbose=False)
        result = str(crew_mini.kickoff())

        # Clean up result (remove markdown code blocks if present)
        json_str = result.replace("```json", "").replace("```", "").strip()

        params = json.loads(json_str)

        # Construct the final params dictionary expected by the main crew
        final_params = {
            "destination": params.get("destination", "Destination"),
            "trip_duration": params.get("trip_duration_numeric", "3"),
            "duration_text": params.get("trip_duration_text", "3 days"),
            "trip_context": params.get("trip_context", "general trip"),
            "age": params.get("age", "Not specified - suitable for all ages"),
            "hotel_location": params.get("hotel_location", "Centrally located hotel"),
            "origin": params.get("origin", ""),
            "flight_information": "",
        }

        # Construct flight info
        if final_params["origin"]:
            final_params["flight_information"] = (
                f"Flight from {final_params['origin']} to {final_params['destination']}"
            )
        else:
            final_params["flight_information"] = f"Flight to {final_params['destination']}"

        print(f"🔍 LLM Extraction Result: {final_params}")

    except Exception as e:
        print(f"❌ LLM Extraction failed: {e}. Falling back to defaults.")
        # Minimal fallback
        return {
            "destination": "Unknown",
            "trip_duration": "3",
            "duration_text": "3 days",
            "trip_context": "General Trip",
            "age": "Suitable for all ages",
            "hotel_location": "Central Hotel",
            "flight_information": "Flight",
            "origin": "",
        }
    else:
        return final_params


def load_config() -> dict:
    """Load agent configuration from project root."""
    possible_paths = [
        Path(__file__).parent.parent / "agent_config.json",
        Path(__file__).parent / "agent_config.json",
        Path.cwd() / "agent_config.json",
    ]

    for config_path in possible_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Error reading {config_path}: {type(e).__name__}")
                continue

    print("⚠️  No agent_config.json found, using default configuration")
    return {
        "name": "surprise-travel-planning",
        "description": "AI surprise trip planning agent for personalized travel itineraries",
        "version": "1.0.0",
        "deployment": {
            "url": "http://127.0.0.1:3773",
            "expose": True,
            "protocol_version": "1.0.0",
            "proxy_urls": ["127.0.0.1"],
            "cors_origins": ["*"],
        },
        "environment_variables": [
            {"key": "OPENAI_API_KEY", "description": "OpenAI API key for LLM calls", "required": False},
            {"key": "OPENROUTER_API_KEY", "description": "OpenRouter API key for LLM calls", "required": True},
            {"key": "MEM0_API_KEY", "description": "Mem0 API key for memory operations", "required": False},
        ],
    }


async def initialize_crew() -> None:
    """Initialize the surprise travel planning crew with proper model and agents."""
    global crew, llm_instance

    openai_api_key = os.getenv("OPENAI_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    model_name = os.getenv("MODEL_NAME", "openai/gpt-4o")

    from crewai import LLM

    try:
        if openai_api_key and not openrouter_api_key:
            llm_instance = LLM(
                model="gpt-4o",
                api_key=openai_api_key,
                temperature=0.7,
            )
            print("✅ Using OpenAI GPT-4o directly")

        elif openrouter_api_key:
            llm_instance = LLM(
                model=model_name,
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.7,
            )
            print(f"✅ Using OpenRouter via CrewAI LLM: {model_name}")

            if not os.getenv("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = openrouter_api_key

        else:
            error_msg = (
                "No API key provided. Set OPENAI_API_KEY or OPENROUTER_API_KEY environment variable.\n"
                "For OpenRouter: https://openrouter.ai/keys\n"
                "For OpenAI: https://platform.openai.com/api-keys"
            )
            raise ValueError(error_msg)  # noqa: TRY301

    except Exception as e:
        print(f"❌ LLM initialization error: {e}")
        print("🔄 Trying alternative configuration...")

        try:
            # SIMPLIFIED: Just use CrewAI LLM directly
            if openrouter_api_key:
                from crewai import LLM as CrewAI_LLM

                llm_instance = CrewAI_LLM(
                    model="gpt-4o",
                    api_key=openrouter_api_key,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0.7,
                )
                print("✅ Using OpenRouter via CrewAI LLM (fallback)")
            else:
                raise ValueError(ERROR_NO_API_KEY)  # noqa: TRY301

        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")

            class MockLLM:
                def __call__(self, *args, **kwargs):
                    return "Mock response for testing"

            llm_instance = MockLLM()
            print("⚠️ Using mock LLM for testing only")

    # Define Agents for surprise travel planning
    activity_planner = Agent(
        role="Personalized Activity Planner",
        goal="""You create activity lists that EXACTLY match the specified trip duration.
        If the trip is 5 days, you suggest activities for 5 days ONLY.
        If the trip is 2 days, you suggest activities for 2 days ONLY.
        You NEVER exceed the requested duration.""",
        backstory="""You are an expert travel planner who is meticulous about respecting trip duration constraints.
        You understand that travelers have limited time and you optimize their experience within their timeframe.
        You always count and verify that your suggestions match the exact number of days requested.""",
        llm=llm_instance,
        allow_delegation=False,
        verbose=False,
    )

    restaurant_scout = Agent(
        role="Restaurant Scout",
        goal="""You find dining options that fit within the trip duration.
        You suggest exactly enough restaurants for the specified number of days.
        You never recommend more dining experiences than can be enjoyed during the trip.""",
        backstory="""You are a food expert who understands that meals must fit within travel schedules.
        You consider the limited time of short trips and prioritize conveniently located options.
        You always match the number of meal recommendations to the trip duration.""",
        llm=llm_instance,
        allow_delegation=False,
        verbose=False,
    )

    itinerary_compiler = Agent(
        role="Itinerary Compiler",
        goal="""You create day-by-day itineraries that EXACTLY match the requested duration.
        You output ONLY the number of days specified - never more, never less.
        You verify the day count before finalizing any itinerary.""",
        backstory="""You are a master itinerary planner with an obsessive attention to detail.
        You double-check and triple-check that every itinerary has the correct number of days.
        You would never output Day 6 for a 5-day trip or stop at Day 2 for a 5-day trip.
        You count days meticulously and ensure perfect alignment with the request.""",
        llm=llm_instance,
        allow_delegation=True,
        verbose=False,
    )

    # Define Tasks - Using simple templates that will be filled at runtime
    activity_planning_task = Task(
        description="""Create a list of activities for {destination} for a {trip_duration_numeric}-day {trip_context}.

        IMPORTANT: You MUST create activities for EXACTLY {trip_duration_numeric} days.
        Count your days: Day 1, Day 2, ... up to Day {trip_duration_numeric}.
        Do NOT create activities for Day {trip_duration_numeric_plus_one} or beyond.

        Traveler details:
        - Destination: {destination}
        - Age: {age}
        - Hotel: {hotel_location}
        - Duration: {trip_duration_text}
        - Trip type: {trip_context}

        Structure your response as:
        Day 1 Activities: [list]
        Day 2 Activities: [list]
        ... continue for exactly {trip_duration_numeric} days""",
        expected_output="Activities list for exactly the specified number of days",
        agent=activity_planner,
    )

    restaurant_scouting_task = Task(
        description="""Find restaurants and dining options for {destination} for a {trip_duration_numeric}-day trip.

        IMPORTANT: You MUST suggest dining for EXACTLY {trip_duration_numeric} days.
        Provide breakfast, lunch, and dinner suggestions for each of the {trip_duration_numeric} days.
        Do NOT suggest meals for Day {trip_duration_numeric_plus_one} or beyond.

        Traveler details:
        - Destination: {destination}
        - Age: {age}
        - Hotel: {hotel_location}
        - Duration: {trip_duration_text}
        - Trip type: {trip_context}

        Structure your response as:
        Day 1 Dining: [suggestions]
        Day 2 Dining: [suggestions]
        ... continue for exactly {trip_duration_numeric} days""",
        expected_output="Dining options for exactly the specified number of days",
        agent=restaurant_scout,
    )

    itinerary_compilation_task = Task(
        description="""Compile a complete {trip_duration_numeric}-day itinerary for {destination}.

        CRITICAL REQUIREMENTS:
        1. Create EXACTLY {trip_duration_numeric} days of itinerary
        2. Number them as: Day 1, Day 2, ... Day {trip_duration_numeric}
        3. STOP at Day {trip_duration_numeric} - do NOT create Day {trip_duration_numeric_plus_one}
        4. Verify you have exactly {trip_duration_numeric} days before finalizing

        Traveler details:
        - Destination: {destination}
        - Age: {age}
        - Hotel: {hotel_location}
        - Flight: {flight_information}
        - Duration: {trip_duration_text}
        - Trip type: {trip_context}

        Structure your itinerary as:
        Day 1: [Theme]
        - Morning: [Activity]
        - Lunch: [Restaurant]
        - Afternoon: [Activity]
        - Dinner: [Restaurant]
        - Evening: [Optional activity]

        Day 2: [Theme]
        [Same structure...]

        [Continue for EXACTLY {trip_duration_numeric} days, then STOP]

        After Day {trip_duration_numeric}, add practical tips and conclusion.
        DO NOT include any text about "Day {trip_duration_numeric_plus_one}" or beyond.""",
        expected_output="Complete travel itinerary with the correct number of days",
        agent=itinerary_compiler,
    )

    # Create crew
    crew = Crew(
        agents=[activity_planner, restaurant_scout, itinerary_compiler],
        tasks=[activity_planning_task, restaurant_scouting_task, itinerary_compilation_task],
        verbose=True,
        process=Process.sequential,
        memory=False,
    )

    print("✅ Surprise Travel Planning Crew initialized")


async def run_crew(input_text: str) -> str:
    """Run the crew and get the travel itinerary."""
    global crew

    if not crew:
        raise RuntimeError(ERROR_CREW_NOT_INITIALIZED)

    try:
        print(f"✈️ Running crew with input: {input_text}")

        # Extract parameters from user input using LLM (Handles typos!)
        params = extract_travel_parameters_with_llm(input_text)

        # Get numeric duration for constraints
        try:
            trip_duration_numeric = int(params["trip_duration"])
        except (ValueError, TypeError):
            trip_duration_numeric = 3

        # Prepare inputs for crew
        inputs = {
            "destination": params["destination"],
            "age": params["age"],
            "hotel_location": params["hotel_location"],
            "flight_information": params["flight_information"],
            "trip_duration_text": params["duration_text"],
            "trip_duration_numeric": str(trip_duration_numeric),
            "trip_duration_numeric_plus_one": str(trip_duration_numeric + 1),
            "trip_context": params["trip_context"],
        }

        print(f"📋 Extracted parameters: {inputs}")
        print(f"⚠️  STRICT CONSTRAINT: Itinerary MUST be EXACTLY {trip_duration_numeric} days")

        # Run the crew
        result = await crew.kickoff_async(inputs=inputs)

        # Get the text - CrewAI returns the result directly
        itinerary = str(result)

        print(f"📊 Generated itinerary: {len(itinerary)} chars")

        # Validate and correct the itinerary
        itinerary = validate_and_correct_itinerary(itinerary, trip_duration_numeric, inputs["destination"])

    except Exception as e:
        error_msg = f"Crew execution failed: {e!s}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return f"Error generating travel itinerary: {error_msg}"
    else:
        return itinerary


async def handler(messages: list[dict[str, str]]) -> str:
    """Handle incoming agent messages."""
    global _initialized

    # Type checking for messages
    if not isinstance(messages, list):
        return "Error: Invalid input format. Messages must be a list."

    # Lazy initialization
    async with _init_lock:
        if not _initialized:
            print("🔧 Initializing Surprise Travel Planning Crew...")
            await initialize_crew()
            _initialized = True

    # Extract user input
    user_input = ""
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_input = msg.get("content", "").strip()
            break

    if not user_input:
        return "Please provide travel details. For example: 'Plan a surprise romantic getaway to Paris for 7 days' or 'Create a family vacation to Tokyo with kids'"

    print(f"✅ Processing: {user_input}")

    try:
        itinerary = await run_crew(user_input)

        if itinerary:
            print("✅ Success! Generated travel itinerary")
            return itinerary
        else:
            return "Unable to generate travel itinerary. Please try again with more specific details."

    except Exception as e:
        error_msg = f"Handler error: {e!s}"
        print(f"❌ {error_msg}")
        return f"Error processing your request: {error_msg}"


async def cleanup() -> None:
    """Clean up resources."""
    global crew
    print("🧹 Cleaning up...")
    crew = None
    print("✅ Cleanup complete")


def main() -> None:
    """Run the main entry point for the Surprise Travel Planning Agent."""
    parser = argparse.ArgumentParser(description="Bindu Surprise Travel Planning Agent")
    parser.add_argument(
        "--openai-api-key",
        type=str,
        default=os.getenv("OPENAI_API_KEY"),
        help="OpenAI API key",
    )
    parser.add_argument(
        "--openrouter-api-key",
        type=str,
        default=os.getenv("OPENROUTER_API_KEY"),
        help="OpenRouter API key",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("MODEL_NAME", "openai/gpt-4o"),
        help="Model ID",
    )
    args = parser.parse_args()

    # Set environment variables
    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
    if args.openrouter_api_key:
        os.environ["OPENROUTER_API_KEY"] = args.openrouter_api_key
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = args.openrouter_api_key
    if args.model:
        os.environ["MODEL_NAME"] = args.model

    print("🤖 Surprise Travel Planning Agent")
    print("✈️ Creates personalized surprise travel itineraries")

    config = load_config()

    try:
        print("🚀 Starting server...")
        bindufy(config, handler)
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        import sys

        sys.exit(1)
    finally:
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()

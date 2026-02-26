# Surprise Travel Planning Agent

AI-powered itinerary generation using CrewAI agents. Generates day-by-day travel plans with activity and dining suggestions from natural language input.

## Overview

Uses three CrewAI agents (Activity Planner, Restaurant Scout, Itinerary Compiler) to generate text-based travel itineraries. Extracts parameters from natural language, handles typos, and validates output matches requested duration.

**Capabilities:**
- Parameter extraction with typo correction
- Trip context inference (romantic, family, adventure, budget, luxury)
- Day-by-day itinerary generation
- Activity and dining suggestions

**Limitations:**
- No booking capabilities
- No real-time pricing
- Single destination per request
- Text output only

## Installation

```bash
git clone https://github.com/Paraschamoli/surprise-travel-planning-agent.git
cd surprise-travel-planning-agent

uv venv --python 3.12
source .venv/bin/activate

uv sync
cp .env.example .env
```

## Configuration

Edit `.env` and add API key:

```bash
OPENAI_API_KEY=your_key        # Required
# OR
OPENROUTER_API_KEY=your_key    # Alternative
MODEL_NAME=openai/gpt-4o       # Optional
```

## Usage

```bash
uv run python -m surprise_travel_planning_agent
# Available at http://localhost:3773
```

**Example requests:**
- "Plan a 7-day romantic getaway to Paris"
- "Create a family vacation to Tokyo with kids for 5 days"
- "Weekend trip to New York City"

**Output format:**
```
Day 1: [Theme]
- Morning: [Activity]
- Lunch: [Restaurant]
- Afternoon: [Activity]
- Dinner: [Restaurant]
- Evening: [Optional activity]

[Continues for requested number of days]
```

## Docker

```bash
docker-compose up --build
# Available at http://localhost:3773
```

## Project Structure

```
surprise-travel-planning-agent/
├── surprise_travel_planning_agent/
│   ├── main.py                 # Core logic
│   ├── skills/                 # Skill definitions
│   └── agent_config.json       # Agent metadata
├── tests/
├── pyproject.toml
└── Dockerfile
```

## Development

```bash
uv run pytest                              # Run tests
uv run pre-commit run --all-files          # Type checking
```

## License

MIT License - see [LICENSE](LICENSE) file.

Built with [Bindu Agent Framework](https://github.com/getbindu/bindu).

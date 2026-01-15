<p align="center">
  <img src="https://raw.githubusercontent.com/getbindu/create-bindu-agent/refs/heads/main/assets/light.svg" alt="bindu Logo" width="200">
</p>

<h1 align="center">Surprise Travel Planning Agent</h1>
<h3 align="center">AI-Powered Personalized Trip Architect</h3>

<p align="center">
  <strong>An intelligent travel agent that plans surprise trip itineraries with surgical precision. It fixes user typos, infers context (Romantic vs. Adventure), and generates strictly formatted day-by-day plans with activities and dining options.</strong>
</p>

<p align="center">
  <a href="https://github.com/Paraschamoli/surprise-travel-planning-agent/actions/workflows/main.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/Paraschamoli/surprise-travel-planning-agent/main.yml?branch=main" alt="Build Status">
  </a>
  <a href="https://github.com/Paraschamoli/surprise-travel-planning-agent/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/Paraschamoli/surprise-travel-planning-agent" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/framework-bindu-purple" alt="Built with Bindu">
</p>

---

## 📖 Overview

The **Surprise Travel Planning Agent** takes vague user requests ("budjet trip to srilanka for a week") and transforms them into detailed, professionally structured itineraries. Unlike standard chatbots, it uses a multi-agent **CrewAI** system to research activities and dining separately, then compiles them into a cohesive plan that strictly adheres to the requested duration.

**Key Capabilities:**
- 🧠 **Smart Extraction:** Uses LLM to fix typos ("budjet" -> "Budget", "itlay" -> "Italy") and understand semantic time ("fortnight" -> 14 days).
- 📅 **Strict Duration Control:** Guarantees itineraries match the *exact* number of days requested—no more, no less.
- 👥 **Context Awareness:** Automatically detects trip vibes (Romantic, Family, Adventure, Luxury) from keywords.
- 🍽️ **Dining & Activity Pairing:** Suggests restaurants conveniently located near daily activities.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- API key for OpenAI (GPT-4o) or OpenRouter

### Installation

```bash
# Clone the repository
git clone https://github.com/Paraschamoli/surprise-travel-planning-agent.git
cd surprise-travel-planning-agent

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
```

### Configuration

Edit `.env` and add your API keys (choose one provider):

| Key | Description | Required |
|-----|-------------|----------|
| `OPENAI_API_KEY` | For direct GPT-4o usage | ✅ Yes (Recommended) |
| `OPENROUTER_API_KEY` | Alternative model provider | Optional |
| `MEM0_API_KEY` | For persistent user preferences | Optional |

### Run the Agent

```bash
# Start the agent
uv run python -m surprise_travel_planning_agent

# Agent will be available at http://localhost:3773
```

---

## 💡 Usage

### Example Queries

```bash
# Basic request with typos
"Plan a 5 days budjet trip to itlay for backpacking"

# Semantic time request
"I want a fortnight luxury vacation in parris for my honeymoon"

# Implicit context
"Weekend getaway to Tokyo with my kids"
```

### How It Works

1.  **Ingestion:** The agent receives your raw text.
2.  **Extraction:** A specialized LLM step cleans the input, fixing typos and inferring context (e.g., "backpacking" -> Adventure Trip).
3.  **Orchestration (CrewAI):**
    *   **Activity Planner:** Finds venue-appropriate things to do.
    *   **Restaurant Scout:** Finds meals near those activities.
    *   **Itinerary Compiler:** Stitches it all together day-by-day.
4.  **Validation:** A final logic check ensures the output length matches the requested days exactly.

### Output Structure

```text
**5-Day Adventure Itinerary in Italy**

**Day 1: Arrival & Exploration**
- Morning: Hike up to...
- Lunch: Trattoria al Forno...
- Afternoon: ...

...

[Continues for exactly 5 days]
```

---

## 🔌 API Usage

The agent exposes a RESTful API compatible with the Bindu protocol.

### Send Message Endpoint

**POST** `http://localhost:3773/chat`

**Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Plan a 3 day surprise trip to Goa"
    }
  ]
}
```

**Response:**
```json
{
  "response": "**3-Day Itinerary for Goa**\n\nDay 1: Beach Vibes..."
}
```

For complete API documentation, visit:
📚 **[Bindu API Reference](https://docs.getbindu.com)**

---

## 🎯 Skills

### surprise-travel-planning (v1.0.0)

**Primary Capability:**
- Generating day-by-day travel itineraries based on natural language constraints.

**Features:**
- Typos correction & entity recognition
- Activity/Restaurant coordination
- Trip type classification (Budget, Luxury, Family, etc.)

**Best Used For:**
- Planning short to medium-length trips (2-14 days).
- Generating ideas when you have a destination but no plan.
- Quick "what if" scenario planning ("What would a luxury trip to Bali look like?").

**Not Suitable For:**
- Real-time flight booking or hotel reservations (it plans, doesn't book).
- Trips longer than 3 weeks (LLM context limits may degrade detail).

---

## 🐳 Docker Deployment

### Local Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up --build

# Agent will be available at http://localhost:3773
```

### Docker Configuration

Ensure your `.env` file is populated before building. The Docker container maps port `3773` by default.

```yaml
version: '3.8'
services:
  agent:
    build: .
    ports:
      - "3773:3773"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

---

## 🌐 Deploy to bindus.directory

Make your agent discoverable worldwide on the Internet of Agents.

### Setup GitHub Secrets

1.  Go to your repo **Settings > Secrets and variables > Actions**.
2.  Add the following secrets:
    *   `BINDU_API_TOKEN`: Your API key from [bindus.directory](https://bindus.directory).
    *   `DOCKERHUB_TOKEN`: Your Docker Hub access token.
    *   `DOCKERHUB_USERNAME`: Your Docker Hub username.

### Deploy

```bash
# Push to main to trigger automatic deployment
git push origin main
```

---

## 🛠️ Development

### Project Structure

```
surprise-travel-planning-agent/
├── surprise_travel_planning_agent/
│   ├── main.py                     # 🧠 Core logic (LLM extraction + CrewAI)
│   ├── skills/                     # Bindu skill definitions
│   └── agent_config.json           # Agent metadata
├── tests/
│   └── test_main.py                # Pytest suite
├── .env.example                    # Env var template
├── pyproject.toml                  # Dependencies (uv)
└── Dockerfile                      # Production build definition
```

### Running Tests

```bash
# Run unit tests
uv run pytest

# Run type checking
uv run pre-commit run --all-files
```

---

## 🤝 Contributing

We love contributions! Whether it's adding new trip types, improving the prompt engineering, or adding integration with booking APIs.

1.  Fork the repo.
2.  Create a branch: `git checkout -b feature/flight-search`
3.  Commit changes.
4.  Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Powered by Bindu

Built with the [Bindu Agent Framework](https://github.com/getbindu/bindu).

**Why Bindu?**
- ⚡ **Zero-config setup:** Focus on logic, not infrastructure.
- 🛠️ **Production-ready:** Built-in HTTP server, protocol handling, and dockerization.
- 🌐 **Interoperable:** Ready for the Internet of Agents.

<p align="center">
  <strong>Built with ❤️ by Paras Chamoli</strong>
</p>

<p align="center">
  <a href="https://github.com/Paraschamoli/surprise-travel-planning-agent/stargazers">⭐ Star this repo</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Join Discord</a> •
  <a href="https://bindus.directory">🌐 Agent Directory</a>
</p>

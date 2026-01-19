# AAQ-backend
Gemini 3 Hackathon

**AAQ-backend** is a clean, scalable FastAPI backend skeleton for an investment decision cockpit. It is feature-modular, agent/RL-ready, and separates user intent, market intelligence, strategy logic, human actions, and performance.

## Project Structure
```text
AAQ-backend/
├── README.md
├── pyproject.toml
├── .env.example
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── user/
│   │   ├── goal/
│   │   ├── market_intelligence/
│   │   ├── strategy/
│   │   ├── activities/
│   │   ├── performance/
│   │   ├── agents/
│   │   └── shared/
│   └── api/
└── tests/
    └── test_health.py
```

## Philosophy
- User decides, system advises
- Explainable strategies
- Performance is the core value
- Human-in-the-loop learning
- Agent & RL ready by design

## Stack
- FastAPI + Pydantic
- uv for env/deps

## Setup with `uv`
```bash
cd AAQ-backend
uv venv                          # create .venv
source .venv/bin/activate        # or .venv\\Scripts\\activate on Windows
uv pip install -e "[dev]"        # install project + dev deps
```

## Run
```bash
uv run uvicorn app.main:app --reload
```

## API docs / Swagger UI
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Test
```bash
uv run pytest
```

## Just commands (after installing `just`)
```bash
just install     # create venv + install deps via uv
just run         # run uvicorn app.main:app --reload
just test        # run pytest (TEST_ARGS env var supported)
just ruff        # lint with ruff
just check       # run pre-commit hooks on all files
just clean       # remove .pytest_cache and .ruff_cache
```

## Notes on modules
- `app/core/user` — user data, preferences, risk profile
- `app/core/goal` — user investment goals
- `app/core/market_intelligence` — signals, events, market snapshots
- `app/core/strategy` — strategies and backtests
- `app/core/activities` — decisions and feedback loop
- `app/core/performance` — performance metrics (core value)
- `app/core/agents` — agent state, reward, policy hooks
- `app/core/shared` — config, logging, database stubs
- `app/api` — aggregates feature routers under `/api`

## Why this architecture
- Feature-aligned with the product philosophy
- Clean separation of intent, intelligence, strategy, actions, performance
- Clear path to graph/RL/multi-agent extensions
- Frontend-friendly API surface for dashboards

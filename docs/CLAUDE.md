# CLAUDE.md — SaludCopilot

## What is this system

SaludCopilot is a clinical orchestration engine for Salud Digna clinics.
It calculates the optimal sequence of medical studies for each patient,
guides them through their visit via WhatsApp in real time, and provides
operational staff with a live dashboard to anticipate and manage patient flow.

WhatsApp is not a module. It is the product. Everything else is invisible
infrastructure that makes it possible.

---

## Stack — exact versions, no deviations

| Layer | Technology | Version |
|---|---|---|
| Backend API | FastAPI | 0.115.0 |
| ORM | SQLAlchemy async | 2.0.36 |
| Migrations | Alembic | 1.13.3 |
| Validation | Pydantic v2 | 2.9.2 |
| Database | PostgreSQL | 15 |
| Cache / queues | Redis | 7 |
| Frontend | Next.js | 14 |
| Bot runtime | Python | 3.12 |
| LLM | Claude API (Anthropic) | latest |
| Computer Vision | YOLOv8 (ultralytics) | 8.2.0 |
| ML | scikit-learn | 1.5.2 |
| Messaging | WhatsApp Cloud API (Meta) | v19 |

---

## Repository structure

```
saludcopilot/
├── apps/
│   ├── api/          → FastAPI backend — owns business logic and DB access
│   ├── bot/          → WhatsApp chatbot — owns patient-facing communication
│   ├── dashboard/    → Next.js dashboard — owns operational staff interface
│   └── cv/           → Computer vision worker — owns people counting pipeline
├── packages/
│   └── rules_engine/ → Clinical rules engine — isolated module, no external imports
├── ml/               → Predictive model — owns wait time predictions
├── scripts/          → Dev utilities
└── docker-compose.yml
```

One module, one responsibility. No module imports from another module's internals.
The only shared interfaces are HTTP (via the API) and the rules_engine package import.

---

## Naming conventions

**Language:** everything in English — variables, functions, classes, files, comments.

**Be explicit. Always.**
- `calculate_study_sequence` not `calc_seq`
- `patient_phone_number` not `phone` or `pn`
- `get_active_visit_by_patient_id` not `get_visit`
- `waiting_time_minutes` not `wait` or `time`

If a name requires a comment to explain what it does, rename it instead.

**Classes:** PascalCase — `PatientVisit`, `StudySequence`, `ClinicalRule`
**Functions and variables:** snake_case — `calculate_sequence`, `patient_id`
**Constants:** UPPER_SNAKE_CASE — `MAX_WAIT_TIME_MINUTES`, `DEFAULT_TTL_SECONDS`
**Files:** snake_case — `patient_router.py`, `sequence_calculator.py`

**Domain entities use their exact business name:**
- `Patient` not `User` or `Client`
- `Visit` not `Appointment` or `Session`
- `Study` not `Service` or `Exam`
- `StudySequence` not `Order` or `Queue`
- `ClinicalArea` not `Department` or `Room`
- `WaitTimeEstimate` not `Prediction` or `Estimate`

---

## Architecture decisions — already made, not up for discussion

**1. Rules engine is an isolated package**
Lives in `packages/rules_engine/`. No imports from `apps/`. The API imports it
as an internal library. Reason: it is the most critical module — wrong sequencing
causes active patient harm. It must be independently testable.

**2. PostgreSQL for historical data, Redis for real-time state**
Patient records, visits, study sequences, notifications go to PostgreSQL.
Active conversation state, current queue per area, active turn go to Redis.
Never write real-time state (changes every few seconds) to PostgreSQL.

**3. Monorepo**
All modules in one repository. Changes that affect multiple modules are visible
in a single commit.

**4. WhatsApp-native, no mobile app**
Zero friction adoption. The bot runs in two modes:
- Proactive mode (patient has appointment): bot initiates contact at booking time,
  sends preparation instructions and a 24h reminder.
- Reactive mode (walk-in patient): bot activates at reception, stays silent until
  the patient asks a question or a turn notification is triggered.

**5. No microservices**
Modules communicate via direct import (rules_engine) or HTTP to the API.
The CV worker posts people counts to the API. The bot calls the API.
No message brokers between modules except Redis for queue state.

**6. No medical interpretation**
The bot and the recommendations engine must never interpret results, diagnose,
or recommend specific treatments. Restricted to reference ranges and
"consult a medical professional" redirections. This is a domain constraint,
not a product decision. It is enforced in code, not in prompts.

---

## What the agent CAN do without asking

- Create new files inside its assigned module folder
- Add dependencies to its module's `requirements.txt`
- Write or modify tests inside its module's `tests/` folder
- Refactor code it wrote in the current session
- Add comments and docstrings
- Create helper functions inside its module

---

## What the agent MUST NOT do without explicit approval

- Modify the database schema (`apps/api/app/models/`)
- Change the rules engine public interface signatures
- Modify files outside its assigned module folder
- Add a dependency not already in scope
- Change an endpoint contract that another module consumes
- Rename domain entities

If any of these is necessary, write `# NEEDS APPROVAL: [reason]` and continue
with everything else that does not require the change.

---

## Error handling policy

- All API endpoints return structured errors:
  `{"error": "human readable description", "code": "SCREAMING_SNAKE_ERROR_CODE"}`
- Never return raw exception messages to the client
- Log errors with context: function name, input that caused the failure
- If TASK.md is ambiguous on a specific behavior, write `# QUESTION: [what is unclear]`
  and implement the most conservative interpretation

---

## Code quality baseline

- Functions do one thing. If a function needs a multi-line comment to explain
  what it does, it should be split into smaller functions.
- No magic numbers. Every numeric constant has a name.
- No commented-out code in commits.
- Every public function has a docstring: what it does, parameters, return value.
- Tests are mandatory for the rules engine.
- Tests are required for any function that contains business logic.

---

## Running the project locally

```bash
# Start base services
docker compose up

# Apply DB migrations (first time and after schema changes)
cd apps/api && alembic upgrade head

# Run rules engine tests
pytest packages/rules_engine/tests/ -v

# Expose bot webhook for WhatsApp
ngrok http 8001
```

---

## Environment variables

All variables are documented in `.env.example` at the repository root.
Never hardcode credentials. Never commit `.env`.
When a new variable is needed, add it to `.env.example` with a comment first.

# CareerPilot AI — focused MVP

CareerPilot AI turns one pasted job description into an honest fit analysis, role-specific
CV recommendations, a reviewed application answer, recruiter and follow-up messages, and
a persistent application record. It deliberately does **not** submit applications.

## The working slice

1. Paste a JD and optional company/role metadata; Wellfound skill tags can be supplied separately.
2. Review parsed job details, strong evidence, missing skills, and the six-part weighted score.
3. Prepare role-specific CV changes, an application answer, and outreach messages.
4. Inspect the critic's issues, improvements, and final application-ready answer.
5. Save a draft, explicitly mark a manually submitted application, or skip the job.
6. Filter the SQLite tracker and export a five-sheet Excel workbook with analytics.

The deterministic workflow works without an API key. An OpenAI-compatible client is
included as a safe extension point for OpenAI or OpenRouter, configured only through
environment variables.

## Run locally

Requires Python 3.11+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run careerpilot_ai/ui/streamlit_app.py
```

The UI opens at `http://localhost:8501`. SQLite creates `careerpilot.db` in the project
root on first run.

Optional API server:

```powershell
uvicorn careerpilot_ai.app.main:app --reload
```

Interactive API docs are then available at `http://127.0.0.1:8000/docs`.

## Test

```powershell
pytest -q
```

Tests cover SquareYards-style GenAI calibration, ParallelDots-style CV/salary handling,
an intentionally poor senior/MLOps fit, reviewer output, human status transitions,
SQLite persistence, and the expanded workbook structure.

## Design notes

- SQLite is the source of truth; Excel is generated on demand.
- Scores use the requested 30/25/15/10/10/10 weights and surface missing or unproven skills.
- Platform tags are merged with skills inferred from the full JD; neither source replaces the other.
- Unstated salary is scored at a neutral 50 with an explicit verification warning.
- Founding/senior backend roles receive conservative experience and project caps when cloud,
  orchestration, observability, or regulated-data ownership is not proven.
- Relevant 45–60% opportunities can be labeled `Maybe / Stretch Apply`; `Skip` is reserved for
  materially irrelevant, unacceptable, or far-beyond-profile roles.
- A high-growth override can lift a 70–74 score to Apply only with strong project evidence.
- Five-plus-year senior roles are capped at Maybe unless the detected skill match is weak,
  in which case they are Skip.
- “Applied” requires an explicit UI confirmation; the app never submits externally.
- The current profile lives in `careerpilot_ai/app/profile.py`, making every claim easy to audit.
- Existing SQLite trackers receive additive columns at startup; records are not discarded.

## Intentional next steps

This MVP avoids the monster-version trap. Base-CV upload, DOCX tailoring, profile editing,
LLM-powered prose, job discovery, recruiter outreach, and reminders remain separate future
increments after this vertical slice is validated.

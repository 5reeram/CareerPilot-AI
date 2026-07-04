from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from careerpilot_ai.app.config import get_settings
from careerpilot_ai.app.db import get_session, init_db
from careerpilot_ai.app.profile import SHASHI_PROFILE
from careerpilot_ai.app.schemas import (
    AnalysisPackage, CandidateProfile, JobInput, TrackerCreate, TrackerRecord, TrackerUpdate,
)
from careerpilot_ai.app.services.excel import ExcelService
from careerpilot_ai.app.services.tracker import DuplicateApplicationError, TrackerService
from careerpilot_ai.app.workflow import CareerPilotWorkflow

app = FastAPI(title=get_settings().app_name, version="0.1.0")
workflow = CareerPilotWorkflow()
tracker = TrackerService()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/profile", response_model=CandidateProfile)
def get_profile() -> CandidateProfile:
    return SHASHI_PROFILE


@app.post("/jobs/analyze", response_model=AnalysisPackage)
def analyze_job(job_input: JobInput) -> AnalysisPackage:
    return workflow.run(job_input)


@app.post("/tracker/add", response_model=TrackerRecord, status_code=201)
def add_tracker(data: TrackerCreate, session: Session = Depends(get_session)) -> TrackerRecord:
    try:
        return tracker.add(session, data)
    except DuplicateApplicationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/tracker/list", response_model=list[TrackerRecord])
def list_tracker(session: Session = Depends(get_session)) -> list[TrackerRecord]:
    return tracker.list(session)


@app.patch("/tracker/update/{record_id}", response_model=TrackerRecord)
def update_tracker(record_id: int, data: TrackerUpdate, session: Session = Depends(get_session)) -> TrackerRecord:
    record = tracker.update(session, record_id, data)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    return record


@app.get("/tracker/export-excel")
def export_tracker(session: Session = Depends(get_session)) -> Response:
    content = ExcelService().export(tracker.list(session))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=careerpilot_tracker.xlsx"},
    )

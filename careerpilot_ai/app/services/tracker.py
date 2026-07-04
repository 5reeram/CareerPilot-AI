from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from careerpilot_ai.app.db import ApplicationRecord
from careerpilot_ai.app.schemas import TrackerCreate, TrackerRecord, TrackerStatus, TrackerUpdate


class DuplicateApplicationError(ValueError):
    def __init__(self, record_id: int) -> None:
        self.record_id = record_id
        super().__init__(f"Application already exists as record #{record_id}.")


def _to_schema(record: ApplicationRecord) -> TrackerRecord:
    return TrackerRecord(
        id=record.id,
        date_found=record.date_found,
        date_applied=record.date_applied,
        company=record.company,
        role=record.role,
        portal=record.portal,
        job_link=record.job_link,
        location=record.location,
        remote_policy=record.remote_policy,
        salary_range=record.salary_range,
        required_experience=record.required_experience,
        role_category=record.role_category,
        match_score=record.match_score,
        skill_score=record.skill_score,
        project_score=record.project_score,
        experience_score=record.experience_score,
        salary_score=record.salary_score,
        location_score=record.location_score,
        growth_score=record.growth_score,
        recommendation=record.recommendation,
        status=record.status,
        strong_matches=[item for item in record.strong_matches.split("|") if item],
        application_answer=record.application_answer,
        missing_skills=[item for item in record.missing_skills.split("|") if item],
        best_projects=[item for item in record.best_projects.split("|") if item],
        cv_version_name=record.cv_version_name,
        recruiter_message=record.recruiter_message,
        follow_up_message=record.follow_up_message,
        notes=record.notes,
        follow_up_date=record.follow_up_date,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class TrackerService:
    def add(self, session: Session, data: TrackerCreate) -> TrackerRecord:
        duplicate = self.find_duplicate(session, data)
        if duplicate:
            raise DuplicateApplicationError(duplicate.id)
        list_fields = {"strong_matches", "missing_skills", "best_projects"}
        values = data.model_dump(exclude=list_fields)
        values["recommendation"] = data.recommendation.value
        values["status"] = data.status.value
        values["missing_skills"] = "|".join(data.missing_skills)
        values["strong_matches"] = "|".join(data.strong_matches)
        values["best_projects"] = "|".join(data.best_projects)
        if data.status == TrackerStatus.APPLIED and not data.date_applied:
            values["date_applied"] = date.today()
        record = ApplicationRecord(**values)
        session.add(record)
        session.commit()
        session.refresh(record)
        return _to_schema(record)

    def find_duplicate(self, session: Session, data: TrackerCreate) -> TrackerRecord | None:
        target = (
            self._normalize_text(data.company),
            self._normalize_text(data.role),
            self._normalize_link(data.job_link),
        )
        records = session.scalars(select(ApplicationRecord)).all()
        for record in records:
            candidate = (
                self._normalize_text(record.company),
                self._normalize_text(record.role),
                self._normalize_link(record.job_link),
            )
            if candidate == target:
                return _to_schema(record)
        return None

    @staticmethod
    def follow_ups_due(
        records: list[TrackerRecord], as_of: date | None = None,
    ) -> list[TrackerRecord]:
        due_date = as_of or date.today()
        terminal = {
            TrackerStatus.OFFER, TrackerStatus.REJECTED,
            TrackerStatus.WITHDRAWN, TrackerStatus.SKIPPED,
        }
        return [
            record for record in records
            if record.follow_up_date is not None
            and record.follow_up_date <= due_date
            and record.status not in terminal
        ]

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _normalize_link(value: str) -> str:
        return value.strip().rstrip("/")

    def list(self, session: Session) -> list[TrackerRecord]:
        records = session.scalars(select(ApplicationRecord).order_by(ApplicationRecord.id.desc())).all()
        return [_to_schema(record) for record in records]

    def update(self, session: Session, record_id: int, data: TrackerUpdate) -> TrackerRecord | None:
        record = session.get(ApplicationRecord, record_id)
        if not record:
            return None
        updates = data.model_dump(exclude_unset=True)
        if "status" in updates:
            record.status = data.status.value
            updates.pop("status")
            if data.status == TrackerStatus.APPLIED and "date_applied" not in updates:
                record.date_applied = date.today()
        for field, value in updates.items():
            setattr(record, field, value)
        session.commit()
        session.refresh(record)
        return _to_schema(record)

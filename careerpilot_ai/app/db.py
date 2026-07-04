from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text, create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from careerpilot_ai.app.config import get_settings


class Base(DeclarativeBase):
    pass


class ApplicationRecord(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_found: Mapped[date] = mapped_column(Date, default=date.today)
    date_applied: Mapped[date | None] = mapped_column(Date, nullable=True)
    company: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(200), index=True)
    portal: Mapped[str] = mapped_column(String(100), default="Manual")
    job_link: Mapped[str] = mapped_column(String(2000), default="")
    location: Mapped[str] = mapped_column(String(200), default="Not specified")
    remote_policy: Mapped[str] = mapped_column(String(100), default="Not specified")
    salary_range: Mapped[str] = mapped_column(String(200), default="Not specified")
    required_experience: Mapped[str] = mapped_column(String(100), default="Not specified")
    role_category: Mapped[str] = mapped_column(String(100), default="AI/Software")
    match_score: Mapped[int] = mapped_column(Integer)
    skill_score: Mapped[int] = mapped_column(Integer, default=0)
    project_score: Mapped[int] = mapped_column(Integer, default=0)
    experience_score: Mapped[int] = mapped_column(Integer, default=0)
    salary_score: Mapped[int] = mapped_column(Integer, default=0)
    location_score: Mapped[int] = mapped_column(Integer, default=0)
    growth_score: Mapped[int] = mapped_column(Integer, default=0)
    recommendation: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(50), index=True)
    application_answer: Mapped[str] = mapped_column(Text, default="")
    strong_matches: Mapped[str] = mapped_column(Text, default="")
    missing_skills: Mapped[str] = mapped_column(Text, default="")
    best_projects: Mapped[str] = mapped_column(Text, default="")
    cv_version_name: Mapped[str] = mapped_column(String(300), default="")
    recruiter_message: Mapped[str] = mapped_column(Text, default="")
    follow_up_message: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    if settings.database_url.startswith("sqlite"):
        _migrate_sqlite_columns()


def _migrate_sqlite_columns() -> None:
    """Add new MVP columns without deleting a user's existing tracker."""
    existing = {column["name"] for column in inspect(engine).get_columns("applications")}
    additions = {
        "role_category": "VARCHAR(100) NOT NULL DEFAULT 'AI/Software'",
        "skill_score": "INTEGER NOT NULL DEFAULT 0",
        "project_score": "INTEGER NOT NULL DEFAULT 0",
        "experience_score": "INTEGER NOT NULL DEFAULT 0",
        "salary_score": "INTEGER NOT NULL DEFAULT 0",
        "location_score": "INTEGER NOT NULL DEFAULT 0",
        "growth_score": "INTEGER NOT NULL DEFAULT 0",
        "strong_matches": "TEXT NOT NULL DEFAULT ''",
        "best_projects": "TEXT NOT NULL DEFAULT ''",
        "cv_version_name": "VARCHAR(300) NOT NULL DEFAULT ''",
        "recruiter_message": "TEXT NOT NULL DEFAULT ''",
        "follow_up_message": "TEXT NOT NULL DEFAULT ''",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in existing:
                connection.exec_driver_sql(f"ALTER TABLE applications ADD COLUMN {name} {definition}")


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

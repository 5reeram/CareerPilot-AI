from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Recommendation(StrEnum):
    APPLY = "Apply"
    MAYBE = "Maybe"
    STRETCH = "Maybe / Stretch Apply"
    SKIP = "Skip"


class TrackerStatus(StrEnum):
    FOUND = "Found"
    READY = "Ready to Apply"
    APPLIED = "Applied"
    SKIPPED = "Skipped"
    ASSESSMENT = "Assessment"
    INTERVIEW_1 = "Interview Round 1"
    INTERVIEW_2 = "Interview Round 2"
    OFFER = "Offer"
    REJECTED = "Rejected"
    NO_RESPONSE = "No Response"
    WITHDRAWN = "Withdrawn"


class CandidateProfile(BaseModel):
    name: str
    target_roles: list[str]
    skills: list[str]
    projects: dict[str, list[str]]
    preferences: dict[str, str] = Field(default_factory=dict)


class JobInput(BaseModel):
    description: str = Field(min_length=80, max_length=50_000)
    company_name: str = Field(default="", max_length=200)
    role_title: str = Field(default="", max_length=200)
    job_link: str = Field(default="", max_length=2_000)
    portal: str = Field(default="Manual", max_length=100)
    platform_skills: list[str] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return "\n".join(line.rstrip() for line in value.strip().splitlines())


class ParsedJob(BaseModel):
    company_name: str = "Unknown company"
    role_title: str = "Unknown role"
    location: str = "Not specified"
    remote_policy: str = "Not specified"
    salary_range: str = "Not specified"
    required_experience: str = "Not specified"
    employment_type: str = "Not specified"
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    company_highlights: list[str] = Field(default_factory=list)
    keywords_for_ats: list[str] = Field(default_factory=list)
    domain: str = "AI/Software"
    seniority_level: str = "Not specified"
    red_flags: list[str] = Field(default_factory=list)
    application_questions: list[str] = Field(default_factory=list)


class FitScore(BaseModel):
    skill_match: int = Field(ge=0, le=100)
    project_match: int = Field(ge=0, le=100)
    experience_match: int = Field(ge=0, le=100)
    salary_match: int = Field(ge=0, le=100)
    location_match: int = Field(ge=0, le=100)
    growth_value: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)
    recommendation: Recommendation
    reasoning: str
    strong_matches: list[str]
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str]
    risks: list[str]
    how_to_position_candidate: str
    relevant_projects: list[str]


class ApplicationAnswer(BaseModel):
    question: str
    answer: str
    short_answer: str
    notes: str = ""


class ReviewResult(BaseModel):
    status: str
    issues_found: list[str]
    improvement_suggestions: list[str]
    improvements_made: list[str] = Field(default_factory=list)
    why_stronger: str = ""
    revised_output: str


class CVSuggestions(BaseModel):
    suggested_headline: str = ""
    tailored_summary: str = ""
    skills_to_move_up: list[str] = Field(default_factory=list)
    projects_to_move_up: list[str] = Field(default_factory=list)
    experience_bullets: list[str] = Field(default_factory=list)
    items_to_reduce: list[str] = Field(default_factory=list)
    ats_keywords: list[str] = Field(default_factory=list)
    cv_version_name: str = ""


class OutreachMessages(BaseModel):
    recruiter_message: str = ""
    follow_up_message: str = ""


class AnalysisPackage(BaseModel):
    job: ParsedJob
    fit: FitScore
    answer: ApplicationAnswer
    review: ReviewResult
    cv_suggestions: CVSuggestions = Field(default_factory=CVSuggestions)
    outreach: OutreachMessages = Field(default_factory=OutreachMessages)
    writing_mode: str = "Deterministic"
    writing_warning: str = ""


class TrackerCreate(BaseModel):
    company: str
    role: str
    portal: str = "Manual"
    job_link: str = ""
    location: str = "Not specified"
    remote_policy: str = "Not specified"
    salary_range: str = "Not specified"
    required_experience: str = "Not specified"
    role_category: str = "AI/Software"
    match_score: int = Field(ge=0, le=100)
    skill_score: int = Field(default=0, ge=0, le=100)
    project_score: int = Field(default=0, ge=0, le=100)
    experience_score: int = Field(default=0, ge=0, le=100)
    salary_score: int = Field(default=0, ge=0, le=100)
    location_score: int = Field(default=0, ge=0, le=100)
    growth_score: int = Field(default=0, ge=0, le=100)
    recommendation: Recommendation
    status: TrackerStatus = TrackerStatus.READY
    strong_matches: list[str] = Field(default_factory=list)
    application_answer: str = ""
    missing_skills: list[str] = Field(default_factory=list)
    best_projects: list[str] = Field(default_factory=list)
    cv_version_name: str = ""
    recruiter_message: str = ""
    follow_up_message: str = ""
    notes: str = ""
    follow_up_date: date | None = None
    date_applied: date | None = None


class TrackerUpdate(BaseModel):
    status: TrackerStatus | None = None
    application_answer: str | None = None
    recruiter_message: str | None = None
    follow_up_message: str | None = None
    notes: str | None = None
    follow_up_date: date | None = None
    date_applied: date | None = None


class TrackerRecord(TrackerCreate):
    id: int
    date_found: date
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

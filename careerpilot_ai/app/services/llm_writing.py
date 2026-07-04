import json
from typing import Literal

from pydantic import BaseModel, Field

from careerpilot_ai.app.agents.answer_writer import ApplicationAnswerAgent
from careerpilot_ai.app.schemas import (
    ApplicationAnswer,
    CandidateProfile,
    CVSuggestions,
    FitScore,
    OutreachMessages,
    ParsedJob,
    ReviewResult,
)
from careerpilot_ai.app.services.llm_client import LLMClient


class LLMWritingOutput(BaseModel):
    application_answer: str = Field(min_length=20)
    reviewer_status: Literal["Approved", "Needs Revision"]
    reviewer_issues: list[str] = Field(default_factory=list)
    reviewer_suggestions: list[str] = Field(default_factory=list)
    improvements_made: list[str] = Field(default_factory=list)
    why_stronger: str = Field(min_length=10)
    revised_output: str = Field(min_length=20)
    recruiter_message: str = Field(min_length=20)
    follow_up_message: str = Field(min_length=20)
    tailored_cv_summary: str = Field(min_length=20)


class LLMWritingService:
    """Enhances prose only; deterministic job parsing and scoring stay authoritative."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    @property
    def enabled(self) -> bool:
        return self.client.configured

    def enhance(
        self,
        job: ParsedJob,
        fit: FitScore,
        profile: CandidateProfile,
        answer: ApplicationAnswer,
        review: ReviewResult,
        cv: CVSuggestions,
        outreach: OutreachMessages,
        character_limit: int | None = None,
    ) -> tuple[ApplicationAnswer, ReviewResult, CVSuggestions, OutreachMessages]:
        context = {
            "candidate_profile": profile.model_dump(mode="json"),
            "parsed_job": job.model_dump(mode="json"),
            "deterministic_fit": fit.model_dump(mode="json"),
            "application_question": answer.question,
            "character_limit": character_limit,
            "deterministic_drafts": {
                "application_answer": answer.answer,
                "review": review.model_dump(mode="json"),
                "cv_summary": cv.tailored_summary,
                "recruiter_message": outreach.recruiter_message,
                "follow_up_message": outreach.follow_up_message,
            },
        }
        system = (
            "You are the writing and review layer for a job application assistant. "
            "Use only facts in the supplied candidate profile and project evidence. Never invent experience, "
            "metrics, employers, tools, or years. Do not alter or dispute any deterministic score or recommendation. "
            "Make the answer company-specific, natural, concise, and directly responsive to the application question. "
            "The recruiter message must be 3-5 short lines; the follow-up must be brief and professional. "
            "Critically review the first answer and always return an application-ready revised_output."
        )
        result = self.client.structured_completion(
            system=system,
            prompt="Generate the structured writing package from this JSON context:\n" + json.dumps(context),
            output_model=LLMWritingOutput,
        )
        llm_answer = result.application_answer
        revised = result.revised_output
        if character_limit:
            llm_answer = ApplicationAnswerAgent._fit_character_limit(
                llm_answer, llm_answer, character_limit,
            )
            revised = ApplicationAnswerAgent._fit_character_limit(
                revised, revised, character_limit,
            )
        return (
            answer.model_copy(update={"answer": llm_answer, "short_answer": llm_answer}),
            ReviewResult(
                status=result.reviewer_status,
                issues_found=result.reviewer_issues,
                improvement_suggestions=result.reviewer_suggestions,
                improvements_made=result.improvements_made,
                why_stronger=result.why_stronger,
                revised_output=revised,
            ),
            cv.model_copy(update={"tailored_summary": result.tailored_cv_summary}),
            OutreachMessages(
                recruiter_message=result.recruiter_message,
                follow_up_message=result.follow_up_message,
            ),
        )

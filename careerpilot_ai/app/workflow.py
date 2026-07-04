from careerpilot_ai.app.agents.answer_writer import ApplicationAnswerAgent
from careerpilot_ai.app.agents.cv_tailor import CVTailoringAgent
from careerpilot_ai.app.agents.fit_scorer import FitScoringAgent
from careerpilot_ai.app.agents.job_parser import JobParserAgent
from careerpilot_ai.app.agents.outreach import OutreachAgent
from careerpilot_ai.app.agents.reviewer import ReviewerAgent
from careerpilot_ai.app.profile import SHASHI_PROFILE
from careerpilot_ai.app.schemas import AnalysisPackage, JobInput
from careerpilot_ai.app.services.llm_client import LLMClient
from careerpilot_ai.app.services.llm_writing import LLMWritingService


class CareerPilotWorkflow:
    def __init__(self, llm_client: LLMClient | None = None, enable_llm: bool = True) -> None:
        self.parser = JobParserAgent()
        self.scorer = FitScoringAgent()
        self.writer = ApplicationAnswerAgent()
        self.reviewer = ReviewerAgent()
        self.cv_tailor = CVTailoringAgent()
        self.outreach = OutreachAgent()
        self.llm_writing = LLMWritingService(llm_client or LLMClient()) if enable_llm else None

    def run(
        self,
        job_input: JobInput,
        question: str = "What interests you about working for this company?",
        character_limit: int | None = None,
    ) -> AnalysisPackage:
        job = self.parser.parse(job_input)
        fit = self.scorer.score(job, SHASHI_PROFILE)
        answer = self.writer.generate(
            job, fit, SHASHI_PROFILE, question, character_limit=character_limit,
        )
        review = self.reviewer.review(
            answer.answer, job, fit, character_limit=character_limit,
        )
        cv_suggestions = self.cv_tailor.generate(job, fit, SHASHI_PROFILE)
        outreach = self.outreach.generate(job, fit)
        writing_mode = "Deterministic"
        writing_warning = ""
        if self.llm_writing and self.llm_writing.enabled:
            try:
                answer, review, cv_suggestions, outreach = self.llm_writing.enhance(
                    job=job,
                    fit=fit,
                    profile=SHASHI_PROFILE,
                    answer=answer,
                    review=review,
                    cv=cv_suggestions,
                    outreach=outreach,
                    character_limit=character_limit,
                )
                writing_mode = "LLM"
            except Exception as exc:
                writing_warning = (
                    "LLM writing failed; deterministic fallback was used. "
                    f"{type(exc).__name__}: {exc}"
                )
        return AnalysisPackage(
            job=job, fit=fit, answer=answer, review=review,
            cv_suggestions=cv_suggestions, outreach=outreach,
            writing_mode=writing_mode, writing_warning=writing_warning,
        )

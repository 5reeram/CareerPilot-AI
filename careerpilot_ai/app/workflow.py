from careerpilot_ai.app.agents.answer_writer import ApplicationAnswerAgent
from careerpilot_ai.app.agents.cv_tailor import CVTailoringAgent
from careerpilot_ai.app.agents.fit_scorer import FitScoringAgent
from careerpilot_ai.app.agents.job_parser import JobParserAgent
from careerpilot_ai.app.agents.outreach import OutreachAgent
from careerpilot_ai.app.agents.reviewer import ReviewerAgent
from careerpilot_ai.app.profile import SHASHI_PROFILE
from careerpilot_ai.app.schemas import AnalysisPackage, JobInput


class CareerPilotWorkflow:
    def __init__(self) -> None:
        self.parser = JobParserAgent()
        self.scorer = FitScoringAgent()
        self.writer = ApplicationAnswerAgent()
        self.reviewer = ReviewerAgent()
        self.cv_tailor = CVTailoringAgent()
        self.outreach = OutreachAgent()

    def run(self, job_input: JobInput, question: str = "What interests you about working for this company?") -> AnalysisPackage:
        job = self.parser.parse(job_input)
        fit = self.scorer.score(job, SHASHI_PROFILE)
        answer = self.writer.generate(job, fit, SHASHI_PROFILE, question)
        review = self.reviewer.review(answer.answer, job, fit)
        cv_suggestions = self.cv_tailor.generate(job, fit, SHASHI_PROFILE)
        outreach = self.outreach.generate(job, fit)
        return AnalysisPackage(
            job=job, fit=fit, answer=answer, review=review,
            cv_suggestions=cv_suggestions, outreach=outreach,
        )

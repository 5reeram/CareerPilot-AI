from careerpilot_ai.app.schemas import ApplicationAnswer, CandidateProfile, FitScore, ParsedJob


class ApplicationAnswerAgent:
    def generate(
        self,
        job: ParsedJob,
        fit: FitScore,
        profile: CandidateProfile,
        question: str = "Why are you a good fit for this role?",
    ) -> ApplicationAnswer:
        company = job.company_name if job.company_name != "Unknown company" else "your team"
        role = job.role_title if job.role_title != "Unknown role" else job.domain + " role"
        project = fit.relevant_projects[0] if fit.relevant_projects else next(iter(profile.projects))
        skills = getattr(fit, "matched_skills", [])[:5]
        skill_text = ", ".join(skills) if skills else "Python and applied AI development"
        role_focus = self._role_focus(job)
        evidence = self._project_evidence(project)
        gap_sentence = self._gap_sentence(fit)

        answer = (
            f"I'm interested in the {role} opportunity at {company} because it combines "
            f"{role_focus}. The chance to apply these technologies to visible, real-world product problems "
            "is especially compelling to me.\n\n"
            f"My strongest evidence of fit is {project}. I {evidence}. Through that work, I gained practical "
            f"experience with {skill_text}, API ownership, and turning AI capabilities into reliable "
            f"user-facing workflows. {gap_sentence}\n\n"
            "I would bring a product-minded engineering approach: learn quickly, test ideas against user needs, "
            "and carry promising AI experiments through to maintainable application workflows."
        )
        short = (
            f"I match this role through hands-on work in {skill_text}, especially {project}. "
            f"I can contribute practical AI product and backend experience to {company} from day one."
        )
        return ApplicationAnswer(
            question=question,
            answer=answer,
            short_answer=short,
            notes="Drafted only from the stored candidate profile and pasted JD.",
        )

    @staticmethod
    def _role_focus(job: ParsedJob) -> str:
        keywords = {skill.casefold() for skill in job.keywords_for_ats}
        highlights = " ".join(getattr(job, "company_highlights", [])).casefold()
        scale = " at million-user production scale" if "million user" in highlights else ""
        industry = " in real estate" if "real-estate" in highlights or "real estate" in highlights else ""
        if job.domain == "Generative AI":
            if {"image generation", "video generation", "diffusion models"}.intersection(keywords):
                return f"open-source image and video generation, practical GenAI tooling, and product work{scale}{industry}"
            return "hands-on generative AI development with real product ownership"
        if job.domain == "Computer Vision":
            return "computer vision model development with practical deployment"
        if job.domain == "Machine Learning":
            return "machine-learning development, evaluation, and production delivery"
        if job.domain == "AI Backend":
            return "AI product development with robust backend and API ownership"
        return "applied AI engineering with measurable product impact"

    @staticmethod
    def _project_evidence(project: str) -> str:
        evidence = {
            "Ghostverse.ai GenAI Storybook Platform": (
                "owned API workflows for story and image generation, regeneration, editing, export, and sharing"
            ),
            "AI Conversational Dashboard": (
                "built a workflow that turns uploaded data and natural-language questions into KPIs, charts, and insights"
            ),
            "XAUUSD Prediction Model": (
                "built the feature-engineering, ensemble-model, backtesting, API, and prediction-logging workflow"
            ),
            "Drowsy Driver Detection": (
                "developed an OpenCV-based safety project that won a Techathon prize and received GCSP recognition"
            ),
        }
        return evidence.get(project, "turned AI requirements into a working product")

    @staticmethod
    def _gap_sentence(fit: FitScore) -> str:
        if not fit.missing_skills:
            return "This gives me a strong base for contributing without overstating the scope of my experience."
        gaps = ", ".join(fit.missing_skills[:2])
        return (
            f"I would treat {gaps} as explicit ramp-up areas, building on adjacent experience rather than "
            "claiming tools I have not yet used deeply."
        )

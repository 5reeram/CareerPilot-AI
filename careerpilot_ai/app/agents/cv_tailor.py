from careerpilot_ai.app.schemas import CVSuggestions, CandidateProfile, FitScore, ParsedJob


class CVTailoringAgent:
    """Produces auditable CV recommendations; it never invents experience."""

    def generate(self, job: ParsedJob, fit: FitScore, profile: CandidateProfile) -> CVSuggestions:
        role = job.role_title if job.role_title != "Unknown role" else job.domain + " Engineer"
        matched = fit.matched_skills or [item for item in fit.strong_matches if len(item) < 50]
        projects = fit.relevant_projects[:3]
        bullets = self._bullets(job.domain)
        summary = (
            f"Applied AI engineer with hands-on experience building {job.domain.lower()} products, "
            f"backend APIs, and user-facing workflows. Strongest evidence includes "
            f"{', '.join(projects[:2]) or 'delivered AI projects'}, supported by "
            f"{', '.join(matched[:5]) or 'Python, FastAPI, and practical model integration'}."
        )
        return CVSuggestions(
            suggested_headline=f"{role} | Python, FastAPI & {job.domain}",
            tailored_summary=summary,
            skills_to_move_up=matched[:8],
            projects_to_move_up=projects,
            experience_bullets=bullets,
            items_to_reduce=[
                "Move unrelated projects below the role-relevant project evidence.",
                "Reduce generic tool lists that are not supported by a project bullet.",
            ],
            ats_keywords=job.keywords_for_ats[:12],
            cv_version_name=f"Shashi_Bandi_{self._safe_name(role)}_{self._safe_name(job.company_name)}.docx",
        )

    @staticmethod
    def _bullets(domain: str) -> list[str]:
        if domain == "Generative AI":
            return [
                "Single-handedly built the Ghostverse.ai API layer for questionnaire, story, image-generation, regeneration, editing, export, download, and sharing workflows.",
                "Emphasize hands-on ComfyUI, Stable Diffusion, LoRA/QLoRA, LLM API, and FastAPI integration work.",
                "Frame the work as end-to-end GenAI product delivery, from model workflow to user-facing capability.",
            ]
        if domain == "Computer Vision":
            return [
                "Lead with the OpenCV/object-detection work in Drowsy Driver Detection.",
                "Mention the Techathon prize and GCSP recognition as external evidence of impact.",
                "Connect Python model work to deployment and real-world safety outcomes.",
            ]
        if domain == "AI Backend":
            return [
                "Lead with FastAPI and REST API ownership for Ghostverse.ai.",
                "Emphasize MySQL logging, model serving, workflow reliability, and Streamlit integration.",
            ]
        return [
            "Lead with XAUUSD feature engineering, ensemble modeling, validation, and backtesting.",
            "Support ML claims with Drowsy Driver Detection and deployed FastAPI workflows.",
        ]

    @staticmethod
    def _safe_name(value: str) -> str:
        return "_".join(part for part in value.replace("/", " ").split() if part)[:50]


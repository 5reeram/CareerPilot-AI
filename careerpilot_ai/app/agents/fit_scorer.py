import re

from careerpilot_ai.app.schemas import CandidateProfile, FitScore, ParsedJob, Recommendation


NORMALIZED_EQUIVALENTS = {
    "computer vision": {"opencv", "computer vision", "object detection"},
    "object detection": {"opencv", "computer vision", "object detection"},
    "image generation": {"stable diffusion", "comfyui", "image generation"},
    "diffusion models": {"stable diffusion", "comfyui", "diffusion models"},
    "llm apis": {"llm apis", "llama", "openrouter", "prompt engineering"},
    "rest apis": {"rest apis", "fastapi"},
    "lora": {"lora", "qlora"},
}

CRITICAL_OWNERSHIP_SKILLS = {
    "Backend Architecture", "AI Layer", "Orchestration Engine", "Cloud Infrastructure", "Message Queues",
    "Event-driven Systems", "Authentication & Authorization", "Observability", "Temporal",
    "Healthcare Domain", "Privacy & PDPL", "FHIR", "NPHIES", "Regulated Data Systems",
    "Clinical Evaluation Harnesses", "Healthcare-grade Reliability", "Scheduling Logic",
}


class FitScoringAgent:
    def score(self, job: ParsedJob, profile: CandidateProfile) -> FitScore:
        candidate_skills = {skill.casefold() for skill in profile.skills}
        requirements = job.required_skills or job.keywords_for_ats
        matched, missing = [], []
        for skill in requirements:
            normalized = skill.casefold()
            equivalents = NORMALIZED_EQUIVALENTS.get(normalized, {normalized})
            (matched if candidate_skills.intersection(equivalents) else missing).append(skill)

        skill_score = round(100 * len(matched) / len(requirements)) if requirements else 60
        project_scores: list[tuple[str, int]] = []
        job_terms = {s.casefold() for s in job.keywords_for_ats} | set(job.domain.casefold().split())
        for name, tags in profile.projects.items():
            project_terms = {tag.casefold() for tag in tags}
            overlap = sum(
                1 for term in job_terms
                if term in project_terms or any(term in tag or tag in term for tag in project_terms)
            )
            project_scores.append((name, overlap + self._role_project_bonus(job.domain, name)))
        project_scores.sort(key=lambda item: item[1], reverse=True)
        relevant_projects = [name for name, count in project_scores if count > 0][:3]
        best_overlap = project_scores[0][1] if project_scores else 0
        project_score = min(100, 45 + best_overlap * 12) if relevant_projects else 35

        years_match = re.search(r"(\d+)", job.required_experience)
        requested_years = int(years_match.group(1)) if years_match else 0
        experience_score = (
            35 if requested_years >= 5 else 55 if requested_years >= 3
            else 72 if requested_years >= 2 else 85 if requested_years == 1 else 65
        )
        ownership_role = job.seniority_level in {"Founding/Lead", "Senior"} or any(
            term in job.role_title.casefold() for term in ("founding", "lead", "principal", "head")
        )
        critical_set = {skill.casefold() for skill in CRITICAL_OWNERSHIP_SKILLS}
        critical_gaps = [skill for skill in missing if skill.casefold() in critical_set]
        if ownership_role:
            if len(critical_gaps) >= 5:
                experience_score = min(experience_score, 40)
                project_score = min(project_score, 75)
            elif len(critical_gaps) >= 2:
                experience_score = min(experience_score, 45)
                project_score = min(project_score, 85)
            else:
                experience_score = min(experience_score, 50)
        salary_score = self._salary_score(job.salary_range)
        location_score = 90 if job.remote_policy == "Remote" else 70 if job.remote_policy in ("Hybrid", "Not specified") else 55
        growth_score = min(95, 70 + 5 * len(matched))
        overall = round(
            skill_score * .30 + project_score * .25 + experience_score * .15
            + salary_score * .10 + location_score * .10 + growth_score * .10
        )
        risks = list(job.red_flags)
        if missing:
            risks.append(f"Missing or unproven requirements: {', '.join(missing[:10])}.")
        if job.salary_range == "Not specified":
            risks.append("Salary not mentioned. Verify before serious commitment.")
        elif salary_score < 60:
            risks.append("The advertised salary appears low for the target role; verify it against your minimum.")
        if ownership_role and critical_gaps:
            risks.append(
                "The role expects production ownership not strongly proven by the current profile: "
                + ", ".join(critical_gaps[:8]) + "."
            )

        material_red_flags = any(
            phrase in risk.casefold() for risk in job.red_flags
            for phrase in ("24/7", "unpaid", "commission only")
        )
        clearly_irrelevant = skill_score < 30 and project_score < 45
        far_beyond_profile = requested_years >= 5 and skill_score < 35 and project_score < 60
        salary_unacceptable = salary_score <= 30
        if material_red_flags or clearly_irrelevant or far_beyond_profile or salary_unacceptable:
            recommendation = Recommendation.SKIP
        elif overall >= 75 and not (ownership_role and len(critical_gaps) >= 5):
            recommendation = Recommendation.APPLY
        elif overall >= 61:
            recommendation = Recommendation.MAYBE
        elif overall >= 45 and growth_score >= 75 and project_score >= 55:
            recommendation = Recommendation.STRETCH
        elif overall >= 45:
            recommendation = Recommendation.MAYBE
        else:
            recommendation = Recommendation.SKIP

        strong_matches = self._explain_matches(job, matched, relevant_projects)
        project_phrase = relevant_projects[0] if relevant_projects else "the closest relevant project"
        reasoning = (
            f"Matched {len(matched)} of {len(requirements)} detected core skills. "
            f"{project_phrase} provides the strongest practical evidence for this role. "
            + (
                f"Experience is capped because {len(critical_gaps)} production ownership requirements are unproven. "
                if ownership_role and critical_gaps else ""
            )
            + ("Salary is unknown and scored neutrally." if job.salary_range == "Not specified" else "")
            + f" Recommendation: {recommendation.value}."
        )
        positioning = (
            f"Lead with {project_phrase}; connect its delivered outcomes to "
            f"{', '.join(matched[:4]) or job.domain}, while treating missing skills as learning areas."
        )
        return FitScore(
            skill_match=skill_score,
            project_match=project_score,
            experience_match=experience_score,
            salary_match=salary_score,
            location_match=location_score,
            growth_value=growth_score,
            overall_score=overall,
            recommendation=recommendation,
            reasoning=reasoning,
            strong_matches=strong_matches,
            matched_skills=matched,
            missing_skills=missing,
            risks=risks,
            how_to_position_candidate=positioning,
            relevant_projects=relevant_projects,
        )

    @staticmethod
    def _salary_score(salary_range: str) -> int:
        if salary_range == "Not specified":
            return 50
        lower = salary_range.casefold()
        values = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", lower)]
        if ("lpa" in lower or "lakh" in lower) and values:
            maximum = max(values)
            if maximum <= 8:
                return 45
            if maximum <= 12:
                return 60
            return 80
        return 75

    @staticmethod
    def _role_project_bonus(domain: str, project: str) -> int:
        priorities = {
            "Generative AI": {
                "Ghostverse.ai GenAI Storybook Platform": 2,
                "Generative Image Editing / ComfyUI Workflows": 1,
            },
            "Computer Vision": {"Drowsy Driver Detection": 2},
            "AI Backend": {
                "Ghostverse.ai GenAI Storybook Platform": 2,
                "AI Conversational Dashboard": 1,
                "CareerPilot AI Multi-Agent Application Assistant": 2,
            },
            "Machine Learning": {
                "XAUUSD Prediction Model": 2,
                "Drowsy Driver Detection": 1,
            },
        }
        return priorities.get(domain, {}).get(project, 0)

    @staticmethod
    def _explain_matches(job: ParsedJob, matched: list[str], projects: list[str]) -> list[str]:
        explanations: list[str] = []
        if any(project.startswith("Ghostverse") for project in projects):
            explanations.append("Ghostverse.ai demonstrates GenAI product delivery and end-to-end API ownership.")
        if any(project.startswith("CareerPilot") for project in projects):
            explanations.append("CareerPilot AI provides direct multi-agent workflow and orchestration-system evidence.")
        if projects and not explanations:
            project = projects[0]
            if project.startswith("Drowsy"):
                explanations.append("Drowsy Driver Detection provides OpenCV/object-detection evidence plus award recognition.")
            elif project.startswith("XAUUSD"):
                explanations.append("XAUUSD provides feature-engineering, ensemble-model, validation, and deployment evidence.")
            else:
                explanations.append(f"{project} provides direct project evidence for this role category.")
        if job.seniority_level == "Founding/Lead":
            explanations.append(
                "Multiple self-owned projects show a startup ownership mindset, though not regulated production ownership."
            )
        groups = [
            ({"ComfyUI", "Stable Diffusion", "Diffusion Models", "Image Generation", "LoRA"},
             "ComfyUI, diffusion/image-generation, and LoRA experience align with the creative-AI workflow."),
            ({"FastAPI", "REST APIs"}, "FastAPI and REST API work support backend integration requirements."),
            ({"LLM APIs", "RAG", "Hugging Face"}, "LLM API and model-integration experience match the GenAI application layer."),
            ({"OpenCV", "Computer Vision", "Object Detection"}, "OpenCV and object-detection work match the computer-vision requirements."),
        ]
        matched_set = set(matched)
        for skills, explanation in groups:
            if matched_set.intersection(skills):
                explanations.append(explanation)
        covered = set().union(*(skills for skills, _ in groups))
        for skill in matched:
            if skill not in covered:
                explanations.append(f"{skill} is explicitly requested and present in the candidate profile.")
        return explanations[:7]

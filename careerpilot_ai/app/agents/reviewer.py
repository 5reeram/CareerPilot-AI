import re

from careerpilot_ai.app.agents.answer_writer import ApplicationAnswerAgent
from careerpilot_ai.app.schemas import FitScore, ParsedJob, ReviewResult


class ReviewerAgent:
    """A deterministic critic that both flags and repairs common application-answer failures."""

    def review(
        self, answer: str, job: ParsedJob, fit: FitScore,
        character_limit: int | None = None,
    ) -> ReviewResult:
        issues: list[str] = []
        suggestions: list[str] = []
        improvements: list[str] = []
        revised = re.sub(r"[ \t]+", " ", answer).strip()
        revised = re.sub(r"\n{3,}", "\n\n", revised)

        if any(len(sentence) > 350 for sentence in re.split(r"(?<=[.!?])\s+", revised)):
            issues.append("The draft copies or paraphrases too much of the JD in one sentence.")
            suggestions.append("Summarize the role focus in one short, candidate-centered phrase.")
            revised = re.sub(
                r"because it (?:centers on|combines) .*?(?=My strongest evidence)",
                f"because it focuses on {job.domain.lower()} work aligned with my background. ",
                revised,
                flags=re.IGNORECASE,
            )
            improvements.append("Condensed an oversized JD-derived sentence.")

        if len(revised) > 1_500:
            issues.append("The answer is too long for a typical application field.")
            suggestions.append("Keep the answer below roughly 250 words.")
            revised = revised[:1_450].rsplit(" ", 1)[0] + "."
            improvements.append("Reduced the answer to application-friendly length.")
        if len(revised.split()) < 70:
            issues.append("The answer is too brief to establish company interest and credible evidence.")
            suggestions.append("Add one concrete project outcome and explain its relevance to this role.")

        company = job.company_name
        if company != "Unknown company" and company.casefold() not in revised.casefold():
            issues.append("The company is not named.")
            suggestions.append("Name the company to make the answer clearly role-specific.")
            revised = f"I'm specifically interested in {company}. " + revised
            improvements.append("Added explicit company specificity.")

        project = fit.relevant_projects[0] if fit.relevant_projects else ""
        if project and project.casefold() not in revised.casefold():
            issues.append("The strongest relevant project is missing.")
            suggestions.append("Use the strongest project as evidence instead of making a generic fit claim.")
            revised += f" My most relevant example is {project}."
            improvements.append("Added the strongest role-relevant project.")

        matched = getattr(fit, "matched_skills", [])
        keyword_hits = [skill for skill in matched[:6] if skill.casefold() in revised.casefold()]
        if matched and not keyword_hits:
            issues.append("Important matched JD keywords are absent.")
            suggestions.append("Mention a small number of supported JD keywords naturally.")
            revised += f" My directly relevant tools include {', '.join(matched[:3])}."
            improvements.append("Added supported ATS keywords without keyword stuffing.")

        inflated = ("expert in every", "perfect fit", "guaranteed", "10x", "unmatched expertise")
        if any(term in revised.casefold() for term in inflated):
            issues.append("The draft includes an inflated claim.")
            suggestions.append("Replace absolutes with evidence from delivered projects.")
            for term in inflated:
                revised = re.sub(re.escape(term), "relevant experience", revised, flags=re.IGNORECASE)
            improvements.append("Removed inflated or absolute claims.")

        ai_phrases = ("delve into", "ever-evolving landscape", "leverage my unique", "synergy")
        if any(term in revised.casefold() for term in ai_phrases):
            issues.append("The wording contains generic AI-style phrasing.")
            suggestions.append("Use direct, plain language grounded in actual work.")
            for term in ai_phrases:
                revised = re.sub(re.escape(term), "work with", revised, flags=re.IGNORECASE)
            improvements.append("Replaced generic AI-sounding language with direct wording.")

        if character_limit and len(revised) > character_limit:
            issues.append(f"The answer exceeds the {character_limit}-character application limit.")
            suggestions.append("Keep the strongest evidence while respecting the application limit.")
            revised = ApplicationAnswerAgent._fit_character_limit(
                revised, revised, character_limit,
            )
            improvements.append(f"Reduced the final answer to {character_limit} characters or fewer.")

        if not improvements:
            improvements.append("Preserved the draft because it already used company context, project evidence, and supported skills.")
        status = "Needs Revision" if issues else "Approved"
        why = (
            "The final answer connects a concrete project to the role, uses supported JD terminology, "
            "and distinguishes demonstrated experience from ramp-up areas."
        )
        return ReviewResult(
            status=status,
            issues_found=issues,
            improvement_suggestions=suggestions,
            improvements_made=improvements,
            why_stronger=why,
            revised_output=revised,
        )

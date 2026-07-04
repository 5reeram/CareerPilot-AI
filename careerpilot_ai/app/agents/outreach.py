from careerpilot_ai.app.schemas import FitScore, OutreachMessages, ParsedJob


class OutreachAgent:
    def generate(self, job: ParsedJob, fit: FitScore) -> OutreachMessages:
        company = job.company_name if job.company_name != "Unknown company" else "your company"
        role = job.role_title if job.role_title != "Unknown role" else job.domain + " role"
        project = fit.relevant_projects[0] if fit.relevant_projects else "my applied AI projects"
        skills = fit.matched_skills[:3]
        skill_text = ", ".join(skills) if skills else job.domain
        recruiter = (
            f"Hi, I recently came across the {role} opening at {company}.\n"
            f"My work on {project}, together with hands-on experience in {skill_text}, aligns well with the role.\n"
            "I would appreciate it if you could review my profile or point me to the appropriate hiring contact.\n"
            "Thank you for your time."
        )
        follow_up = (
            f"Hi, I wanted to follow up on my application for the {role} role at {company}. "
            f"I remain very interested, particularly because my experience with {project} aligns with the work. "
            "Please let me know if I can provide any additional information."
        )
        return OutreachMessages(recruiter_message=recruiter, follow_up_message=follow_up)

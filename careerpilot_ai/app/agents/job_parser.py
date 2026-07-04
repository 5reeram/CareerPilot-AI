import re

from careerpilot_ai.app.schemas import JobInput, ParsedJob


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "SQL": ("sql",),
    "FastAPI": ("fastapi", "fast api"),
    "REST APIs": ("rest api", "restful"),
    "Streamlit": ("streamlit",),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "Scikit-learn": ("scikit-learn", "sklearn"),
    "TensorFlow": ("tensorflow",),
    "PyTorch": ("pytorch", "torch"),
    "XGBoost": ("xgboost",),
    "OpenCV": ("opencv",),
    "Computer Vision": ("computer vision",),
    "Object Detection": ("object detection",),
    "OCR": ("ocr", "optical character recognition"),
    "NLP": ("nlp", "natural language processing"),
    "LLM APIs": ("llm api", "large language model", "openai", "openrouter", "llm", "llms"),
    "RAG": ("rag", "retrieval augmented"),
    "Hugging Face": ("hugging face", "huggingface"),
    "Stable Diffusion": ("stable diffusion",),
    "Diffusion Models": ("diffusion model", "diffusion image model", "flux-klein", "flux"),
    "ComfyUI": ("comfyui", "comfy ui"),
    "LoRA": ("lora", "qlora"),
    "Image Generation": ("image generation", "image/video generation", "image synthesis", "diffusion image"),
    "Video Generation": ("video generation", "image/video generation", "video model"),
    "LTX-2": ("ltx-2", "ltx 2"),
    "WAN Animate": ("wan animate", "wan-animate"),
    "Docker": ("docker", "containerization"),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure",),
    "GCP": ("gcp", "google cloud"),
    "MLOps": ("mlops", "model monitoring", "model registry"),
    "Git": ("git", "github"),
    "MySQL": ("mysql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "Redis": ("redis",),
    "Agentic AI": ("agentic ai", "ai agent", "multi-agent"),
    "LangGraph": ("langgraph",),
    "Backend Architecture": ("backend architecture", "backend platform", "backend systems"),
    "AI Layer": ("ai layer",),
    "Orchestration Engine": ("orchestration engine", "workflow orchestration", "agent orchestration"),
    "Fine-tuning & Evaluation": ("fine-tuning", "fine tuning", "evaluation framework", "model evaluation"),
    "Scheduling Logic": ("scheduling logic", "job scheduling", "task scheduling"),
    "Cloud Infrastructure": ("cloud infrastructure", "cloud platform", "cloud-native"),
    "Message Queues": ("message queue", "queues", "rabbitmq", "sqs", "kafka"),
    "Event-driven Systems": ("event-driven", "event driven", "event bus"),
    "Authentication & Authorization": ("authentication", "authorization", "oauth", "jwt", "auth/rbac"),
    "Observability": ("observability", "distributed tracing", "production monitoring"),
    "Temporal": ("temporal",),
    "Healthcare Domain": ("healthcare", "health-tech", "clinical workflow"),
    "Privacy & PDPL": ("privacy", "pdpl", "personal data protection law"),
    "FHIR": ("fhir",),
    "NPHIES": ("nphies",),
    "Regulated Data Systems": ("regulated data", "regulated clinical data", "clinical data system", "health data"),
    "Clinical Evaluation Harnesses": ("clinical evaluation", "evaluation harness"),
    "Healthcare-grade Reliability": ("healthcare-grade reliability", "clinical-grade reliability"),
}


class JobParserAgent:
    def parse(self, job_input: JobInput) -> ParsedJob:
        text = job_input.description
        lower = text.lower()
        inferred_skills = [
            skill for skill, aliases in SKILL_ALIASES.items()
            if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lower) for alias in aliases)
        ]
        tagged_skills = [self._normalize_platform_skill(skill) for skill in job_input.platform_skills]
        skills = list(dict.fromkeys(inferred_skills + [skill for skill in tagged_skills if skill]))

        preferred_section = self._section(text, ("preferred", "nice to have", "good to have"))
        preferred_skills = [skill for skill in skills if skill.lower() in preferred_section.lower()]
        required_skills = [skill for skill in skills if skill not in preferred_skills]

        experience_match = re.search(
            r"(?:at least\s+)?(\d+)(?:\s*[-–]\s*(\d+))?\+?\s*(?:years?|yrs?)",
            lower,
        )
        required_experience = (
            experience_match.group(0) + " experience" if experience_match else "Not specified"
        )
        years = int(experience_match.group(1)) if experience_match else 0

        remote_policy = "Remote" if "remote" in lower else "Hybrid" if "hybrid" in lower else "On-site" if "on-site" in lower or "onsite" in lower else "Not specified"
        location = self._extract_label(text, ("location",)) or "Not specified"
        salary = self._extract_salary(text)
        role = job_input.role_title or self._extract_label(text, ("role", "job title", "position"))
        company = job_input.company_name or self._extract_label(text, ("company", "organization"))

        domain = self._domain(lower)
        ownership_role = any(term in lower for term in (
            "founding engineer", "founding ai", "exceptional ownership", "technical lead", "lead engineer",
        ))
        seniority = (
            "Founding/Lead" if ownership_role else "Senior" if years >= 5 or "senior" in lower
            else "Mid-level" if years >= 2 else "Entry/Associate"
        )
        red_flags = []
        if years >= 5:
            red_flags.append(f"Role asks for {years}+ years of experience.")
        if any(term in lower for term in ("24/7", "unpaid", "commission only")):
            red_flags.append("The description contains a potentially concerning work condition.")

        # Pasted JDs often arrive as one giant paragraph. Sentence splitting
        # prevents downstream writers from treating the entire advert as a task.
        sentences = [
            sentence.strip(" •-*\t")
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
            if len(sentence.strip()) > 20
        ]
        responsibilities = [
            line[:300] for line in sentences
            if any(word in line.lower() for word in ("build", "develop", "design", "deploy", "maintain", "responsib"))
        ][:6]
        company_highlights = [
            line[:300] for line in sentences
            if any(signal in line.lower() for signal in (
                "million user", "billion", "real-estate", "real estate", "head of ai",
            ))
        ][:4]

        return ParsedJob(
            company_name=company or "Unknown company",
            role_title=role or self._infer_role(text) or "Unknown role",
            location=location,
            remote_policy=remote_policy,
            salary_range=salary,
            required_experience=required_experience,
            employment_type=self._employment_type(lower),
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            responsibilities=responsibilities,
            company_highlights=company_highlights,
            keywords_for_ats=skills,
            domain=domain,
            seniority_level=seniority,
            red_flags=red_flags,
            application_questions=[],
        )

    @staticmethod
    def _extract_label(text: str, labels: tuple[str, ...]) -> str:
        pattern = rf"(?im)^(?:{'|'.join(map(re.escape, labels))})\s*:\s*(.+)$"
        match = re.search(pattern, text)
        return match.group(1).strip()[:200] if match else ""

    @staticmethod
    def _extract_salary(text: str) -> str:
        match = re.search(
            r"(?i)(?:₹|\$|€|£|INR|USD)\s?[\d,.]+(?:\s*[-–]\s*(?:₹|\$|€|£|INR|USD)?\s?[\d,.]+)?(?:\s*(?:LPA|lakhs?|k|per annum|/year))?",
            text,
        )
        return match.group(0) if match else "Not specified"

    @staticmethod
    def _section(text: str, headings: tuple[str, ...]) -> str:
        pattern = rf"(?is)(?:{'|'.join(map(re.escape, headings))})[^\n]*\n(.*?)(?:\n\s*\n|\Z)"
        match = re.search(pattern, text)
        return match.group(1) if match else ""

    @staticmethod
    def _infer_role(text: str) -> str:
        for line in text.splitlines()[:8]:
            if re.search(r"(?i)(engineer|developer|scientist|specialist)", line) and len(line) < 120:
                return line.strip(" •-*\t")
        return ""

    @staticmethod
    def _domain(lower: str) -> str:
        if "backend" in lower and any(x in lower for x in ("agentic", "healthcare", "clinical")):
            return "AI Backend"
        if any(x in lower for x in ("diffusion", "comfyui", "generative ai", "llm")):
            return "Generative AI"
        if any(x in lower for x in ("computer vision", "object detection", "ocr")):
            return "Computer Vision"
        if any(x in lower for x in ("machine learning", "ml engineer", "data science")):
            return "Machine Learning"
        if "fastapi" in lower or "backend" in lower:
            return "AI Backend"
        return "AI/Software"

    @staticmethod
    def _normalize_platform_skill(value: str) -> str:
        cleaned = value.strip()
        normalized = cleaned.casefold()
        if not cleaned:
            return ""
        for skill, aliases in SKILL_ALIASES.items():
            if normalized == skill.casefold() or normalized in {alias.casefold() for alias in aliases}:
                return skill
        return cleaned

    @staticmethod
    def _employment_type(lower: str) -> str:
        for value in ("full-time", "part-time", "contract", "internship"):
            if value in lower:
                return value.title()
        return "Not specified"

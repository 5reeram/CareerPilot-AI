import pytest

from careerpilot_ai.app.agents.fit_scorer import FitScoringAgent
from careerpilot_ai.app.profile import SHASHI_PROFILE
from careerpilot_ai.app.schemas import JobInput, Recommendation
from careerpilot_ai.app.workflow import CareerPilotWorkflow


@pytest.fixture
def workflow() -> CareerPilotWorkflow:
    return CareerPilotWorkflow()


def test_genai_job_is_high_match(workflow: CareerPilotWorkflow) -> None:
    package = workflow.run(JobInput(
        company_name="SquareYards",
        role_title="Generative AI Engineer",
        description="""
        We are hiring a Generative AI Engineer to build image generation workflows.
        Required skills include Python, ComfyUI, LoRA, diffusion models, LLM APIs,
        and image generation. You will develop and deploy reliable AI workflows,
        collaborate with product teams, and improve generated image quality.
        This is a remote full-time opportunity in India.
        """,
    ))
    assert package.fit.recommendation == Recommendation.APPLY
    assert package.fit.overall_score >= 75
    assert package.fit.relevant_projects[0] == "Ghostverse.ai GenAI Storybook Platform"
    assert "SquareYards" in package.review.revised_output


def test_senior_mlops_job_does_not_overstate_fit(workflow: CareerPilotWorkflow) -> None:
    package = workflow.run(JobInput(
        company_name="ScaleCloud",
        role_title="Senior ML Engineer",
        description="""
        Senior ML Engineer responsible for designing large-scale cloud ML platforms.
        At least 5+ years of experience required. Must have Python, Kubernetes, Docker,
        AWS, MLOps, model registries, distributed systems, and production monitoring.
        You will build and maintain multi-region infrastructure and mentor engineers.
        This is a full-time on-site position in Bengaluru.
        """,
    ))
    assert package.fit.recommendation in (
        Recommendation.MAYBE, Recommendation.STRETCH, Recommendation.SKIP,
    )
    assert "Kubernetes" in package.fit.missing_skills
    assert package.fit.experience_match <= 40
    assert 40 <= package.fit.overall_score <= 60
    assert package.fit.risks


def test_short_description_is_rejected() -> None:
    with pytest.raises(ValueError):
        JobInput(description="Python role")


def test_answer_summarizes_instead_of_copying_a_long_jd(workflow: CareerPilotWorkflow) -> None:
    package = workflow.run(JobInput(
        company_name="SquareYards",
        role_title="Generative AI Engineer",
        description=(
            "One of our AI products is used by 9 million users every month and we are hiring. "
            "The engineer will work across every business area in our ten-billion-dollar real-estate "
            "operation and report directly to the Head of AI while monitoring every new AI development. "
            "Required skills include Python, ComfyUI, LoRA, open-source diffusion models, LLM APIs, "
            "image generation, and production API development. The role requires at least 1 year of "
            "coding experience and ownership of innovative monthly-million-user AI applications."
        ),
    ))
    answer = package.review.revised_output
    assert "9 million users every month" not in answer
    assert answer.count("Ghostverse.ai GenAI Storybook Platform") == 1
    assert len(answer) < 1_200
    assert "story and image generation" in answer


def test_squareyards_package_meets_mvp_acceptance_criteria(workflow: CareerPilotWorkflow) -> None:
    package = workflow.run(JobInput(
        company_name="SquareYards",
        role_title="Generative AI Engineer",
        description=(
            "One of our AI products is used by 9 million users every month in our real-estate business. "
            "We need at least 1 year of coding experience in GenAI, specializing in open-source diffusion "
            "image models such as the Flux-Klein family, video generation models such as LTX-2, and tooling "
            "including ComfyUI and LoRA training. You will build innovative AI applications at monthly-million-user "
            "scale, improve product workflows, and report directly to the Head of AI. This is a full-time role."
        ),
    ))
    assert package.job.domain == "Generative AI"
    assert 78 <= package.fit.overall_score <= 88
    assert package.fit.recommendation == Recommendation.APPLY
    assert "LTX-2" in package.fit.missing_skills
    assert any("Ghostverse.ai" in match for match in package.fit.strong_matches)
    assert any("Ghostverse.ai" in project for project in package.cv_suggestions.projects_to_move_up)
    assert "SquareYards" in package.review.revised_output
    assert "million" in package.review.revised_output
    assert "Generative AI Engineer" in package.outreach.recruiter_message
    assert package.review.why_stronger


def test_parallel_dots_cv_role_surfaces_salary_warning(workflow: CareerPilotWorkflow) -> None:
    package = workflow.run(JobInput(
        company_name="ParallelDots",
        role_title="Machine Learning / Computer Vision Engineer",
        description=(
            "We need an ML Engineer with 1 year experience in Python, PyTorch, Computer Vision, "
            "Image Classification, Object Detection, OCR, NLP and FastAPI. This is a remote full-time "
            "role with salary INR 6-8 LPA for building and deploying production vision systems."
        ),
    ))
    assert package.job.domain == "Computer Vision"
    assert 75 <= package.fit.overall_score <= 85
    assert package.fit.salary_match == 45
    assert any("salary" in risk.casefold() for risk in package.fit.risks)
    assert package.fit.relevant_projects[0] == "Drowsy Driver Detection"
    assert any("Techathon" in bullet for bullet in package.cv_suggestions.experience_bullets)


def test_vitarc_founding_backend_is_a_neutral_salary_stretch(workflow: CareerPilotWorkflow) -> None:
    package = workflow.run(JobInput(
        company_name="Vitarc",
        role_title="Founding AI Backend Engineer",
        portal="Wellfound",
        platform_skills=[
            "Python", "Redis", "PostgreSQL", "OCR", "Docker", "FastAPI",
            "Temporal", "LLMs", "RAG", "LangGraph", "Agentic AI",
        ],
        description=(
            "Vitarc is building a healthcare agentic platform and needs a founding engineer with exceptional "
            "ownership of backend architecture, the orchestration engine, and the AI layer. Build cloud "
            "infrastructure, message queues, event-driven systems, authentication, production observability, "
            "and healthcare-grade reliability. Own fine-tuning and evaluation, OCR pipelines, scheduling logic, "
            "RAG, Temporal and LangGraph workflows. The platform handles regulated clinical data and requires "
            "privacy, PDPL, FHIR, NPHIES, and clinical evaluation harnesses. This is a remote full-time role."
        ),
    ))

    required = set(package.job.required_skills)
    assert {"Redis", "PostgreSQL", "Temporal", "LLM APIs", "RAG", "LangGraph", "Agentic AI"} <= required
    assert {"Backend Architecture", "Orchestration Engine", "Event-driven Systems", "Privacy & PDPL"} <= required
    assert 52 <= package.fit.overall_score <= 56
    assert package.fit.recommendation == Recommendation.STRETCH
    assert package.fit.salary_match == 50
    assert 35 <= package.fit.experience_match <= 45
    assert "ownership" in package.fit.reasoning.casefold()
    assert "stretch apply" in package.fit.reasoning.casefold()
    assert "Salary not mentioned. Verify before serious commitment." in package.fit.risks
    assert any("Ghostverse" in match for match in package.fit.strong_matches)
    assert any("CareerPilot" in match for match in package.fit.strong_matches)
    for missing in (
        "Healthcare Domain", "Privacy & PDPL", "FHIR", "NPHIES", "Cloud Infrastructure",
        "Message Queues", "Event-driven Systems", "Temporal", "Observability",
        "Clinical Evaluation Harnesses", "Regulated Data Systems",
    ):
        assert missing in package.fit.missing_skills

    case_variant_job = package.job.model_copy(update={
        "required_skills": [skill.swapcase() for skill in package.job.required_skills],
    })
    case_variant_fit = FitScoringAgent().score(case_variant_job, SHASHI_PROFILE)
    assert 35 <= case_variant_fit.experience_match <= 45
    assert case_variant_fit.recommendation == Recommendation.STRETCH


def test_business_gtv_is_not_parsed_as_salary(workflow: CareerPilotWorkflow) -> None:
    package = workflow.run(JobInput(
        company_name="Vitarc",
        role_title="Founding AI Backend Engineer",
        description=(
            "Vitarc operates across more than $10+ Billion GTV in its business areas and is hiring a founding "
            "AI backend engineer. The role owns FastAPI services, LLM workflows, backend architecture, cloud "
            "infrastructure, event-driven systems, observability, privacy, and healthcare-grade reliability. "
            "No candidate compensation information is provided in this job description."
        ),
    ))

    assert package.job.salary_range == "Not specified"
    assert package.fit.salary_match == 50
    assert "Salary not mentioned. Verify before serious commitment." in package.fit.risks

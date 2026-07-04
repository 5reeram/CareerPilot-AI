from datetime import date, timedelta
from pathlib import Path
import sys

# Streamlit executes this file as a script. Keep package imports stable even
# when an IDE launches it from a different working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from careerpilot_ai.app.db import SessionLocal, init_db
from careerpilot_ai.app.schemas import JobInput, TrackerCreate, TrackerStatus, TrackerUpdate
from careerpilot_ai.app.services.excel import ExcelService
from careerpilot_ai.app.services.llm_client import LLMClient
from careerpilot_ai.app.services.tracker import DuplicateApplicationError, TrackerService
from careerpilot_ai.app.workflow import CareerPilotWorkflow


st.set_page_config(page_title="CareerPilot AI", page_icon="🧭", layout="wide")
init_db()
workflow = CareerPilotWorkflow()
tracker = TrackerService()
llm_client = LLMClient()


def bullet_list(items: list[str], empty_message: str = "None detected") -> None:
    if not items:
        st.caption(empty_message)
        return
    for item in items:
        st.markdown(f"- {item}")


def tracker_payload(package, final_answer: str, recruiter_message: str,
                    follow_up_message: str, follow_up_date: date,
                    status: TrackerStatus) -> TrackerCreate:
    job, fit = package.job, package.fit
    meta = st.session_state.get("job_meta", {"portal": "Manual", "job_link": ""})
    cv = getattr(package, "cv_suggestions", None)
    return TrackerCreate(
        company=job.company_name,
        role=job.role_title,
        portal=meta["portal"],
        job_link=meta["job_link"],
        location=job.location,
        remote_policy=job.remote_policy,
        salary_range=job.salary_range,
        required_experience=job.required_experience,
        role_category=job.domain,
        match_score=fit.overall_score,
        skill_score=fit.skill_match,
        project_score=fit.project_match,
        experience_score=fit.experience_match,
        salary_score=fit.salary_match,
        location_score=fit.location_match,
        growth_score=fit.growth_value,
        recommendation=fit.recommendation,
        status=status,
        strong_matches=fit.strong_matches,
        missing_skills=fit.missing_skills,
        best_projects=fit.relevant_projects,
        cv_version_name=cv.cv_version_name if cv else "",
        application_answer=final_answer,
        recruiter_message=recruiter_message,
        follow_up_message=follow_up_message,
        follow_up_date=follow_up_date,
        date_applied=date.today() if status == TrackerStatus.APPLIED else None,
    )


def save_analysis(package, final_answer: str, recruiter_message: str,
                  follow_up_message: str, follow_up_date: date,
                  status: TrackerStatus) -> int:
    record_id = st.session_state.get("saved_record_id")
    with SessionLocal() as session:
        if record_id:
            updated = tracker.update(session, record_id, TrackerUpdate(
                status=status,
                application_answer=final_answer,
                recruiter_message=recruiter_message,
                follow_up_message=follow_up_message,
                follow_up_date=follow_up_date,
                date_applied=date.today() if status == TrackerStatus.APPLIED else None,
            ))
            if updated:
                return updated.id
        payload = tracker_payload(
            package, final_answer, recruiter_message, follow_up_message,
            follow_up_date, status,
        )
        try:
            saved = tracker.add(session, payload)
            st.session_state.duplicate_detected = False
            return saved.id
        except DuplicateApplicationError as exc:
            tracker.update(session, exc.record_id, TrackerUpdate(
                status=status,
                application_answer=final_answer,
                recruiter_message=recruiter_message,
                follow_up_message=follow_up_message,
                follow_up_date=follow_up_date,
                date_applied=date.today() if status == TrackerStatus.APPLIED else None,
            ))
            st.session_state.duplicate_detected = True
            return exc.record_id


st.title("🧭 CareerPilot AI")
st.caption("Paste JD → analyze fit → prepare application → review → track")
st.sidebar.header("Settings")
if llm_client.configured:
    st.sidebar.success(f"LLM mode: Enabled\n\nModel: {llm_client.settings.llm_model}")
else:
    st.sidebar.info("LLM mode: Disabled\n\nUsing deterministic writing fallback.")

message = st.session_state.pop("action_message", None)
if message:
    st.success(message)

analyze_tab, tracker_tab = st.tabs(["Analyze & prepare", "Tracker & Excel"])

with analyze_tab:
    with st.form("job_form"):
        left, right = st.columns(2)
        company = left.text_input("Company (optional)")
        role = right.text_input("Role (optional)")
        portal = left.text_input("Portal", value="Manual")
        job_link = right.text_input("Job link (optional)")
        platform_tags = st.text_input(
            "Platform skill tags (optional, comma-separated)",
            help="Paste Wellfound skill tags here; they are merged with skills inferred from the full JD.",
        )
        application_question = st.text_input(
            "Application question",
            value="What interests you about working for this company?",
        )
        character_limit = st.number_input(
            "Answer character limit (optional; 0 means no limit)",
            min_value=0, max_value=10_000, value=0, step=50,
        )
        description = st.text_area("Paste job description", height=280)
        submitted = st.form_submit_button("Analyze and prepare", type="primary")

    if submitted:
        try:
            st.session_state.package = workflow.run(
                JobInput(
                    description=description,
                    company_name=company,
                    role_title=role,
                    portal=portal,
                    job_link=job_link,
                    platform_skills=[tag.strip() for tag in platform_tags.split(",") if tag.strip()],
                ),
                question=application_question.strip() or "Why are you a good fit for this role?",
                character_limit=int(character_limit) or None,
            )
            st.session_state.job_meta = {"portal": portal, "job_link": job_link}
            st.session_state.saved_record_id = None
        except ValueError as exc:
            st.error(f"Please check the job description: {exc}")

    package = st.session_state.get("package")
    if package:
        fit, job = package.fit, package.job
        cv = getattr(package, "cv_suggestions", None)
        outreach = getattr(package, "outreach", None)
        st.sidebar.caption(f"Last writing run: {getattr(package, 'writing_mode', 'Deterministic')}")
        writing_warning = getattr(package, "writing_warning", "")
        if writing_warning:
            st.warning(writing_warning)
        st.divider()

        top = st.columns(5)
        values = (
            ("Overall fit", f"{fit.overall_score}%"),
            ("Recommendation", fit.recommendation.value),
            ("Detected role", job.role_title),
            ("Salary match", f"{fit.salary_match}%"),
            ("Experience match", f"{fit.experience_match}%"),
        )
        for column, (label, value) in zip(top, values):
            column.metric(label, value)

        with st.expander("1. Why this score", expanded=True):
            st.write(fit.reasoning)
            metrics = {
                "Skills": fit.skill_match,
                "Projects": fit.project_match,
                "Experience": fit.experience_match,
                "Salary": fit.salary_match,
                "Location": fit.location_match,
                "Growth": fit.growth_value,
            }
            st.bar_chart(metrics)
            if fit.risks:
                st.warning(" ".join(fit.risks))

        with st.expander("2. Parsed job details"):
            a, b = st.columns(2)
            a.markdown(f"**Company:** {job.company_name}")
            a.markdown(f"**Role:** {job.role_title}")
            a.markdown(f"**Location:** {job.location}")
            a.markdown(f"**Remote policy:** {job.remote_policy}")
            a.markdown(f"**Salary:** {job.salary_range}")
            b.markdown(f"**Required experience:** {job.required_experience}")
            b.markdown(f"**Employment type:** {job.employment_type}")
            b.markdown(f"**Category:** {job.domain}")
            b.markdown(f"**Seniority:** {job.seniority_level}")
            st.markdown("**Required skills**")
            bullet_list(job.required_skills)
            st.markdown("**Preferred skills**")
            bullet_list(job.preferred_skills)
            st.markdown("**Responsibilities**")
            bullet_list(job.responsibilities)
            st.markdown("**ATS keywords:** " + (", ".join(job.keywords_for_ats) or "None detected"))
            if job.red_flags:
                st.markdown("**Red flags**")
                bullet_list(job.red_flags)

        match_col, gap_col = st.columns(2)
        with match_col.container(border=True):
            st.subheader("3. Strong matches")
            bullet_list(fit.strong_matches, "No strong match was detected.")
        with gap_col.container(border=True):
            st.subheader("4. Missing / weak skills")
            bullet_list(
                [f"{skill} is requested but not clearly evidenced in the profile." for skill in fit.missing_skills],
                "No material missing skill was detected. Verify this manually.",
            )

        with st.expander("5. Best projects to highlight", expanded=True):
            bullet_list(fit.relevant_projects, "No clear project match was detected.")
            st.info(fit.how_to_position_candidate)

        with st.expander("6. Tailored CV suggestions", expanded=True):
            if not cv:
                st.warning("This result predates CV suggestions. Analyze the JD again to refresh it.")
            else:
                st.markdown(f"**Suggested headline:** {cv.suggested_headline}")
                st.markdown(f"**Tailored summary:** {cv.tailored_summary}")
                with st.expander("Copy tailored CV summary"):
                    st.code(cv.tailored_summary, language=None)
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Skills to move up**")
                    bullet_list(cv.skills_to_move_up)
                    st.markdown("**Projects to move up**")
                    bullet_list(cv.projects_to_move_up)
                with c2:
                    st.markdown("**Experience bullets to emphasize**")
                    bullet_list(cv.experience_bullets)
                    st.markdown("**Items to reduce**")
                    bullet_list(cv.items_to_reduce)
                st.markdown("**ATS keywords:** " + (", ".join(cv.ats_keywords) or "None detected"))
                st.code(cv.cv_version_name, language=None)

        st.subheader("7. Application answer")
        initial_answer = package.review.revised_output
        final_answer = st.text_area(
            package.answer.question,
            value=initial_answer,
            height=260,
            key=f"answer_{hash(initial_answer)}",
        )
        st.caption(f"{len(final_answer)} characters")
        with st.expander("Copy application answer"):
            st.code(final_answer, language=None)

        with st.expander("8. Reviewer feedback", expanded=True):
            review = package.review
            status_method = st.success if review.status == "Approved" else st.warning
            status_method(f"Reviewer status: {review.status}")
            st.markdown("**Issues found**")
            bullet_list(review.issues_found, "No blocking issues found.")
            st.markdown("**Improvement suggestions**")
            bullet_list(review.improvement_suggestions, "No further automatic revision was required.")
            st.markdown("**What was improved**")
            bullet_list(getattr(review, "improvements_made", []))
            why_stronger = getattr(review, "why_stronger", "")
            if why_stronger:
                st.info(why_stronger)

        st.subheader("9. Recruiter and follow-up messages")
        recruiter_default = outreach.recruiter_message if outreach else "Re-analyze the JD to generate this message."
        follow_up_default = outreach.follow_up_message if outreach else "Re-analyze the JD to generate this message."
        recruiter_message = st.text_area(
            "LinkedIn recruiter message", value=recruiter_default, height=150,
            key=f"recruiter_{hash(recruiter_default)}",
        )
        with st.expander("Copy recruiter message"):
            st.code(recruiter_message, language=None)
        follow_up_message = st.text_area(
            "Follow-up message (send after 5–7 days)", value=follow_up_default, height=130,
            key=f"followup_{hash(follow_up_default)}",
        )
        with st.expander("Copy follow-up message"):
            st.code(follow_up_message, language=None)

        st.subheader("10. Tracker actions")
        follow_up_date = st.date_input("Planned follow-up date", value=date.today() + timedelta(days=7))
        approved = st.checkbox("I reviewed the final content and confirm any application submission myself")
        action_columns = st.columns(4)

        if action_columns[0].button("Save Draft", type="primary"):
            record_id = save_analysis(
                package, final_answer, recruiter_message, follow_up_message,
                follow_up_date, TrackerStatus.READY,
            )
            st.session_state.saved_record_id = record_id
            st.session_state.action_message = (
                f"Existing application #{record_id} updated as Ready to Apply."
                if st.session_state.pop("duplicate_detected", False)
                else f"Application #{record_id} saved as Ready to Apply."
            )
            st.rerun()

        if action_columns[1].button("Mark as Applied", disabled=not approved):
            record_id = save_analysis(
                package, final_answer, recruiter_message, follow_up_message,
                follow_up_date, TrackerStatus.APPLIED,
            )
            st.session_state.saved_record_id = record_id
            st.session_state.action_message = (
                f"Existing application #{record_id} updated and marked Applied."
                if st.session_state.pop("duplicate_detected", False)
                else f"Application #{record_id} marked Applied by your explicit action."
            )
            st.rerun()

        if action_columns[2].button("Skip Job"):
            record_id = save_analysis(
                package, final_answer, recruiter_message, follow_up_message,
                follow_up_date, TrackerStatus.SKIPPED,
            )
            st.session_state.saved_record_id = record_id
            st.session_state.action_message = (
                f"Existing application #{record_id} updated and marked Skipped."
                if st.session_state.pop("duplicate_detected", False)
                else f"Application #{record_id} marked Skipped."
            )
            st.rerun()

        with SessionLocal() as session:
            current_records = tracker.list(session)
        action_columns[3].download_button(
            "Export / Update Excel",
            data=ExcelService().export(current_records),
            file_name="careerpilot_tracker.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

with tracker_tab:
    with SessionLocal() as session:
        records = tracker.list(session)

    found = len(records)
    applied = sum(record.date_applied is not None for record in records)
    interviews = sum(record.status.value.startswith("Interview") for record in records)
    offers = sum(record.status == TrackerStatus.OFFER for record in records)
    due_records = tracker.follow_ups_due(records)
    due_ids = {record.id for record in due_records}
    columns = st.columns(5)
    for column, label, value in zip(
        columns, ("Found", "Applied", "Interviews", "Offers", "Follow-ups due"),
        (found, applied, interviews, offers, len(due_records)),
    ):
        column.metric(label, value)

    if records:
        st.markdown("### Filters")
        f1, f2, f3 = st.columns(3)
        status_filter = f1.multiselect("Status", sorted({r.status.value for r in records}))
        recommendation_filter = f2.multiselect(
            "Recommendation", sorted({r.recommendation.value for r in records})
        )
        portal_filter = f3.multiselect("Portal", sorted({r.portal for r in records}))
        f4, f5, f6 = st.columns(3)
        company_filter = f4.text_input("Company contains", key="tracker_company_filter")
        role_filter = f5.text_input("Role contains", key="tracker_role_filter")
        follow_up_due_only = f6.checkbox("Follow-ups due only")

        filtered = [
            record for record in records
            if (not status_filter or record.status.value in status_filter)
            and (not recommendation_filter or record.recommendation.value in recommendation_filter)
            and (not portal_filter or record.portal in portal_filter)
            and (not company_filter or company_filter.casefold() in record.company.casefold())
            and (not role_filter or role_filter.casefold() in record.role.casefold())
            and (not follow_up_due_only or record.id in due_ids)
        ]
        rows = [{
            "ID": r.id,
            "Company": r.company,
            "Role": r.role,
            "Category": r.role_category,
            "Portal": r.portal,
            "Score": r.match_score,
            "Recommendation": r.recommendation.value,
            "Status": r.status.value,
            "Follow-up": r.follow_up_date,
        } for r in filtered]
        st.dataframe(rows, width="stretch", hide_index=True)

        st.markdown("### Update an application")
        record_id = st.selectbox("Application", options=[r.id for r in records])
        selected = next(r for r in records if r.id == record_id)
        update_left, update_right = st.columns(2)
        new_status = update_left.selectbox(
            "Status",
            options=list(TrackerStatus),
            format_func=lambda status: status.value,
            index=list(TrackerStatus).index(selected.status),
        )
        new_follow_up = update_right.date_input(
            "Follow-up date",
            value=selected.follow_up_date or date.today() + timedelta(days=7),
            key=f"tracker_followup_{record_id}",
        )
        notes = st.text_area("Notes", value=selected.notes, key=f"notes_{record_id}")
        if st.button("Update tracker"):
            with SessionLocal() as session:
                tracker.update(session, record_id, TrackerUpdate(
                    status=new_status, notes=notes, follow_up_date=new_follow_up,
                ))
            st.session_state.action_message = f"Application #{record_id} updated."
            st.rerun()
    else:
        st.info("No applications yet. Analyze one and save it when ready.")

    st.download_button(
        "Download Excel tracker",
        data=ExcelService().export(records),
        file_name="careerpilot_tracker.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

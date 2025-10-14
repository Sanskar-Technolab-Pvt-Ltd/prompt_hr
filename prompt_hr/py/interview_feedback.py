import frappe
from prompt_hr.py.utils import send_notification_email, get_hr_managers_by_company

def on_submit(doc,method):
    
    
    if doc.result == "Pending":
        frappe.throw("Interview Feedback cannot be submitted while the result is marked as 'Pending'. Please update the result to proceed.")

    hr_managers = get_hr_managers_by_company(company=doc.custom_company)
    if send_notification_email(
        recipients=hr_managers,
        doctype=doc.doctype,
        docname=doc.name,
        notification_name= "Interview Feedback Submit Notification"
    ):
        frappe.msgprint(("Notification email sent to HR Managers."), alert=True)
    else:
        frappe.msgprint(("Failed to send notification email to HR Managers."), alert=True)


def on_update(doc, method):
    update_interview_status(doc.interview)
    
    skill_assessments = frappe.get_all("Skill Assessment", filters={"parent": doc.name}, fields=["*"])
    # ? INITIALIZE RATING VARIABLES
    final_rating = 0
    total_rating_scale = 0
    total_rating_given = 0
    # * LOOP THROUGH EACH SKILL ASSESSMENT ENTRY TO ACCUMULATE SCORES
    for assessment in skill_assessments:
        if assessment.custom_rating_scale:
            total_rating_scale += assessment.custom_rating_scale
        if assessment.custom_rating_given:
            total_rating_given += assessment.custom_rating_given
    #! CALCULATE FINAL RATING OUT OF 10 (NORMALIZED)
    final_rating = total_rating_given/total_rating_scale * 10
    doc.db_set("custom_obtained_average_score", final_rating)
    if doc.custom_expected_average_score:
        if doc.has_value_changed("custom_obtained_average_score") and (doc.result == "Pending" or doc.has_value_changed("custom_obtained_average_score")):
            if doc.custom_obtained_average_score >= float(doc.custom_expected_average_score):
                doc.db_set("result", "Cleared")
            else:
                doc.db_set("result", "Rejected")


@frappe.whitelist()
def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return

    roles = frappe.get_roles(user)

    # HR Manager and System Manager have full access
    if "S - HR Director (Global Admin)" in roles or "System Manager" in roles:
        return

    # Interviewers can only see feedback where they are the assigned interviewer
    if "Interviewer" in roles:
        return (
            f"""(`tabInterview Feedback`.interviewer = {frappe.db.escape(user)})"""
        )


def update_interview_status(interview_name):
    # Fetch all feedback for this interview
    feedback_list = frappe.get_all(
        "Interview Feedback",
        filters={"interview": interview_name},
        fields=["result", "docstatus"]
    )

    # Consider only submitted feedback
    submitted_feedback = [f for f in feedback_list if f.docstatus == 1]
    total_feedback = len(feedback_list)
    total_submitted = len(submitted_feedback)

    # If no feedback submitted at all or none has result yet
    if total_submitted == 0:
        frappe.db.set_value("Interview", interview_name, "status", "Pending")
        return

    results = [f.result for f in submitted_feedback]

    cleared_count = results.count("Cleared")
    rejected_count = results.count("Rejected")

    # 1. All Cleared
    if total_submitted == total_feedback and cleared_count == total_feedback:
        frappe.db.set_value("Interview", interview_name, "status", "Cleared")

    # 2. All Rejected
    elif total_submitted == total_feedback and rejected_count == total_feedback:
        frappe.db.set_value("Interview", interview_name, "status", "Rejected")

    # 3. Some feedbacks are submitted but not all finalized
    elif cleared_count > 0 or rejected_count > 0:
        frappe.db.set_value("Interview", interview_name, "status", "Under Review")

    # 4. All pending (none cleared/rejected yet)
    else:
        frappe.db.set_value("Interview", interview_name, "status", "Pending")


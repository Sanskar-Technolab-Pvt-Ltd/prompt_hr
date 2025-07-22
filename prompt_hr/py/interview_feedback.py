import frappe
from prompt_hr.py.utils import send_notification_email, get_hr_managers_by_company

def on_submit(doc,method):
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
    #! CALCULATE FINAL RATING OUT OF 5 (NORMALIZED)
    final_rating = total_rating_given/total_rating_scale * 5
    doc.db_set("custom_obtained_average_score", final_rating)
    if doc.custom_expected_average_score:
        if doc.has_value_changed("custom_obtained_average_score") and (doc.result == "Pending" or doc.has_value_changed("custom_obtained_average_score")):
            if doc.custom_obtained_average_score >= doc.custom_expected_average_score:
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
    if "HR Manager" in roles or "System Manager" in roles:
        return

    # Interviewers can only see feedback where they are the assigned interviewer
    if "Interviewer" in roles:
        return (
            f"""(`tabInterview Feedback`.interviewer = {frappe.db.escape(user)})"""
        )

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
    skill_types = {}
    final_rating = 0
    for assessment in skill_assessments:
        skill_type = assessment.custom_skill_type
        if skill_type not in skill_types:
            skill_types[skill_type] = [assessment.custom_rating_given]
        skill_types[skill_type].append(assessment.custom_rating_given)
    for skill_type, ratings in skill_types.items():
        average_rating = sum(ratings) / len(ratings)
        skill_type_doc = frappe.get_doc("Interview Assessment Skill Type", skill_type)
        final_rating += skill_type_doc.weightage * average_rating
    doc.db_set("custom_obtained_average_score", final_rating / 100)
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

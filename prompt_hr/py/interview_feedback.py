import frappe

def on_submit(doc,method):
    notification = frappe.get_doc("Notification", "Interview Feedback Submit Notification")
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})
    hr_manager_email = None
    hr_manager_users = frappe.get_all(
        "Employee",
        filters={"company": doc.custom_company},
        fields=["user_id"]
    )

    for hr_manager in hr_manager_users:
        hr_manager_user = hr_manager.get("user_id")
        if hr_manager_user:
            # Check if this user has the HR Manager role
            if "HR Manager" in frappe.get_roles(hr_manager_user):
                hr_manager_email = frappe.db.get_value("User", hr_manager_user, "email")
                break

    if not hr_manager_email:
        frappe.throw("HR Manager email not found.")
    
    frappe.sendmail(
        recipients=hr_manager_email,
        subject=subject,
        message=message,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )

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

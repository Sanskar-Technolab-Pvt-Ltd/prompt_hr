import frappe
from prompt_hr.py.utils import get_applicable_print_format,send_notification_email, get_prompt_company_name
# testing comment
@frappe.whitelist()
def trigger_appointment_notification(name):
    doc = frappe.get_doc("Appointment Letter", name)
    employee = frappe.get_doc("Employee", doc.custom_employee)

    # Determine preferred email
    preferred = employee.prefered_contact_email
    email = (
        employee.company_email if preferred == "Company Email"
        else employee.personal_email if preferred == "Personal Email"
        else employee.prefered_email if preferred == "User ID"
        else employee.personal_email 
    )
    print("email:\n\n",email)
    is_prompt = False
    if doc.company == get_prompt_company_name():
        is_prompt = True

    print_format = get_applicable_print_format(is_prompt=is_prompt, doctype=doc.doctype).get("print_format")
    send_notification_email(
        recipients=[email],
        doctype=doc.doctype,
        docname=doc.name,
        notification_name="Send Appointment Letter",
        send_attach=True,
        print_format=print_format
    )
   

    notify_signatory_on_email(doc.company, "S - HR Director (Global Admin)", doc.name, f"Appointment Letter - {doc.company}")

    return "Appointment Letter Successfully"

@frappe.whitelist()
def notify_signatory_on_email(company,role,name,letter,email=None):
    signatory_doc = frappe.get_all("Signature Directory", filters={"company":company},fields=["name"])
    if signatory_doc:
        signatory_details = frappe.get_all("Signature Details", filters={"parent": signatory_doc[0].name,"is_approval_required":1,"role":role}, fields=["name"])
    if signatory_doc and signatory_details:
            role_email = email
            notification = frappe.get_doc("Notification", "Signature Used")
            message = frappe.render_template(notification.message, {"company": company,"role":role,"name":name,"letter":letter})
            subject = frappe.render_template(notification.subject, {"company": company, "role":role})
            if role_email:
                frappe.sendmail(
                    recipients=role_email,
                    subject=subject,
                    message=message
                )
                return

            role_users = frappe.get_all(
                "Employee",
                filters={"company": company},
                fields=["user_id"]
            )
            for role_user in role_users:
                role_user_id = role_user.get("user_id")
                if role_user_id:
                    # Check if this user has the HR Manager role
                    if role in frappe.get_roles(role_user_id):
                        role_email = frappe.db.get_value("User", role_user_id, "email")
                        break
            if role_email:
                frappe.sendmail(
                    recipients=role_email,
                    subject=subject,
                    message=message
                )
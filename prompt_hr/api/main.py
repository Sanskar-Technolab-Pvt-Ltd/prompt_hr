import frappe
from prompt_hr.py.utils import get_applicable_print_format,send_notification_email, get_prompt_company_name
# testing comment
# @frappe.whitelist()
# def trigger_appointment_notification(name):
#     doc = frappe.get_doc("Appointment Letter", name)
#     employee = frappe.get_doc("Employee", doc.custom_employee)

#     # Determine preferred email
#     preferred = employee.prefered_contact_email
#     email = (
#         employee.company_email if preferred == "Company Email"
#         else employee.personal_email if preferred == "Personal Email"
#         else employee.prefered_email if preferred == "User ID"
#         else employee.personal_email 
#     )
#     print("email:\n\n",email)
#     is_prompt = False
#     if doc.company == get_prompt_company_name():
#         is_prompt = True

#     print_format = get_applicable_print_format(is_prompt=is_prompt, doctype=doc.doctype).get("print_format")
#     send_notification_email(
#         recipients=[email],
#         doctype=doc.doctype,
#         docname=doc.name,
#         notification_name="Send Appointment Letter",
#         send_attach=True,
#         print_format=print_format
#     )
#     notify_signatory_on_email(doc.company, doc.name, f"Appointment Letter - Prompt")

#     return "Appointment Letter Successfully"


@frappe.whitelist()
def trigger_appointment_notification(name, to=None, cc=None):
    """Send appointment letter email with TO & CC support"""

    to = frappe.parse_json(to) if to else []
    cc = frappe.parse_json(cc) if cc else []

    doc = frappe.get_doc("Appointment Letter", name)
    employee = frappe.get_doc("Employee", doc.custom_employee)

    #  Determine Preferred Email
    preferred = employee.prefered_contact_email
    email = (
        employee.company_email if preferred == "Company Email"
        else employee.personal_email if preferred == "Personal Email"
        else employee.prefered_email if preferred == "User ID"
        else employee.personal_email
    )

    # Ensure applicant email is always in TO
    if email not in to:
        to.append(email)

    #  Check Letter Print Format
    is_prompt = doc.company == get_prompt_company_name()

    print_format = get_applicable_print_format(
        is_prompt=is_prompt, 
        doctype=doc.doctype
    ).get("print_format")

    #  Send Email
    send_notification_email(
        recipients=to,
        cc=cc,
        doctype=doc.doctype,
        docname=doc.name,
        notification_name="Send Appointment Letter",
        send_attach=True,
        print_format=print_format
    )

    #  Notify Signatory
    notify_signatory_on_email(
        doc.company,
        doc.name,
        f"Appointment Letter - Prompt"
    )

    return "Appointment Letter Sent Successfully"



@frappe.whitelist()
def notify_signatory_on_email(company,name,letter,email=None):
    signatory_doc = frappe.get_all("Signature Directory", filters={"company":company},fields=["name"])
    if signatory_doc:
        signatory_details = frappe.get_all("Signature Details", filters={"parent": signatory_doc[0].name,"is_approval_required":1,"print_format":letter}, fields=["name","employee"])
    if signatory_doc and signatory_details:
            role_email = email
            emp = frappe.get_doc("Employee", signatory_details[0].employee)
            notification = frappe.get_doc("Notification", "Signature Used")
            message = frappe.render_template(notification.message, {"company": company,"emp":emp.employee_name,"name":name,"letter":letter})
            subject = frappe.render_template(notification.subject, {"company": company, "emp":emp.employee_name})
            if role_email:
                frappe.sendmail(
                    recipients=role_email,
                    subject=subject,
                    message=message
                )
            else:
                frappe.sendmail(
                    recipients=emp.user_id,
                    subject=subject,
                    message=message
                )

            # role_users = frappe.get_all(
            #     "Employee",
            #     filters={"company": company},
            #     fields=["user_id"]
            # )
            # for role_user in role_users:
            #     role_user_id = role_user.get("user_id")
            #     if role_user_id:
            #         # Check if this user has the HR Manager role
            #         if role in frappe.get_roles(role_user_id):
            #             role_email = frappe.db.get_value("User", role_user_id, "email")
            #             break
            # if role_email:
            #     frappe.sendmail(
            #         recipients=role_email,
            #         subject=subject,
            #         message=message
            #     )
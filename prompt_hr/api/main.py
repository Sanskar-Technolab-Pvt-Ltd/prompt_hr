import frappe

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

    notification = frappe.get_doc("Notification", "Send Appointment Letter")
    if not notification:
        frappe.throw("No Notification found for Appointment Letter")

    # Company abbreviation logic
    company_abbr = frappe.get_doc("Company", doc.company).abbr
    prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
    indifoss_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")

    # Generate PDF attachment based on company
    attachment = None
    if company_abbr == prompt_abbr:
        pdf_content = frappe.get_print(
            "Appointment Letter", doc.name,
            print_format="Appointment letter - Prompt",
            as_pdf=True
        )
        attachment = {
            "fname": "Appointment letter - Prompt.pdf",
            "fcontent": pdf_content
        }
    elif company_abbr == indifoss_abbr:
        pdf_content = frappe.get_print(
            "Appointment Letter", doc.name,
            print_format="Appointment letter - Indifoss",
            as_pdf=True
        )
        attachment = {
            "fname": "Appointment letter - Indifoss.pdf",
            "fcontent": pdf_content
        }

    # Send email if email found
    if email:
        message = frappe.render_template(notification.message, {"doc": doc, "employee": employee})
        subject = frappe.render_template(notification.subject, {"doc": doc})
        frappe.sendmail(
            recipients=email,
            subject=subject,
            content=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            attachments=[attachment] if attachment else None
        )

        notify_signatory_on_email(doc.company, "HR Manager", doc.name, f"Appointment Letter - {doc.company}")

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
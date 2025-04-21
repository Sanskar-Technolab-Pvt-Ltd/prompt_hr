import frappe

@frappe.whitelist()
def send_interview_schedule_notification(name, applicant_name):
    doc = frappe.get_doc("Interview", name)
    if not doc:
        frappe.throw("Interview document not found.")

    # Internal Interviewers
    interviewers = frappe.get_all(
        "Interview Detail",
        filters={"parent": doc.name},
        fields=["custom_interviewer_employee", "custom_interviewer_name", "custom_is_confirm","name"]
    )

    for interviewer in interviewers:
        if interviewer.custom_interviewer_employee:
            try:
                if interviewer.custom_is_confirm:
                    interviewer.custom_is_confirm = 0
                    frappe.db.set_value("Interview Detail", interviewer.name, "custom_is_confirm", 0)
                    frappe.db.commit()
                    interviewer.reload()
                # Fetch Employee details
                employee = frappe.get_doc("Employee", interviewer.custom_interviewer_employee)
                if employee.user_id:
                    user_email = frappe.db.get_value("User", employee.user_id, "email")

                    # Grant read permission to this user for Interview
                    frappe.share.add(doc.doctype, doc.name, employee.user_id, read=1)

                    if user_email:
                        frappe.sendmail(
                            recipients=[user_email],
                            subject=f"Interview Availability Request - {doc.name}",
                            message=f"""
                                Dear {employee.employee_name or 'Interviewer'},<br><br>
                                You have been scheduled for an interview session:<br>
                                <b>Interview:</b> {doc.name}<br>
                                <b>Date:</b> {frappe.utils.format_date(doc.scheduled_on)}<br>
                                <b>Time:</b> {doc.from_time} to {doc.to_time}<br><br>
                                Please confirm your availability for this session.<br><br>
                                <a href="{frappe.utils.get_url()}/app/interview/{doc.name}">Click here to view the interview details and Confirm Your Availability</a><br><br>
                                Regards,<br>
                                HR Team
                            """,
                            reference_doctype=doc.doctype,
                            reference_name=doc.name,
                            now=True
                        )
            except Exception as e:
                frappe.log_error(f"Failed to send internal email: {e}", "Interview Notification Error")

    # External Interviewers
    external_interviewers = frappe.get_all(
        "External Interviewer",
        filters={"parent": doc.name},
        fields=["user", "user_name", "is_confirm","name"]
    )

    for interviewer in external_interviewers:
        if interviewer.user:
            try:
                supplier = frappe.get_doc("Supplier", interviewer.user)
                if supplier.custom_user:
                    if interviewer.is_confirm:
                        interviewer.is_confirm = 0
                        frappe.db.set_value("External Interviewer", interviewer.name, "is_confirm", 0)
                        frappe.db.commit()
                        interviewer.reload()
                    user_email = frappe.db.get_value("User", supplier.custom_user, "email")

                    # Grant read permission to external user too
                    frappe.share.add(doc.doctype, doc.name, supplier.custom_user, read=1)

                    if user_email:
                        frappe.sendmail(
                            recipients=[user_email],
                            subject=f"Interview Availability Request - {doc.name}",
                            message=f"""
                                Dear {interviewer.user_name or 'Interviewer'},<br><br>
                                You have been scheduled for an interview session:<br>
                                <b>Interview:</b> {doc.name}<br>
                                <b>Date:</b> {frappe.utils.format_date(doc.scheduled_on)}<br>
                                <b>Time:</b> {doc.from_time} to {doc.to_time}<br><br>
                                Please confirm your availability for this session.<br><br>
                                <a href="{frappe.utils.get_url()}/app/interview/{doc.name}">Click here to view the interview details and Confirm Your Availability</a><br><br>
                                Regards,<br>
                                HR Team
                            """,
                            reference_doctype=doc.doctype,
                            reference_name=doc.name,
                            now=True
                        )
            except Exception as e:
                frappe.log_error(f"Failed to send external email: {e}", "Interview Notification Error")

    return "Notification sent to interviewers successfully."

@frappe.whitelist()
def send_notification_to_hr_manager(name, company, user):
    try:
        # Fetch Interview document
        doc = frappe.get_doc("Interview", name)
        
        if not doc:
            frappe.throw("Interview document not found.")

        # Fetch HR Manager email from Employees in the given company
        hr_manager_email = None
        hr_manager_users = frappe.get_all(
            "Employee",
            filters={"company": company},
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

        # Fetch User details of the person confirming the interview
        user_doc = frappe.get_doc("User", user)

        # Prepare email content
        subject = f"{user_doc.full_name} confirmed availability for Interview - {doc.name}"
        message = f"""
            Dear HR Manager,<br><br>
            Interviewer <b>{user_doc.full_name}</b> has confirmed their availability for the interview with the applicant:<br><br>
            <b>Applicant Name:</b> {doc.custom_applicant_name}<br>
            <b>Interview Round:</b> {doc.interview_round}<br>
            <b>Position:</b> {doc.designation}<br><br>
            <a href="{frappe.utils.get_url()}/app/interview/{doc.name}">Please review the applicant's details.</a><br><br>
            Regards,<br>
            HR Team
        """
        
        # Update Interview Detail if the interviewer is internal
        interviewer = frappe.get_all(
            "Interview Detail",
            filters={"parent": doc.name, "custom_interviewer_name": user_doc.full_name},
            fields=["name"]
        )
        if interviewer:
            frappe.db.set_value("Interview Detail", interviewer[0].name, "custom_is_confirm", 1)
        
        # Update External Interviewer confirmation if the interviewer is external
        external_interviewers = frappe.get_all(
            "External Interviewer",
            filters={"parent": doc.name},
            fields=["user", "user_name", "is_confirm","name"]
        )
        print("External Interviewers:", external_interviewers)
        print("User Doc:", user_doc)
        print("User:", user)
        print("Interviewer:", interviewer)
        external_interviewer = None
        for interviewer in external_interviewers:
            print("Checking External Interviewer:", user_doc,frappe.get_doc("Supplier", interviewer.user).custom_user)
            if frappe.get_doc("Supplier", interviewer.user).custom_user == user_doc.name:
                external_interviewer = interviewer  
                break
        if external_interviewer:
            frappe.db.set_value("External Interviewer", external_interviewer.name, "is_confirm", 1)
            message = f"""
            Dear HR Manager,<br><br>
            Interviewer <b>{external_interviewer.user_name}</b> has confirmed their availability for the interview with the applicant:<br><br>
            <b>Applicant Name:</b> {doc.custom_applicant_name}<br>
            <b>Interview Round:</b> {doc.interview_round}<br>
            <b>Position:</b> {doc.designation}<br><br>
            <a href="{frappe.utils.get_url()}/app/interview/{doc.name}">Please review the applicant's details.</a><br><br>
            Regards,<br>
            HR Team
        """

        # Send the email to HR Manager
        frappe.sendmail(
            recipients=[hr_manager_email],
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            now=True
        )

    except Exception as e:
        # Log the error with traceback for debugging
        frappe.log_error(title="HR Notification Error", message=frappe.get_traceback())
        frappe.throw("Something went wrong while sending notification to the HR Manager.")

@frappe.whitelist()
def get_supplier_custom_user(supplier_name):
    custom_user = frappe.db.get_value("Supplier", supplier_name, "custom_user")
    return custom_user
    """Check if the current user is an unconfirmed interviewer for this interview"""
    result = {
        "is_internal_interviewer_not_confirmed": False,
        "is_external_interviewer_not_confirmed": False
    }
    
    # Check internal interviewers
    internal_interviewers = frappe.get_all(
        "Interview Detail",
        filters={"parent": interview_name, "custom_is_confirm": 0},
        fields=["custom_interviewer_employee"]
    )
    
    for interviewer in internal_interviewers:
        if interviewer.custom_interviewer_employee:
            employee_user = frappe.db.get_value("Employee", interviewer.custom_interviewer_employee, "user_id")
            if employee_user == user:
                result["is_internal_interviewer_not_confirmed"] = True
                break
    
    # Check external interviewers
    external_interviewers = frappe.get_all(
        "External Interviewer",
        filters={"parent": interview_name, "is_confirm": 0},
        fields=["user"]
    )
    
    for interviewer in external_interviewers:
        if interviewer.user:
            supplier_user = frappe.db.get_value("Supplier", interviewer.user, "custom_user")
            if supplier_user == user:
                result["is_external_interviewer_not_confirmed"] = True
                break
    
    return result
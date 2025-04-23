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
    notification = frappe.get_doc("Notification", "Notify Interviewer")
    for interviewer in interviewers:
        if interviewer.custom_interviewer_employee:
            try:
                if interviewer.custom_is_confirm:
                    interviewer.custom_is_confirm = 0
                    frappe.db.set_value("Interview Detail", interviewer.name, "custom_is_confirm", 0)
                    frappe.db.commit()
                # Fetch Employee details
                employee = frappe.get_doc("Employee", interviewer.custom_interviewer_employee)
                if employee.user_id:
                    user_email = frappe.db.get_value("User", employee.user_id, "email")

                    # Grant read permission to this user for Interview
                    frappe.share.add(doc.doctype, doc.name, employee.user_id, read=1)
                    
                    if user_email:
                        frappe.sendmail(
                            recipients=[user_email],
                            message = frappe.render_template(notification.message, {"doc": doc,"interviewer": interviewer.custom_interviewer_name}),
                            subject = frappe.render_template(notification.subject, {"doc": doc}),
                            reference_doctype=doc.doctype,
                            reference_name=doc.name,
                            now=True
                        )
                interviewer.reload()

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
                            message = frappe.render_template(notification.message, {"doc": doc,"interviewer": interviewer.custom_interviewer_name}),
                            subject = frappe.render_template(notification.subject, {"doc": doc}),
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

def after_insert(doc, method):
    # Get all interview details from the document
    interviewers = frappe.get_all(
        "Interview Detail",
        filters={"parent": doc.name},
        fields=["custom_interviewer_employee", "custom_interviewer_name", "custom_is_confirm", "name"]
    )
    
    # Get all external interviewers
    external_interviewers = frappe.get_all(
        "External Interviewer",
        filters={"parent": doc.name},
        fields=["user", "user_name", "is_confirm", "name"]
    )
    
    # Process internal interviewers
    for interviewer in interviewers:
        if interviewer.get("custom_interviewer_employee"):
            # Check if feedback already exists
            employee = frappe.get_doc("Employee", interviewer.custom_interviewer_employee)
            user = None
            if employee.user_id:
                user = frappe.get_doc("User", employee.user_id)
            exists = frappe.db.exists("Interview Feedback", {
                "interview": doc.name,
                "job_applicant": doc.job_applicant,
                "interview_round": doc.interview_round,
                "custom_company": doc.custom_company,
                "interviewer": user.name
            })
            
            if not exists:
                try:
                    # Create new feedback document
                    feedback = frappe.get_doc({
                        "doctype": "Interview Feedback",
                        "interview": doc.name,
                        "interview_round": doc.interview_round,
                        "interviewer": user.name,
                        "job_applicant": doc.job_applicant,
                        "custom_company": doc.custom_company,
                        "result": "Pending"
                    })
                    round_doc = frappe.get_doc("Interview Round", doc.interview_round)
                    for criterion in round_doc.expected_skill_set:
                        feedback.append("skill_assessment", {
                            "skill": criterion.skill,
                            "custom_skill_type": criterion.custom_skill_type,
                            "custom_rating_scale":criterion.custom_rating_scale
                        })
                    feedback.flags.ignore_validate = True
                    feedback.insert(ignore_permissions=True)
                    frappe.db.commit()
                    print(f"Created feedback for internal interviewer: {interviewer.custom_interviewer_employee}")
                except Exception as e:
                    frappe.log_error("Failed to create Interview Feedback", f"{user.name}: {str(e)}")
    
    # Process external interviewers
    for interviewer in external_interviewers:
        if interviewer.get("user"):
            # Check if feedback already exists
            supplier = frappe.get_doc("Supplier", interviewer.user)
            if supplier.custom_user:
                user = frappe.get_doc("User", supplier.custom_user)
            exists = frappe.db.exists("Interview Feedback", {
                "interview": doc.name,
                "interview_round": doc.interview_round,
                "job_applicant": doc.job_applicant,
                "custom_company": doc.custom_company,
                "interviewer": user.name
            })
            
            if not exists:
                try:
                    # Create new feedback document
                    feedback = frappe.get_doc({
                        "doctype": "Interview Feedback",
                        "interview": doc.name,
                        "interview_round": doc.interview_round,
                        "interviewer": user.name,
                        "job_applicant": doc.job_applicant,
                        "custom_company": doc.custom_company,
                        "result": "Pending"
                    })
                    round_doc = frappe.get_doc("Interview Round", doc.interview_round)
                    for criterion in round_doc.expected_skill_set:
                        feedback.append("skill_assessment", {
                            "skill": criterion.skill,
                            "custom_skill_type": criterion.custom_skill_type,
                            "custom_rating_scale":criterion.custom_rating_scale
                        })
                    feedback.flags.ignore_validate = True
                    feedback.insert(ignore_permissions=True)
                    frappe.db.commit()
                    print(f"Created feedback for external interviewer: {interviewer.user}")
                except Exception as e:
                    frappe.log_error("Failed to create Interview Feedback", f"{user.name}: {str(e)}")


@frappe.whitelist()
def submit_feedback(doc_name, interview_round, job_applicant, custom_company):
    # Get the current logged-in user
    current_user = frappe.session.user
    feedback_exists = frappe.db.exists("Interview Feedback", {
        "interview": doc_name,
        "job_applicant": job_applicant,
        "interview_round": interview_round,
        "custom_company": custom_company,
        "interviewer": current_user
    })
    if feedback_exists:
        # If feedback exists, open the existing feedback record
        feedback_doc = frappe.get_doc("Interview Feedback", feedback_exists)
        return f"{frappe.utils.get_url()}/app/interview-feedback/{feedback_doc.name}"
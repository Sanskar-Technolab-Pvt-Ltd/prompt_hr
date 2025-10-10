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
                # if not interviewer.custom_is_confirm:
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
                            # now=True
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
                    if not interviewer.is_confirm:
                        user_email = frappe.db.get_value("User", supplier.custom_user, "email")

                        if user_email:
                            frappe.sendmail(
                                recipients=[user_email],
                                message = frappe.render_template(notification.message, {"doc": doc,"interviewer": interviewer.custom_interviewer_name}),
                                subject = frappe.render_template(notification.subject, {"doc": doc}),
                                reference_doctype=doc.doctype,
                                reference_name=doc.name,
                                # now=True
                            )
                        interviewer.reload()
            except Exception as e:
                frappe.log_error(f"Failed to send external email: {e}", "Interview Notification Error")

    return "Notification sent to interviewers successfully."

@frappe.whitelist()
def send_notification_to_hr_manager(name, company, user):
    try:
        # Fetch Interview document
        doc = frappe.get_doc("Interview", name)
        notification = frappe.get_doc("Notification", "Notify HR Manager")
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
                if "S - HR Director (Global Admin)" in frappe.get_roles(hr_manager_user):
                    hr_manager_email = frappe.db.get_value("User", hr_manager_user, "email")
                    break

        if not hr_manager_email:
            frappe.throw("HR Manager email not found.")

        # Fetch User details of the person confirming the interview
        user_doc = frappe.get_doc("User", user)

        # Prepare email content
        subject = frappe.render_template(notification.subject, {"doc": doc, "user_doc": user_doc})
        message = frappe.render_template(notification.message, {"doc": doc, "interviewer": user_doc.full_name})

        # Update Interview Detail if the interviewer is internal
        employee_user = frappe.get_all("Employee", filters={"user_id":user_doc.name, "status":"Active"}, fields=["name"])
        interviewer = frappe.get_all(
            "Interview Detail",
            filters={"parent": doc.name, "custom_interviewer_employee": employee_user[0].name},
            fields=["name"]
        )
        if interviewer:
            interviewer_doc = frappe.get_doc("Interview Detail", interviewer[0].name)
            interviewer_doc.db_set("custom_is_confirm", 1)
        
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
            message = frappe.render_template(notification.message, {"doc": doc,"interviewer": external_interviewer.user_name})

        # Send the email to HR Manager
        frappe.sendmail(
            recipients=[hr_manager_email],
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            # now=True
        )

    except Exception as e:
        # Log the error with traceback for debugging
        frappe.log_error(title="HR Notification Error", message=frappe.get_traceback())
        frappe.throw("Something went wrong while sending notification to the HR Manager.")

@frappe.whitelist()
def get_supplier_custom_user(supplier_name):
    custom_user = frappe.db.get_value("Supplier", supplier_name, "custom_user")
    return custom_user

def on_update(doc, method):
    # Fetch previous doc to compare
    prev_doc = doc.get_doc_before_save()
    
    # Get current internal interviewers (Employee IDs)
    current_internal = {
        d.custom_interviewer_employee for d in doc.get("interview_details", [])
        if d.custom_interviewer_employee
    }

    # Get current external interviewers (Supplier user links)
    current_external = {
        d.user for d in doc.get("custom_external_interviewers", [])
        if d.user
    }

    # Handle previous interviewers if update (not insert)
    prev_internal = set()
    prev_external = set()
    if prev_doc:
        prev_internal = {
            d.custom_interviewer_employee for d in prev_doc.get("interview_details", [])
            if d.custom_interviewer_employee
        }
        prev_external = {
            d.user for d in prev_doc.get("custom_external_interviewers", [])
            if d.user
        }

    removed_internal = prev_internal - current_internal
    removed_external = prev_external - current_external

    # Delete removed internal feedback
    for emp_id in removed_internal:
        emp_doc = frappe.get_doc("Employee", emp_id)
        if emp_doc.user_id:
            feedback_name = frappe.db.get_value("Interview Feedback", {
                "interview": doc.name,
                "interviewer": emp_doc.user_id
            })
            if feedback_name:
                frappe.delete_doc("Interview Feedback", feedback_name, force=True)
                frappe.logger().info(f"Deleted internal feedback for {emp_doc.user_id}")

    # Delete removed external feedback
    for supplier_id in removed_external:
        supplier_doc = frappe.get_doc("Supplier", supplier_id)
        if supplier_doc.custom_user:
            feedback_name = frappe.db.get_value("Interview Feedback", {
                "interview": doc.name,
                "interviewer": supplier_doc.custom_user
            })
            if feedback_name:
                frappe.delete_doc("Interview Feedback", feedback_name, force=True)
                frappe.logger().info(f"Deleted external feedback for {supplier_doc.custom_user}")

    # Process internal interviewers
    for emp_id in current_internal:
        emp = frappe.get_doc("Employee", emp_id)
        if emp.user_id:
            exists = frappe.db.exists("Interview Feedback", {
                "interview": doc.name,
                "job_applicant": doc.job_applicant,
                "interview_round": doc.interview_round,
                "custom_company": doc.custom_company,
                "interviewer": emp.user_id
            })
            if not exists:
                try:
                    feedback = frappe.new_doc("Interview Feedback")
                    feedback.update({
                        "interview": doc.name,
                        "interview_round": doc.interview_round,
                        "interviewer": emp.user_id,
                        "job_applicant": doc.job_applicant,
                        "custom_company": doc.custom_company,
                        "result": "Pending"
                    })
                    
                    round_doc = frappe.get_doc("Interview Round", doc.interview_round)
                    for criterion in round_doc.expected_skill_set:
                        feedback.append("skill_assessment", {
                            "skill": criterion.skill,
                            "custom_skill_type": criterion.custom_skill_type,
                            "custom_rating_scale": criterion.custom_rating_scale
                        })
                    
                    feedback.flags.ignore_validate = True
                    feedback.insert(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.logger().info(f"Created feedback for internal interviewer: {emp.user_id}")
                except Exception as e:
                    frappe.log_error(f"{emp.user_id}: {str(e)}", "Failed to create Interview Feedback")

    # Process external interviewers
    for sup_id in current_external:
        supplier = frappe.get_doc("Supplier", sup_id)
        if supplier.custom_user:
            user_id = supplier.custom_user
            exists = frappe.db.exists("Interview Feedback", {
                "interview": doc.name,
                "job_applicant": doc.job_applicant,
                "interview_round": doc.interview_round,
                "custom_company": doc.custom_company,
                "interviewer": user_id
            })
            if not exists:
                try:
                    feedback = frappe.new_doc("Interview Feedback")
                    feedback.update({
                        "interview": doc.name,
                        "interview_round": doc.interview_round,
                        "interviewer": user_id,
                        "job_applicant": doc.job_applicant,
                        "custom_company": doc.custom_company,
                        "result": "Pending"
                    })
                    
                    round_doc = frappe.get_doc("Interview Round", doc.interview_round)
                    for criterion in round_doc.expected_skill_set:
                        feedback.append("skill_assessment", {
                            "skill": criterion.skill,
                            "custom_skill_type": criterion.custom_skill_type,
                            "custom_rating_scale": criterion.custom_rating_scale
                        })
                    
                    feedback.flags.ignore_validate = True
                    feedback.insert(ignore_permissions=True)
                    frappe.db.commit()
                    frappe.logger().info(f"Created feedback for external interviewer: {user_id}")
                except Exception as e:
                    frappe.log_error(f"{user_id}: {str(e)}", "Failed to create Interview Feedback")

    # Get current internal interviewer users
    current_internal_users = {}
    for emp_id in current_internal:
        employee = frappe.get_doc("Employee", emp_id)
        if employee.user_id:
            current_internal_users[employee.user_id] = True

    # Get current external interviewer users
    current_external_users = {}
    for sup_id in current_external:
        supplier = frappe.get_doc("Supplier", sup_id)
        if supplier.custom_user:
            current_external_users[supplier.custom_user] = True
    
    # Combine all current users who should have access
    current_users = {**current_internal_users, **current_external_users}
    
    # Get previous users if this is an update
    prev_internal_users = {}
    prev_external_users = {}
    
    if prev_doc:
        for emp_id in prev_internal:
            employee = frappe.get_doc("Employee", emp_id)
            if employee.user_id:
                prev_internal_users[employee.user_id] = True
        
        for sup_id in prev_external:
            supplier = frappe.get_doc("Supplier", sup_id)
            if supplier.custom_user:
                prev_external_users[supplier.custom_user] = True
    
    # Combine all previous users who had access
    prev_users = {**prev_internal_users, **prev_external_users}
    
    # Add permissions for new users
    for user_id in current_users:
        frappe.share.add(doc.doctype, doc.name, user_id, read=1)
        
    # Remove permissions for users no longer involved
    removed_users = set(prev_users.keys()) - set(current_users.keys())
    for user_id in removed_users:
        frappe.share.remove(doc.doctype, doc.name, user_id)


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
    
@frappe.whitelist()
def check_interviewer_permission(user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return

    roles = frappe.get_roles(user)

    if "System Manager" in roles or "S - HR Director (Global Admin)" in roles:
        return

    if "Interviewer" in roles:
        # Correct SQL condition with proper quoting
        return (
            f"""EXISTS (
                SELECT name FROM `tabDocShare`
                WHERE `tabDocShare`.share_doctype = 'Interview'
                AND `tabDocShare`.share_name = `tabInterview`.name
                AND `tabDocShare`.user = {frappe.db.escape(user)}
            )"""
        )

@frappe.whitelist()
def get_employee_user_id(employee_id):
    # Only allow if the session user is linked
    emp = frappe.get_doc("Employee", employee_id)
    if emp.user_id == frappe.session.user:
        return emp.user_id
    # or apply other business logic
    return None

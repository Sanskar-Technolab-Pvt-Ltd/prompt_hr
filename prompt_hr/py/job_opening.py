import frappe
import traceback
from dateutil.relativedelta import relativedelta
from frappe.utils import getdate, nowdate, formatdate
from prompt_hr.py.utils import send_notification_email
import json

# ? before_insert HOOK
def before_insert(doc, method):
    current_workflow_state = frappe.db.get_value("Job Requisition", doc.custom_job_requisition_record, "workflow_state")
    final_workflow_state = "Final Approval"
    if current_workflow_state != final_workflow_state: 
        frappe.throw(f"You are not authorized to create a Job Opening from this Job Requisition. Final Stage of Approval is not reached.")
    

# ! prompt_hr.py.job_opening.send_job_opening_notification
@frappe.whitelist()
def send_job_opening_notification(
    company=None,
    due_date=None,
    notification_name=None,
    min_tenure_in_company=0,
    min_tenure_in_current_role=0,
    allowed_department=None,
    allowed_location=None,
    allowed_grade=None,
    job_opening=None,
    source=None,
):
    """
    Send internal job opening notifications to eligible employees.
    """
    
    try:

        if isinstance(allowed_department, str):
            allowed_department = json.loads(allowed_department)
        if isinstance(allowed_location, str):
            allowed_location = json.loads(allowed_location)
        if isinstance(allowed_grade, str):
            allowed_grade = json.loads(allowed_grade)

        # ? BUILD EMPLOYEE FILTERS
        filters = {"status": "Active"}
        if allowed_department:
            filters["department"] = ["in", allowed_department]
        if allowed_location:
            filters["custom_work_location"] = ["in", allowed_location]
        if allowed_grade:
            filters["grade"] = ["in", allowed_grade]
        if company:
            filters["company"] = company
                

        # ? FETCH EMPLOYEES
        employees = frappe.get_all(
            "Employee",
            filters=filters,
            fields=["name", "date_of_joining", "prefered_email", "user_id"],
        ) 

        print(f"Eligible Employees\n\n\n: {employees}")

        # ? BUILD ROLE HISTORY MAP FOR TENURE CALCULATION
        role_history_map = get_role_history_map()
        eligible_emails = []

        # ? FILTER BY TENURE IN COMPANY AND ROLE
        for emp in employees:
            if not emp.date_of_joining:
                continue
            company_months = get_months_between(emp.date_of_joining, nowdate())
            if company_months < float(min_tenure_in_company):
                continue
            role_months = get_role_tenure_from_map(
                role_history_map, emp.name, emp.date_of_joining
            )
            if role_months < float(min_tenure_in_current_role):
                continue
            if emp.user_id:
                eligible_emails.append(emp.get("prefered_email"))

        # ? SEND NOTIFICATION IF ANYONE IS ELIGIBLE
        if eligible_emails:
            base_url = frappe.utils.get_url()
            apply_link = f"{base_url}/app/job-applicant/new-job-applicant-1?job_title={job_opening}&source={source}"
            send_notification_email(
                recipients=eligible_emails,
                notification_name=notification_name,
                doctype="Job Opening",
                docname=job_opening,
                button_link=apply_link
            )

        return eligible_emails

    except Exception as e:
        frappe.log_error(
            title="Job Notification Error",
            message=f"Error in job notification: {str(e)}\n{traceback.format_exc()}",
        )
        return []


@frappe.whitelist()
def send_job_opening_recruiter_notification(name):
    doc = frappe.get_doc("Job Opening", name)
    notification = frappe.get_doc("Notification", "Notify Job Opening Recruiters")

    # NOTIFY INTERNAL RECRUITERS
    if doc.custom_internal_recruiter:
        internal_recruiters = frappe.get_all(
            "Internal Recruiter",
            filters={"parent": doc.name},
            fields=["name", "user", "is_confirm"]
        )

        for recruiter in internal_recruiters:
            if recruiter.user and not recruiter.is_confirm:
                try:
                    recruiter_employee = frappe.get_doc("Employee", recruiter.user)
                    if recruiter_employee.user_id:
                        user_email = frappe.db.get_value("User", recruiter_employee.user_id, "email")
                        frappe.share.add(doc.doctype, doc.name, recruiter_employee.user_id, read=1)
                        if user_email:
                            subject = frappe.render_template(notification.subject, {"doc": doc, "recruiter": recruiter_employee.employee_name})
                            message = frappe.render_template(notification.message, {"doc": doc, "recruiter": recruiter_employee.employee_name})
                            frappe.sendmail(
                                recipients=[user_email],
                                subject=subject,
                                message=message,
                                reference_doctype=doc.doctype,
                                reference_name=doc.name
                            )
                            frappe.db.set_value("Internal Recruiter", recruiter.name, "assign_date", frappe.utils.nowdate())
                    else:
                        frappe.msgprint(f"User ID not found for employee {recruiter_employee.name}")
                except Exception as e:
                    frappe.log_error(f"Failed to notify internal recruiter: {e}", "Internal Recruiter Notification Error")

    # NOTIFY EXTERNAL RECRUITERS
    if doc.custom_external_recruiter:
        external_recruiters = frappe.get_all(
            "External Recruiter",
            filters={"parent": doc.name},
            fields=["name", "user", "is_confirm"]
        )

        for recruiter in external_recruiters:
            if recruiter.user and not recruiter.is_confirm:
                try:
                    supplier_doc = frappe.get_doc("Supplier", recruiter.user)
                    if supplier_doc.custom_user:
                        user_email = frappe.db.get_value("User", supplier_doc.custom_user, "email")
                        frappe.share.add(doc.doctype, doc.name, supplier_doc.custom_user, read=1)
                        if user_email:
                            subject = frappe.render_template(notification.subject, {"doc": doc, "recruiter": supplier_doc.supplier_name})
                            message = frappe.render_template(notification.message, {"doc": doc, "recruiter": supplier_doc.supplier_name})
                            frappe.sendmail(
                                recipients=[user_email],
                                subject=subject,
                                message=message,
                                reference_doctype=doc.doctype,
                                reference_name=doc.name
                            )
                            frappe.db.set_value("External Recruiter", recruiter.name, "assign_date", frappe.utils.nowdate())
                    else:
                        frappe.msgprint(f"Custom User not set for supplier {supplier_doc.name}")
                except Exception as e:
                    frappe.log_error(f"Failed to notify external recruiter: {e}", "External Recruiter Notification Error")

    return "Recruiters notified successfully."

@frappe.whitelist()
def send_job_opening_interview_notification(name):
    doc = frappe.get_doc("Job Opening", name)
    notification = frappe.get_doc("Notification", "Notify Job Opening Interviewers")

    # NOTIFY INTERNAL INTERVIEWERS
    if doc.custom_internal_interviewers:
        internal_interviewers = frappe.get_all(
            "Internal Interviewer",
            filters={"parent": doc.name},
            fields=["name", "user"]
        )

        for interviewer in internal_interviewers:
            if interviewer.user:
                try:
                    employee = frappe.get_doc("Employee", interviewer.user)
                    if employee.user_id:
                        user_email = frappe.db.get_value("User", employee.user_id, "email")
                        frappe.share.add(doc.doctype, doc.name, employee.user_id, read=1)

                        if user_email:
                            subject = frappe.render_template(notification.subject, {
                                "doc": doc,
                                "interviewer": employee.employee_name
                            })
                            message = frappe.render_template(notification.message, {
                                "doc": doc,
                                "interviewer": employee.employee_name
                            })
                            frappe.sendmail(
                                recipients=[user_email],
                                subject=subject,
                                message=message,
                                reference_doctype=doc.doctype,
                                reference_name=doc.name
                            )
                except Exception as e:
                    frappe.log_error(f"Failed to notify internal interviewer: {e}", "Internal Interviewer Notification Error")

    # NOTIFY EXTERNAL INTERVIEWERS
    if doc.custom_external_interviewers:
        external_interviewers = frappe.get_all(
            "External Interviewer",
            filters={"parent": doc.name},
            fields=["name", "user", "is_confirm"]
        )

        for interviewer in external_interviewers:
            if interviewer.user:
                try:
                    supplier = frappe.get_doc("Supplier", interviewer.user)
                    if supplier.custom_user:
                        user_email = frappe.db.get_value("User", supplier.custom_user, "email")
                        frappe.share.add(doc.doctype, doc.name, supplier.custom_user, read=1)
                        if user_email:
                            subject = frappe.render_template(notification.subject, {
                                "doc": doc,
                                "interviewer": supplier.supplier_name
                            })
                            message = frappe.render_template(notification.message, {
                                "doc": doc,
                                "interviewer": supplier.supplier_name
                            })
                            frappe.sendmail(
                                recipients=[user_email],
                                subject=subject,
                                message=message,
                                reference_doctype=doc.doctype,
                                reference_name=doc.name
                            )
                except Exception as e:
                    frappe.log_error(f"Failed to notify external interviewer: {e}", "External Interviewer Notification Error")

    return "Interviewers notified successfully."


def get_months_between(from_date, to_date):
    if not from_date or not to_date:
        return 0
    from_dt = getdate(from_date)
    to_dt = getdate(to_date)
    diff = relativedelta(to_dt, from_dt)
    return diff.years * 12 + diff.months


def get_role_history_map():
    records = frappe.get_all(
        "Employee Internal Work History",
        fields=["parent", "from_date", "to_date"],
        order_by="to_date desc",
    )
    history_map = {}
    for row in records:
        history_map.setdefault(row.parent, []).append(row)
    return history_map


def get_role_tenure_from_map(history_map, emp_id, joining_date):
    try:
        if emp_id in history_map and history_map[emp_id]:
            latest = history_map[emp_id][0]
            from_date = latest.from_date
            to_date = latest.to_date or nowdate()
            return get_months_between(from_date, to_date)
        return get_months_between(joining_date, nowdate())
    except Exception as e:
        frappe.log_error(
            title="Role Tenure Error",
            message=f"Error getting role tenure for {emp_id}: {str(e)}\n{traceback.format_exc()}",
        )
        return 0

@frappe.whitelist()
def send_notification_to_hr_manager(name, company, user):
    try:
        # Fetch Job Opening document
        doc = frappe.get_doc("Job Opening", name)
        notification = frappe.get_doc("Notification", "Notify HR Manager About Recruiter Confirmation")
        if not doc:
            frappe.throw("Job Opening document not found.")

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
        subject = frappe.render_template(notification.subject, {"doc": doc, "user_doc": user_doc})
        message = frappe.render_template(notification.message, {"doc": doc, "recruiter_name": user_doc.full_name})

        internal_recruiter = frappe.get_all(
            "Internal Recruiter",
            filters={"parent": doc.name, "user_name": user_doc.full_name},
            fields=["name"]
        )
        if internal_recruiter:
            frappe.db.set_value("Internal Recruiter", internal_recruiter[0].name, "is_confirm", 1)
        
        # Update External Interviewer confirmation if the interviewer is external
        external_recruiters = frappe.get_all(
            "External Recruiter",
            filters={"parent": doc.name},
            fields=["user", "user_name", "is_confirm","name"]
        )
        external_recruiter = None
        for recruiter in external_recruiters:
            if frappe.get_doc("Supplier", recruiter.user).custom_user == user_doc.name:
                external_recruiter = recruiter  
                break
        if external_recruiter:
            frappe.db.set_value("External Recruiter", external_recruiter.name, "is_confirm", 1)
            message = frappe.render_template(notification.message, {"doc": doc,"recruiter_name": external_recruiter.user_name})

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
def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return

    roles = frappe.get_roles(user)

    # HR Manager and System Manager have full access
    if "HR Manager" in roles or "System Manager" in roles:
        return

    if "Interviewer" in roles:
        return (
            f"""EXISTS (
                SELECT name FROM `tabDocShare`
                WHERE `tabDocShare`.share_doctype = 'Job Opening'
                AND `tabDocShare`.share_name = `tabJob Opening`.name
                AND `tabDocShare`.user = {frappe.db.escape(user)}
            )"""
        )

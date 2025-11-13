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
            fields=["name", "date_of_joining", "user_id"],
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
                eligible_emails.append(emp.get("user_id"))

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
            fields=["name", "custom_user"]
        )

        for recruiter in internal_recruiters:
            if recruiter.custom_user:
                try:
                    recruiter_employee = frappe.get_doc("Employee", recruiter.custom_user)
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
            fields=["name", "custom_user"]
        )

        for recruiter in external_recruiters:
            if recruiter.custom_user:
                try:
                    supplier_doc = frappe.get_doc("Supplier", recruiter.custom_user)
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
            fields=["name", "custom_user"]
        )

        for interviewer in internal_interviewers:
            if interviewer.custom_user:
                try:
                    employee = frappe.get_doc("Employee", interviewer.custom_user)
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
            fields=["name", "custom_user"]
        )

        for interviewer in external_interviewers:
            if interviewer.custom_user:
                try:
                    supplier = frappe.get_doc("Supplier", interviewer.custom_user)
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
def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return

    roles = frappe.get_roles(user)

    # HR Manager and System Manager have full access
    if "S - HR Director (Global Admin)" in roles or "System Manager" in roles:
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

# ? CALLED FROM FORM VIEW TO FETCH DASHBOARD SUMMARY
@frappe.whitelist()
def get_job_applicant_summary(job_opening):
	"""
	FETCHES JOB APPLICANT STATUS SUMMARY FOR A GIVEN JOB OPENING.
	RETURNS A DICT WITH COUNT OF APPLICANTS IN EACH STAGE.
	"""
	try:
		# * FETCH THE JOB OPENING DOCUMENT
		job_opening_doc = frappe.get_doc("Job Opening", job_opening)
		if not job_opening_doc:
			frappe.throw(f"Job Opening {job_opening} not found.")

		# * FETCH ALL JOB APPLICANTS LINKED TO THE JOB OPENING
		job_applicants = frappe.get_all(
			"Job Applicant",
			filters={"job_title": job_opening},
			fields=["name", "applicant_name", "status"]
		)

		# * INITIALIZE STATUS-WISE COUNTERS
		job_applicant_summary = frappe._dict({
			"Open": 0,
			"Hold": 0,
			"Shortlisted": 0,
			"In Interview Stage": 0,
			"Offer Given": 0,
			"Offer Accepted": 0
		})

		# * LOOP THROUGH EACH APPLICANT AND UPDATE COUNT BASED ON STATUS
		for applicant in job_applicants:
			status = applicant.status

			if status == "Open":
				job_applicant_summary["Open"] += 1
			elif status == "Hold":
				job_applicant_summary["Hold"] += 1
			elif status in ["Shortlisted by Interviewer", "Shortlisted by HR"]:
				job_applicant_summary["Shortlisted"] += 1
			elif status in ["Interview in Progress", "Final Interview Selected"]:
				job_applicant_summary["In Interview Stage"] += 1
			elif status == "Job Offer Given":
				job_applicant_summary["Offer Given"] += 1
			elif status == "Job Offer Accepted":
				job_applicant_summary["Offer Accepted"] += 1

		# * RETURN THE FINAL SUMMARY TO CLIENT
		return {"data": job_applicant_summary}

	except Exception as e:
		# ! LOG THE ERROR IF SOMETHING FAILS
		frappe.log_error(
			title="JOB APPLICANT SUMMARY ERROR",
			message=f"ERROR FETCHING JOB APPLICANT SUMMARY FOR {job_opening}: {str(e)}\n{traceback.format_exc()}"
		)
		frappe.throw(f"An error occurred while fetching job applicant summary: {str(e)}")

import frappe


# ! prompt_hr.py.job_opening.release_internal_job_posting
# ? FUNTION TO RELEASE INTERNAL JOB POSTING
@frappe.whitelist()
def release_internal_job_posting(
    due_date,
    min_tenure_in_company,
    min_tenure_in_current_role,
    allowed_department,
    allowed_location,
    allowed_grade,
):
    # ? CONVERT MONTHS TO DAYS
    company_cutoff = frappe.utils.add_days(
        frappe.utils.nowdate(), -(min_tenure_in_company * 30)
    )
    role_cutoff = frappe.utils.add_days(
        frappe.utils.nowdate(), -(min_tenure_in_current_role * 30)
    )

    # ? GET ELIGIBLE EMPLOYEES
    employees = frappe.get_all(
        "Employee",
        filters={
            "status": "Active",
            "department": ["in", allowed_department],
            "location": ["in", allowed_location],
            "grade": ["in", allowed_grade],
            "date_of_joining": ["<=", company_cutoff],
            "current_role_start_date": ["<=", role_cutoff],
        },
        fields=["name", "personal_email"],
    )

    # ? RELEASE JOB POSTING AND COLLECT EMAILS
    emails = []
    for emp in employees:
        doc = frappe.get_doc("Employee", emp.name)
        if hasattr(doc, "release_internal_job_posting"):
            doc.release_internal_job_posting(due_date=due_date)
        if emp.personal_email:
            emails.append(emp.personal_email)

    return emails

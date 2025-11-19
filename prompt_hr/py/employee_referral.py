import frappe


def before_save(doc, method):

    if doc.get("custom_job_opening"):

        job_opening_details = frappe.db.get_value(
            "Job Opening",
            {"name": doc.custom_job_opening, "custom_allow_employee_referance": 1},
            ["custom_due_date_for_applying_job_jr"],
            as_dict=True,
        )

        if job_opening_details and job_opening_details.custom_due_date_for_applying_job_jr:
            if doc.creation > job_opening_details.custom_due_date_for_applying_job_jr:
                frappe.throw(
                    "You cannot refer a candidate after the due date for applying to this job opening."
                )

# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    # Columns of Job Opening Report
    return [
        {
            "fieldname": "job_title",
            "label": _("Job Title"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "custom_job_requisition_record",
            "label": _("Job ID"),
            "fieldtype": "Link",
            "options": "Job Requisition",
            "width": 120,
        },
        {
            "fieldname": "creation",
            "label": _("Created On"),
            "fieldtype": "Datetime",
            "width": 150,
        },
        {
            "fieldname": "owner",
            "label": _("Created By"),
            "fieldtype": "Link",
            "options": "User",
            "width": 120,
        },
        {
            "fieldname": "published_on",
            "label": _("Published On"),
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "fieldname": "published_by",
            "label": _("Published By"),
            "fieldtype": "Link",
            "options": "User",
            "width": 120,
        },
        {
            "fieldname": "requisition_requested",
            "label": _("Requisition Requested"),
            "fieldtype": "Check",
            "width": 100,
        },
        {
            "fieldname": "no_of_positions",
            "label": _("Number Of Openings"),
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 120,
        },
        {
            "fieldname": "sub_department",
            "label": _("Sub Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 120,
        },
        {
            "fieldname": "location",
            "label": _("Location"),
            "fieldtype": "Link",
            "options": "Location",
            "width": 120,
        },
        {
            "fieldname": "target_hire_date",
            "label": _("Target Hire Date"),
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "fieldname": "salary_range_from",
            "label": _("Salary Range (From)"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "salary_range_to",
            "label": _("Salary Range (To)"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "experience",
            "label": _("Experience"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "job_type",
            "label": _("Job Type"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "hiring_managers",
            "label": _("Hiring Managers"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "recruiters",
            "label": _("Recruiters"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "status",
            "label": _("Job Status"),
            "fieldtype": "Select",
            "width": 100,
        },
        {
            "fieldname": "hiring_flow",
            "label": _("Hiring Flow"),
            "fieldtype": "Link",
            "options": "Hiring Flow",
            "width": 120,
        },
        {
            "fieldname": "candidates_sourced",
            "label": _("Candidates Sourced"),
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "fieldname": "candidates_offered",
            "label": _("Candidates Offered"),
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "fieldname": "candidates_hired",
            "label": _("Candidates Hired"),
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "fieldname": "candidates_archived",
            "label": _("Candidates Archived"),
            "fieldtype": "Int",
            "width": 120,
        },
    ]


def get_data(filters):
    # SQL query to fetch job openings based on conditions
    job_openings = frappe.db.sql(
        f"""
        SELECT
            name,
            custom_job_requisition_record,
            job_title,
            department,
            status,
            creation,
            owner,
            IFNULL(custom_no_of_position, 0) as no_of_positions,
            IFNULL(location, NULL) as location,
            IFNULL(lower_range, 0) as salary_range_from,
            IFNULL(upper_range, 0) as salary_range_to,
            IFNULL(custom_job_opening_type, NULL) as job_type
        FROM `tabJob Opening`
        ORDER BY creation DESC
    """,
        as_dict=1,
    )

    # Loop through the fetched job openings and process related data
    for job in job_openings:
        job["hiring_managers"] = None
        job["target_hire_date"] = get_target_hire_date(job)
        job["recruiters"] = get_recruiters(job.name)
        if job.location:
            job["location"] = frappe.get_doc(	
                "Address", job.location
            ).city  # Set location city from Address DocType
        candidates_stats = get_candidate_stats(
            job.name
        )  # Fetch candidate statistics for the job opening
        job["candidates_sourced"] = candidates_stats.get("sourced", 0)
        job["candidates_offered"] = candidates_stats.get("offered", 0)
        job["candidates_hired"] = candidates_stats.get("hired", 0)
        job["candidates_archived"] = candidates_stats.get("archived", 0)

    return job_openings  # Return processed job opening data


def get_recruiters(job_opening):
    doc = frappe.get_doc("Job Opening", job_opening)
    internal_recruiters = frappe.get_all(
        "Internal Recruiter", filters={"parent": doc.name}, fields=["user_name"]
    )
    external_recruiters = frappe.get_all(
        "External Recruiter", filters={"parent": doc.name}, fields=["user_name"]
    )

    recruiters = [rec["user_name"] for rec in internal_recruiters + external_recruiters]
    return ", ".join(recruiters) if recruiters else ""


def get_candidate_stats(job_opening):
    """Calculate and return candidate statistics (sourced, offered, hired, archived) for a job opening."""
    stats = {"sourced": 0, "offered": 0, "hired": 0, "archived": 0}

    candidate_data = frappe.get_all(
        "Job Applicant", fields=["name", "status"], filters={"job_title": job_opening}
    )
    stats["sourced"] = len(candidate_data)

    for data in candidate_data:
        job_offer = frappe.get_all(
            "Job Offer",
            fields=["name"],
            filters={"job_applicant": data.name, "docstatus": ["!=", 2]},
        )
        if job_offer:
            stats["offered"] += 1
            employee_onboarding = frappe.get_all(
                "Employee Onboarding",
                filters={"job_offer": job_offer[0].name, "docstatus": ["!=", 2]},
            )
            if employee_onboarding:
                stats["hired"] += 1

    return stats


def get_target_hire_date(job_opening):
    if job_opening.custom_job_requisition_record:
        job_requisition = frappe.get_doc(
            "Job Requisition", job_opening.custom_job_requisition_record
        )
        return job_requisition.custom_target_hiring_date
    return None

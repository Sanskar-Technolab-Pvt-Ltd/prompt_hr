# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt


import frappe
from frappe import _

def execute(filters=None):
    user = frappe.session.user
    employee_company = frappe.db.get_value("Employee", {"user_id": user}, "company")
    interview_rounds = frappe.get_all(
        "Interview Round",
        filters={"custom_company": employee_company},
        fields=["name"],
        order_by="creation"
    )
    columns = get_columns(interview_rounds)
    data = get_data(employee_company, interview_rounds, filters)
    
    return columns, data

def get_columns(interview_rounds):
    columns = [
        {
            "fieldname": "job_opening",
            "label": _("Job Opening"),
            "fieldtype": "Link",
            "width": 200,
            "options": "Job Opening"
        },
        {
            "fieldname": "requisition_id",
            "label": _("Requisition ID"),
            "fieldtype": "Link",
            "width": 200,
            "options": "Job Requisition"
        },
        {
            "fieldname": "date_of_requisition",
            "label": _("Date of Requisition"),
            "fieldtype": "Date",
            "width": 200,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Select",
            "width": 200,
        },
        {
            "fieldname": "designation",
            "label": _("Position Vacant"),
            "fieldtype": "Link",
            "options": "Designation",
            "width": 200,
        },
        {
            "fieldname": "location",
            "label": _("Location"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 200,
        },
        {
            "fieldname": "no_of_positions",
            "label": _("No Of Openings"),
            "fieldtype": "Int",
            "width": 200,
        },
        {
            "fieldname": "recruiters",
            "label": _("Recruiters"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "sourced",
            "label": _("Sourced"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "screening",
            "label": _("No of Screening Done"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "shortlisted",
            "label": _("Shortlisted"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "selected_in_interview",
            "label": _("Selected in Interview"),
            "fieldtype": "Int",
            "width": 200
        },
        {
            "fieldname": "salary_high",
            "label": _("Salary High"),
            "fieldtype": "Int",
            "width": 200,
        },
        {
            "fieldname": "not_looking_for_change",
            "label": _("Not Looking for Change"),
            "fieldtype": "Int",
            "width": 200,
        },
        {
            "fieldname": "not_responding",
            "label": _("Not Responding"),
            "fieldtype": "Int",
            "width": 200,
        },
        {
            "fieldname": "hold",
            "label": _("Hold"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "preboarding",
            "label": _("Preboarding"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "backout_candidate",
            "label": _("Backout Candidates"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "offer_given",
            "label": _("Offer Given"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "offer_accepted",
            "label": _("Offer Accepted"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "hired",
            "label": _("Hired"),
            "fieldtype": "Int",
            "width": 130
        }
    ]
    # Add Interview Rounds Columns
    for interview_round in interview_rounds:
        columns.append({
            "fieldname": f"interview_round_{interview_round.name}",
            "label": f"{interview_round.name}",
            "fieldtype": "Int",
            "width": 120
        })
    
    # Add "General Remarks for not shortlisting" at the end
    columns.append({
        "fieldname": "general_remarks",
        "label": _("General Remarks for Not Shortlisting"),
        "fieldtype": "Text",
        "width": 250
    })
    
    return columns

def get_data(employee_company, interview_rounds, filters=None):
    statuses = {
        "Shortlisted By Interviewer": "shortlisted",
        "Final Interview Selected": "selected_in_interview",
        "Job Offer Given": "offer_given",
        "Job Offer Accepted": "offer_accepted",
        "Hold": "hold",
        "Screening Test Passed": "screening"
    }
    job_applicants = frappe.get_all("Job Applicant", filters={"custom_company": employee_company}, fields=["job_title", "status"], group_by="job_title")
    
    # Apply filters if provided
    conditions = ""
    if filters and filters.get("job_opening"):
        conditions += f" AND job_title = '{filters.get('job_opening')}'"
    
    total_counts = []
    # Fetch counts for each status
    for job_applicant in job_applicants:
        job_title = job_applicant.get("job_title")
        if not job_title:
            continue
        else:
            # Initialize dict for counts
            counts = {
                "shortlisted": 0,
                "selected_in_interview": 0,
                "offer_given": 0,
                "offer_accepted": 0,
                "hold": 0,
                "screening": 0,
                "preboarding": 0,
                "hired": 0,
                "not_looking_for_change": 0,
                "not_responding": 0,
                "salary_high": 0,
                "backout_candidate": 0
            }
            for status, fieldname in statuses.items():
                count = frappe.db.sql(f"""
                    SELECT COUNT(*) 
                    FROM `tabJob Applicant` 
                    WHERE status = %s {conditions} and job_title = %s
                """, (status, job_title))[0][0]
                counts[fieldname] = count
            counts["job_opening"] = job_title
            counts["designation"] = frappe.db.get_value("Job Opening", job_title, "designation")
            location = frappe.db.get_value("Job Opening", job_title, "location")
            location_name = frappe.db.get_value("Address", location, "address_title")
            counts["location"] = location_name
            counts["department"] = frappe.db.get_value("Job Opening", job_title, "department")
            counts["recruiters"] = get_recruiters(job_title)
            counts["no_of_positions"] = frappe.db.get_value("Job Opening", job_title, "custom_no_of_position")
            counts["requisition_id"] = frappe.db.get_value("Job Opening", job_title, "custom_job_requisition_record")
            counts["date_of_requisition"] = frappe.db.get_value("Job Requisition", counts["requisition_id"], "creation")
            counts["status"] = job_applicant.get("status")
            if not counts["requisition_id"]:
                counts["requisition_id"] = ""
            counts["sourced"] = len(frappe.get_all("Job Applicant", fields=["name"], filters={"job_title": job_title}))
            for interview_round in interview_rounds:
                interview_round_name = interview_round.get("name")
                counts[f"interview_round_{interview_round_name}"] = len(frappe.get_all("Interview", filters={"job_opening": job_title, "interview_round": interview_round_name, "status": "Cleared", "custom_company": employee_company}, group_by="job_applicant"))
            
            # Add General Remarks if not shortlisted
            if counts["shortlisted"] == 0:
                counts["general_remarks"] = "Reason for not shortlisting the candidate"
            else:
                counts["general_remarks"] = ""
            
        total_counts.append(counts)
    
    return total_counts

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

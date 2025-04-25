# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt


import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    # Define columns for each status horizontally
    return [
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
        }
    ]

def get_data(filters=None):
    statuses = {
        "Shortlisted By HR": "shortlisted",
        "Final Interview Selected": "selected_in_interview",
        "Job Offer Given": "offer_given",
        "Job Offer Accepted": "offer_accepted"
    }
    
    # Apply filters if provided
    conditions = ""
    if filters and filters.get("job_opening"):
        conditions += f" AND job_title = '{filters.get('job_opening')}'"
    
    # Initialize dict for counts
    counts = {
        "shortlisted": 0,
        "selected_in_interview": 0,
        "offer_given": 0,
        "offer_accepted": 0
    }
    
    # Fetch counts for each status
    for status, fieldname in statuses.items():
        count = frappe.db.sql(f"""
            SELECT COUNT(*) 
            FROM `tabJob Applicant` 
            WHERE status = %s {conditions}
        """, (status,))[0][0]
        counts[fieldname] = count
    
    return [counts]

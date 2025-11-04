// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["Project-Wise Billing Summary Report"] = {
	 "filters": [
        {
            "fieldname": "project",
            "label": "Project",
            "fieldtype": "Link",
            "options": "Project"
        },
        {
            "fieldname": "start_date",
            "label": "Start Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "end_date",
            "label": "End Date",
            "fieldtype": "Date"
        }
    ]
};

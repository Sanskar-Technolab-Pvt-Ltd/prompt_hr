// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["Applicant Count by Stage for Job Openings"] = {
	filters: [
		{
			fieldname: "job_opening",
			label: __("Job Opening"),
			fieldtype: "Link",
			options: "Job Opening",
		},
	],
};

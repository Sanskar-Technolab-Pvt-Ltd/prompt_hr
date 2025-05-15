// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["OT Register"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_default("company")
		},
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		}
	]
};

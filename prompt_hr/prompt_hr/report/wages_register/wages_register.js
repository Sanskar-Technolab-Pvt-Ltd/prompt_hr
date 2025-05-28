// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["Wages Register"] = {
	filters: [
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
			default: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
			[frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()]

		},
	]
};

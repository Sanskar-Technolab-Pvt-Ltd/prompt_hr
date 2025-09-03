// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Attendance Report"] = {
	"filters": [
		{
			fieldname: "employee",
			label: "Employee",
			fieldtype: "Link",
			options: "Employee"
		},
		{
			fieldname: "attendance_date",
			fieldtype: "Date",
			label: "Attendance Date",
			default: "Today",
		},
		{
			fieldname: "status",
			label: "Status",
			fieldtype: "Select",
			options: "\nPresent\nAbsent\nOn Leave\nHalf Day\nWeekOff\nMispunch",
		}
	]	
};

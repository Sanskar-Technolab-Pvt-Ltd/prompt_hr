// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["Leave Balance Summary"] = {
	filters: [
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.now_date(),
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            reqd:1
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "employee_status",
            label: __("Employee Status"),
            fieldtype: "Select",
            options: [
                "",
                { value: "Active", label: __("Active") },
                { value: "Inactive", label: __("Inactive") },
                { value: "Suspended", label: __("Suspended") },
                { value: "Left", label: __("Left", null, "Employee") },
            ],
            default: "Active",
        },
    ],
    onload: function(report) {
        // Fetch employee linked to current user
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { user_id: frappe.session.user },
                fieldname: "name"
            },
            callback: function(r) {
                if (r.message && r.message.name) {
                    // Set default employee filter value programmatically
                    const employee_filter = report.get_filter('employee');
                    if (employee_filter) {
                        employee_filter.set_input(r.message.name);
                        employee_filter.set_value(r.message.name);
                    }
                }
            }
        });
    }
};

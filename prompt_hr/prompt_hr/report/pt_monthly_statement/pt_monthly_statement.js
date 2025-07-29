// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["PT Monthly Statement"] = {
	filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 0
        }
    ],

	onload: function(report) {
        const roles = frappe.user_roles || [];

        // Button 1: Notify Accountify Team
        if (roles.includes("HR User") || roles.includes("HR Manager")) {
            report.page.add_inner_button("Notify Accountify Team", () => {
                frappe.call({
                    method: "prompt_hr.py.accounting_team_notifications.send_esic_challan_notification",
                    args: {
                        report_name: "PT Monthly Statement",
                        url: window.location.href,
                    },
                    callback: function(r) {
                        if (r.message === "success") {
                            frappe.msgprint("Notification sent to the Accounting team Succesfully.");
                        }
                    }
                });
            }).removeClass("btn-default").addClass("btn-primary");
        }
	}
};

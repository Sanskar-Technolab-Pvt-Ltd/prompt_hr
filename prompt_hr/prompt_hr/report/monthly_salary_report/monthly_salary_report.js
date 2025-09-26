// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Salary Report"] = {
    filters: [
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: "Jan\nFeb\nMar\nApr\nMay\nJun\nJul\nAug\nSep\nOct\nNov\nDec",
            reqd:1,
            default: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            [frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth()]

        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
			reqd:1,
            options: [
                String(new Date().getFullYear()),
                String(new Date().getFullYear() - 1)
            ],
            default: String(new Date().getFullYear())
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 0
        },
		{
        fieldname: "department",
        label: __("Department"),
        fieldtype: "Link",
        options: "Department",
        reqd: 0
    },
    {
        fieldname: "designation",
        label: __("Designation"),
        fieldtype: "Link",
        options: "Designation",
        reqd: 0
    },
    {
        fieldname: "status",
        label: __("Status"),
        fieldtype: "Select",
        options: "Draft\nSubmitted",
        default: "Submitted",
        reqd: 0
    }
    ],

	onload: function(report) {
        const roles = frappe.user_roles || [];

        // Button 1: Notify Accountify Team
        if (roles.includes("S - HR Director (Global Admin)")) {
            report.page.add_inner_button("Notify Accountify Team", () => {
                frappe.call({
                    method: "prompt_hr.py.accounting_team_notifications.send_esic_challan_notification",
                    args: {
                        report_name: "Monthly Salary",
                        url: window.location.href,
                    },
                    callback: function(r) {
                        if (r.message === "success") {
                            frappe.msgprint("Notification sent to Accounting team Succesfully.");
                        }
                    }
                });
            }).removeClass("btn-default").addClass("btn-primary");
        }
	}
};

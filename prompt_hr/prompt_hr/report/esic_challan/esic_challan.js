// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["ESIC_Challan"] = {
    "filters": [],

    onload: function(report) {
        const roles = frappe.user_roles || [];

        // Button 1: Notify Accountify Team
        if (roles.includes("HR User") || roles.includes("HR Manager")) {
            report.page.add_inner_button("Notify Accountify Team", () => {
                frappe.call({
                    method: "prompt_hr.py.accounting_team_notifications.send_esic_challan_notification",
                    args: {
                        report_name: "ESIC Challan",
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

        // Button 2: Create Payment Entry
        if (roles.includes("Accounts User") || roles.includes("Accounts Manager")) {
            report.page.add_inner_button("Create Payment Entry", () => {
                frappe.new_doc("Payment Entry", {
                    payment_type: "Pay",
                    party_type: "Employee",
                });
            }).removeClass("btn-default").addClass("btn-primary");
        }
    }
};

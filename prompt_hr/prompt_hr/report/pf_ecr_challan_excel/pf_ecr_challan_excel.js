// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.query_reports["PF ECR Challan Excel"] = {
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
                        report_name: "PF ECR Challan Excel",
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

        // // Button 2: Create Payment Entry
        // if (roles.includes("Accounts User") || roles.includes("Accounts Manager")) {
        //     report.page.add_inner_button("Create Payment Entry", () => {
        //         frappe.new_doc("Payment Entry", {
        //             payment_type: "Pay",
        //             party_type: "Employee",
        //         });
        //     }).removeClass("btn-default").addClass("btn-primary");
        // }
    
        report.page.add_inner_button('Download Text File', async function() {
            // 1. Fetch the report data
            const result = await frappe.call({
                method: "frappe.desk.query_report.run",
                args: {
                    report_name: "PF ECR Challan Excel",
                    filters: report.get_filter_values()
                }
            });
            // 2. Process the data
            const data = result.message.result;
            const columns = result.message.columns.map(col => col.label);

            // 3. Format as text with #~# separator
            let lines = [];
            data.forEach(row => {
				const rowText = Object.values(row).map(val => {
					// If value is null, undefined, or empty string
					if (val === null || val === undefined || val === '') {
						// If the value is expected to be a number, put 0, else null
						// Try to detect number type
						return typeof val === 'number' || (!isNaN(val) && val !== '') ? 0 : 'Null';
					}
					// If value is a number, return as is
					if (typeof val === 'number') return val;
					// For other types, return as is
					return val;
				}).join("#~#");
				lines.push(rowText);
			});

            const textContent = lines.join("\n");

            // 4. Trigger download
            const blob = new Blob([textContent], {type: "text/plain"});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "pf_ecr_challan_report.txt";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 'Actions');
    },
};

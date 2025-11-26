frappe.ui.form.on("Loan", {
    refresh(frm) {
        if (!frm.doc.name) return;

        // Find connected Loan Repayment Schedule (via Dynamic Link)
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Loan Repayment Schedule",
                filters: {
                    "loan": frm.doc.name
                },
                fields: ["name"],
                limit_page_length: 1
            },
            callback(res) {
                if (!res.message || res.message.length === 0) return;

                let schedule_name = res.message[0].name;

                // Now get the repayment schedule child table (repayment schedule rows)
                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Loan Repayment Schedule",
                        name: schedule_name
                    },
                    callback(r2) {
                        if (!r2.message || !r2.message.repayment_schedule) return;

                        let rows = r2.message.repayment_schedule;

                        if (rows.length > 0) {
                            // last row date
                            let last_payment_date = rows[rows.length - 1].payment_date;

                            // Set in Loan form
                            frm.set_value("custom_repayment_end_date", last_payment_date);
                        }
                    }
                });
            }
        });
    }
});

// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Gratuity", {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__("Create Payment Entry"), function () {
                frappe.model.with_doctype("Payment Entry", () => {
                    const doc = frappe.model.get_new_doc("Payment Entry");
                    frappe.set_route("Form", "Payment Entry", doc.name);

                    // Wait for Payment Entry form to load
                    const wait = setInterval(() => {
                        if (cur_frm && cur_frm.docname === doc.name && cur_frm.is_new()) {
                            clearInterval(wait);

                            // Step 1: Set Payment Type
                            cur_frm.set_value("payment_type", "Pay");
                            // Step 2: Set Party Type
                            cur_frm.set_value("company", frm.doc.company);
                            setTimeout(() => {
                                cur_frm.set_value("party_type", "Employee");
                            }, 150);
                            // Step 3: Set Party after a delay
                            setTimeout(() => {
                                cur_frm.set_value("party", frm.doc.employee);
                            }, 200);
                            // Step 4: Set Party Balance after a delay
                            setTimeout(() => {
                                cur_frm.set_value("party_balance", frm.doc.gratuity_amount);
                            }, 300);
                        }
                    }, 100);
                });
            }).removeClass("btn-default").addClass("btn-primary");
        }
    },
    employee(frm) {
        frm.set_value("total_working_year", null);
        frm.set_value("last_salary_slip", null);
        frm.set_value("gratuity_amount", null);
        frm.set_value("last_drawn_salary", null);
        if (frm.doc.employee) {
            setTimeout(() => {
                // IF Date of Leaving is not set, then throw error
                if (!frm.doc.date_of_leaving) {
                    frappe.throw(__("Relieving Date is mandatory for gratuity calculation"));
                } else {
                    const diff = frappe.datetime.get_diff(frm.doc.date_of_leaving, frm.doc.date_of_joining);
                    frm.set_value("total_working_year", parseFloat((diff / 365).toFixed(1))); // Set total working years
                }
            }, 50);
        }
    },
});

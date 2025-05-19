// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Gratuity", {
    employee(frm) {
        frm.set_value("total_working_year", null);
        if (frm.doc.employee) {
            setTimeout(() => {
                // IF Date of Leaving is not set, then throw error
                if (!frm.doc.date_of_leaving) {
                    frappe.throw(__("Relieving Date is mandatory for gratuity calculation"));
                } else {
                    const diff = frappe.datetime.get_diff(frm.doc.date_of_leaving, frm.doc.date_of_joining);
                    frm.set_value("total_working_year", diff / 365); // Set total working years
                }
            }, 300);
        }
    }
});

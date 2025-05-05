// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Regularization", {
	refresh(frm) {
        const user = frappe.session.user
        if (frm.doc.employee) {
            frappe.call({
                "method": "prompt_hr.py.utils.check_user_is_reporting_manager",
                "args": {
                    user_id: user,
                    requesting_employee_id: frm.doc.employee
                },
                callback: function (r) {
                    if (!r.message.error) {
                        if (r.message.is_rh) {
                            frm.set_df_property("status", "hidden", 0)
                        }
                    } else if (r.message.error) {
                        frappe.throw(r.message.message)
                    }
                }
            })
        }
	},
});

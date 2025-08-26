// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Regularization", {
    refresh(frm) {
        if (frm.doc.employee && !frm.is_new()){
            frappe.call({
                method: "prompt_hr.py.utils.check_user_is_reporting_manager",
                args: {
                    user_id: frappe.session.user,
                    requesting_employee_id: frm.doc.employee
                },
                callback: function (res) {
                    if (!res.message.error) {
                        if (res.message.is_rh) {
                            if (!has_common(frappe.user_roles, ["S - HR Director (Global Admin)", "System Manager"])) {
                                frm.fields.filter(field => field.has_input).forEach(field => {
                                    frm.set_df_property(field.df.fieldname, "read_only", 1);
                                });
                                
                                frm.set_df_property("checkinpunch_details", "read_only", 1);
                                frm.refresh_field("checkinpunch_details");
                            }
                        }
                        else {
                            if (!has_common(frappe.user_roles, ["S - HR Director (Global Admin)", "System Manager"])) {
                                frm.fields.filter(field => field.has_input).forEach(field => {                                    
                                    frm.set_df_property(field.df.fieldname, "read_only", 1);
                                });                                       
                                frm.set_df_property("checkinpunch_details", "read_only", 1);
                                frm.refresh_field("checkinpunch_details");
                            }
                        }
                    } else if (res.message.error) {
                        frappe.throw(res.message.message)
                    }
                }
            })
        }
    }
});

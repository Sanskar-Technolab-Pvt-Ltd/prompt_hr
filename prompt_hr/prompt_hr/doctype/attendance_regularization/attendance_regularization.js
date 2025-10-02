// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Regularization", {
    refresh(frm) {
        if (frm.doc.employee && !frm.is_new()) {
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
    },
    before_workflow_action: async (frm) => {

        if (frm.selected_workflow_action === "Reject" && (frm.doc.reason_for_rejection || "").length < 1) {
            let promise = new Promise((resolve, reject) => {
                frappe.dom.unfreeze()

                frappe.prompt({
                    label: 'Reason for rejection',
                    fieldname: 'reason_for_rejection',
                    fieldtype: 'Small Text',
                    reqd: 1
                }, (values) => {
                    if (values.reason_for_rejection) {
                        frm.set_value("reason_for_rejection", values.reason_for_rejection)
                        frm.save().then(() => {
                            resolve();
                        }).catch(reject);
                    }
                    else {
                        reject()
                    }
                })
            });
            await promise.catch(() => frappe.throw());
        }
    },

    regularization_date: (frm) => {
        populate_checkin_punch_table(frm);
    }
});

// ? FUNCTION TO POPULATE CHECK-IN / PUNCH DETAILS TABLE (PAIR IN/OUT WITH BLANKS IF MISSING)
function populate_checkin_punch_table(frm) {
    if (!frm.doc.regularization_date || !frm.doc.employee) return;

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee Checkin',
            filters: {
                employee: frm.doc.employee,
                time: ['between', [
                    frm.doc.regularization_date,
                    frm.doc.regularization_date
                ]]
            },
            fields: ['name', 'time', 'log_type'],
            order_by: 'time asc'
        },
        callback: function (res) {
            if (!res.message) return;

            let punches = res.message;
            let paired_rows = [];
            let current_in = null;

            // helper to extract only HH:mm:ss from datetime
            const extractTime = (dt) => dt ? dt.split(" ")[1] : "";

            punches.forEach(entry => {
                if (entry.log_type === "IN") {
                    current_in = {
                        in_time: extractTime(entry.time),
                        out_time: ""
                    };
                } else if (entry.log_type === "OUT") {
                    if (current_in) {
                        current_in.out_time = extractTime(entry.time);
                        paired_rows.push(current_in);
                        current_in = null;
                    } else {
                        paired_rows.push({
                            in_time: "",
                            out_time: extractTime(entry.time)
                        });
                    }
                }
            });

            if (current_in) {
                paired_rows.push(current_in);
            }

            frm.set_value("checkinpunch_details", paired_rows);
            frm.refresh_field("checkinpunch_details");
        }
    });
}


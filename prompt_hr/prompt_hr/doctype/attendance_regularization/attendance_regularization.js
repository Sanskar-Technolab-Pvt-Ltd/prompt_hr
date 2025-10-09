// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Regularization", {
    refresh(frm) {

        display_existing_checkin_punch_details(frm);

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
        display_existing_checkin_punch_details(frm);
    }
});

// ? GENERIC FUNCTION TO FETCH CHECK-IN / PUNCH DETAILS
function get_checkin_punch_details(employee, regularization_date) {
    if (!employee || !regularization_date) return Promise.resolve([]);

    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'prompt_hr.api.mobile.attendance_regularization.get_checkin_punch_details',
            args: {
                employee: employee,
                regularization_date: regularization_date
            },
            callback: function (res) {
                if (res && res.message) {
                    resolve(Array.isArray(res.message.data) ? res.message.data : [res.message]);
                } else {
                    resolve([]);
                }
            },
            error: function (err) {
                reject(err);
            }
        });
    });
}


// ? FUNCTION TO POPULATE CHECK-IN / PUNCH DETAILS TABLE
async function populate_checkin_punch_table(frm) {
    if (!frm.doc.regularization_date || !frm.doc.employee || !frm.is_new()) return;

    let punches = await get_checkin_punch_details(frm.doc.employee, frm.doc.regularization_date);
    console.log("Fetched Punches:", punches);

    if (!punches.length) {
        frm.set_value("checkinpunch_details", []);
        frm.refresh_field("checkinpunch_details");
        return;
    }

    // ? IF YOUR BACKEND ALREADY RETURNS PAIRED ROWS, JUST SET THE TABLE DIRECTLY
    frm.set_value("checkinpunch_details", punches);
    frm.refresh_field("checkinpunch_details");
}


// ? FUNCTION TO DISPLAY EXISTING CHECK-IN / PUNCH DETAILS IN HTML
async function display_existing_checkin_punch_details(frm) {
    if (!frm.doc.employee || !frm.doc.regularization_date) return;

    let checkinpunch_details = await get_checkin_punch_details(frm.doc.employee, frm.doc.regularization_date);

    // If no data, show message
    if (!checkinpunch_details || !checkinpunch_details.length) {
        frm.fields_dict.existing_check_in_check_out_logs.wrapper.innerHTML =
            `<h5>Original Punch Logs</h5>
             <div class="text-muted">No check-in/punch data available.</div>`;
        return;
    }

    // Build HTML table with heading
    let html = `
        <h5>Original Logs</h5>
        <div class="table-responsive">
            <table class="table table-bordered table-striped">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>IN Time</th>
                        <th>OUT Time</th>
                    </tr>
                </thead>
                <tbody>
    `;

    checkinpunch_details.forEach((entry, index) => {
        html += `
            <tr>
                <td>${index + 1}</td>
                <td>${entry.in_time || "-"}</td>
                <td>${entry.out_time || "-"}</td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    // Inject HTML into your HTML field
    frm.fields_dict.existing_check_in_check_out_logs.wrapper.innerHTML = html;
}



// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exit Approval Process', {
    refresh: function(frm) {
        if (frm.doc.resignation_approval == "Approved") {
            // ? ADD THE "RAISE EXIT CHECKLIST" BUTTON
            add_raise_exit_checklist_button(frm);

            // ? ADD THE "RAISE EXIT INTERVIEW QUESTIONNAIRE" BUTTON
            add_raise_exit_interview_button(frm);
        }

        // ? HIDE MARKS AND MARKS OUT OF FIELD OF THE CHILD TABLE
        prompt_hr.utils.update_child_table_columns(frm, "user_response", ["is_correct", "marks", "marks_out_of"]);
    },

    // ? TRIGGERED WHEN NOTICE PERIOD DAYS IS CHANGED
    notice_period_days: function(frm) {
        update_last_date_of_working(frm);
    },

    // ? TRIGGERED WHEN LAST DATE OF WORKING IS CHANGED
    last_date_of_working: function(frm) {
        update_notice_period_days(frm);
    }
});

// ? FUNCTION TO UPDATE LAST DATE OF WORKING BASED ON NOTICE PERIOD DAYS
function update_last_date_of_working(frm) {
    if (frm.doc.posting_date && frm.doc.notice_period_days) {
        const posting_date = frappe.datetime.str_to_obj(frm.doc.posting_date);
        const new_date = frappe.datetime.add_days(posting_date, frm.doc.notice_period_days);
        frm.set_value("last_date_of_working", frappe.datetime.obj_to_str(new_date));
    }
}

// ? FUNCTION TO UPDATE NOTICE PERIOD DAYS BASED ON LAST DATE OF WORKING
function update_notice_period_days(frm) {
    if (frm.doc.posting_date && frm.doc.last_date_of_working) {
        const posting_date = frappe.datetime.str_to_obj(frm.doc.posting_date);
        const end_date = frappe.datetime.str_to_obj(frm.doc.last_date_of_working);
        const diff = frappe.datetime.get_diff(end_date, posting_date);
        frm.set_value("notice_period_days", diff);
    }
}

// ? ADD THE "RAISE EXIT CHECKLIST" BUTTON
function add_raise_exit_checklist_button(frm) {
    frm.add_custom_button('Raise Employee Separation', function () {
        frappe.dom.freeze("Creating Employee Separation...");

        frappe.call({
            method: 'prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process.raise_exit_checklist',
            args: {
                employee: frm.doc.employee,
                company: frm.doc.company,
                exit_approval_process: frm.doc.name
            },
            callback: function (r) {
                frappe.dom.unfreeze();

                if (r.message) {
                    const res = r.message;

                    frappe.show_alert({
                        message: res.message,
                        indicator: res.status === "success" ? "green" : (res.status === "info" ? "blue" : "red")
                    });

                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                }
            },
            error: function () {
                frappe.dom.unfreeze();
                frappe.msgprint("Something went wrong while raising Employee Separation.");
            }
        });
    });
}

// ? FUNCTION TO ADD THE "RAISE EXIT INTERVIEW QUESTIONNAIRE" BUTTON
function add_raise_exit_interview_button(frm) {
    frm.add_custom_button('Raise Exit Interview Questionnaire', function () {
        frappe.dom.freeze("Creating Exit Interview Questionnaire...");

        frappe.call({
            method: 'prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process.raise_exit_interview',
            args: {
                employee: frm.doc.employee,
                company: frm.doc.company,
                exit_approval_process: frm.doc.name
            },
            callback: function (r) {
                frappe.dom.unfreeze();

                if (r.message) {
                    const res = r.message;

                    frappe.show_alert({
                        message: res.message,
                        indicator: res.status === "success" ? "green" : (res.status === "info" ? "blue" : "red")
                    });

                    setTimeout(() => {
                            window.location.reload();
                        }, 3000);
                    
                }
            },
            error: function () {
                frappe.dom.unfreeze();
                frappe.msgprint("Something went wrong while raising Exit Interview Questionnaire.");
            }
        });
    });
}

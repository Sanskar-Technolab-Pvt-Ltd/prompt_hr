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
	frm.add_custom_button('Raise Exit Checklist', function () {
		frappe.call({
            method: 'prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process.raise_exit_checklist',
            args: {
                employee: frm.doc.employee,
                company: frm.doc.company,
            },
            callback: function (r) {
                console.log(r);
                if (r.message) {
                    // Optionally tick checkbox if it's a success message
                    if (r.message.status.includes("success")) {
                        frm.set_value("raise_exit_checklist", 1);
                        frm.save().then(() => {
                            frappe.show_alert({
                                message: __('Exit Checklist Raised'),
                                indicator: 'green'
                            });
                        }
                        );
                    }
                    else {
                        frappe.show_alert({
                            message: __('Exit Checklist Not Raised'),
                            indicator: 'red'
                        });
                    }
                }
            }
        });
        
	});
}

// ? FUNCTION TO ADD THE "RAISE EXIT INTERVIEW QUESTIONNAIRE" BUTTON
function add_raise_exit_interview_button(frm) {
    frm.add_custom_button('Raise Exit Interview Questionnaire', function () {
        frappe.call({
            method: 'prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process.raise_exit_interview',
            args: {
                employee: frm.doc.employee,
                company: frm.doc.company,
                exit_approval_process: frm.doc.name
            },
            callback: function (r) {
                if (r.message) {
                    const res = r.message;
                    
                    // ? SHOW MESSAGE BASED ON RESPONSE STATUS
                    if (res.status === "success") {
                        frappe.msgprint({
                            title: __("Success"),
                            indicator: "green",
                            message: res.message
                        });

                        // ? RELOAD THE DOCUMENT AFTER 3 SECONDS
                        setTimeout(() => {
                            frappe.reload_doc();
                        }, 3000);
                    }
                     else if (res.status === "info") {
                        frappe.msgprint({
                            title: __("Info"),
                            indicator: "blue",
                            message: res.message
                        });
                    } else if (res.status === "error") {
                        frappe.msgprint({
                            title: __("Error"),
                            indicator: "red",
                            message: res.message
                        });
                    }
                }
            }
        });
    });
}

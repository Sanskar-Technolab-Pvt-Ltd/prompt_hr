// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exit Approval Process', {
    refresh: function(frm) {

        // ? ADD THE "RAISE EXIT CHECKLIST" BUTTON
        add_raise_exit_checklist_button(frm);
        // ? ADD THE "RAISE EXIT CHECKLIST" BUTTON
        add_raise_exit_interview_button(frm);
    }
});

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
            },
            callback: function (r) {
                console.log(r);
                if (r.message) {
                    
                }
            }
        });
    });
}

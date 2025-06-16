
frappe.ui.form.on('Exit Interview', {
    refresh(frm) {
        console.log("Exit Interview Form Refreshed");

        // ? REMOVE SEND EXIT QUESTIONNAIRE BUTTON
        remove_send_exit_interview_button(frm);

        // ? ADD CUSTOM BUTTON TO RAISE EXIT INTERVIEW QUESTIONNAIRE
        add_invite_for_exit_interview_button(frm);

        // ? HIDE MARKS AND MARKS OUT OF FIELD OF THE CHILD TABLE
        prompt_hr.utils.update_child_table_columns(frm,"custom_questions",["is_correct","marks","marks_out_of"]);
    },
});


// ? FUNCTION TO REMOVE THE "SEND EXIT QUESTIONNAIRE" BUTTON
function remove_send_exit_interview_button(frm) {
    // ? REMOVE CUSTOM BUTTON
    frm.remove_custom_button('Send Exit Questionnaire');
}

function add_invite_for_exit_interview_button(frm) {
    // ? ADD CUSTOM BUTTON TO INVITE FOR EXIT INTERVIEW
    frm.add_custom_button('Invite for Exit Interview', function () {
        frappe.call({
            method: 'prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process.send_exit_interview_notification',
            args: {
                employee: frm.doc.employee,
                exit_interview_name: frm.doc.name,
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
                    } else if (res.status === "info") {
                        frappe.msgprint({
                            title: __("Info"),
                            indicator: "blue",
                            message: res.message
                        });
                    } else {
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
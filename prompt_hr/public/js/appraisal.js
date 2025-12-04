frappe.ui.form.on("Appraisal", {
    refresh(frm) { 
        //
        if(frm.doc.docstatus === 1) {
            frm.add_custom_button("Send Performance Appraisal Letter", function() {
                frappe.dom.freeze("Sending Performance Appraisal Letter...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name },
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // No Approval Record → Simple dialog
                        if (!record) {
                            show_performance_letter_letter_dialog(frm);
                            return;
                        }

                        // Approval exists but NOT Final Approval → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(
                                __(`Performance Appraisal Letter is under approval: ${frm.doc.applicant_name}`)
                            );
                            return;
                        }

                        // FINAL APPROVAL → 2 OPTIONS
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    label: "Choose Action",
                                    fieldtype: "Select",
                                    options: [
                                        "Resend Performance Appraisal Letter",
                                        "Send with TO/CC"
                                    ],
                                    reqd: 1
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Performance Appraisal Letter") {
                                    // ✔ No TO/CC dialog
                                    show_performance_letter_letter_dialog(frm);
                                }

                                if (values.action === "Send with TO/CC") {
                                    // ✔ TO/CC dialog
                                    show_performance_letter_to_cc_dialog(frm);
                                }

                            },
                            __("Performance Appraisal Letter Already Approved"),
                            __("Continue")
                        );
                    }
                });

            });

        }
    }
});


function show_performance_letter_letter_dialog(frm) {
    const employee_id = frm.doc.employee;

    if (!employee_id) {
        frappe.throw("applicant is missing in this Appraisal Letter.");
        return;
    }

    // Fetch company & personal email from Employee
    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Appraisal Letter'),
            fields: [
                {
                    fieldname: 'send_company_email',
                    fieldtype: 'Check',
                    label: __('Send to Company Email') + 
                        (company_email ? ` (${company_email})` : " (Not Available)"),
                    default: company_email ? 1 : 0,
                    depends_on: () => company_email ? 1 : 0
                },
                {
                    fieldname: 'send_personal_email',
                    fieldtype: 'Check',
                    label: __('Send to Personal Email') + 
                        (personal_email ? ` (${personal_email})` : " (Not Available)"),
                    default: personal_email ? 1 : 0,
                    depends_on: () => personal_email ? 1 : 0
                }
            ],

            primary_action_label: __('Send'),

            primary_action(values) {

                // Validation — at least ONE option
                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw(__('Please select at least one email option.'));
                }

                frappe.dom.freeze(__('Sending Apprisal Letter...'));

                // Fetch EMPLOYEE of CURRENT USER → For released_by
                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                )
                .then(emp => {

                    const released_by =
                        emp && emp.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.appraisal_letter.create_appraisal_letter_approval",
                        args: {    
                            employee_id: employee_id,
                            letter: "Prompt Equipments _ Performance Appraisal Letter (Oct) (Eng) Gross New",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by,  
                        },

                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message && r.message.status === "success") {
                                frappe.msgprint({
                                    message: r.message.message,
                                    indicator: 'green'
                                });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || __('Failed to send loan agreement.'),
                                    indicator: 'red'
                                });
                            }
                        },

                        error(err) {
                            frappe.dom.unfreeze();
                            frappe.msgprint({
                                message: __('Something went wrong.'),
                                indicator: 'red'
                            });
                            console.error(err);
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}


function show_performance_letter_to_cc_dialog(frm,) {
    let d = new frappe.ui.Dialog({
        title:"Send Loan Agreement",
        fields: [
            {
                fieldname: "recipient_table",
                label: "Recipients",
                fieldtype: "Table",
                cannot_add_rows: false,
                in_place_edit: true,
                fields: [
                    {
                        fieldtype: "Select",
                        fieldname: "recipient_type",
                        label: "Type",
                        options: ["To", "CC"],
                        in_list_view: 1,
                        reqd: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        in_list_view: 1,
                        reqd: 1,
                        get_query: () => {
                            return {
                                query: "frappe.core.doctype.user.user.user_query"
                            };
                        }
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",
        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // Applicant email always goes in TO list
            if (frm.doc.applicant_email) {
                to_users.push(frm.doc.applicant_email);
            }

            // Separate TO and CC users
            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            // Call function 
            frappe.call({
                method: "prompt_hr.py.appraisal_letter.trigger_apprisal_notification",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Appraisal Letter");
                    d.hide();
                }
            });

            d.hide();
        }
    });

    d.show();
}

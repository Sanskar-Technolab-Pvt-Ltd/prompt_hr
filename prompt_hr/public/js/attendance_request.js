frappe.ui.form.on('Attendance Request', {
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee',
                    filters: {
                        user_id: frappe.session.user
                    },
                    fields: ['name', 'employee_name'],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value('employee', r.message[0].name);
                    }
                }
            });
        }
    },

    refresh: function (frm) {
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
                            }
                        }
                        else {
                            if (!has_common(frappe.user_roles, ["S - HR Director (Global Admin)", "System Manager"])) {
                                frm.fields.filter(field => field.has_input).forEach(field => {                                    
                                    frm.set_df_property(field.df.fieldname, "read_only", 1);
                                });                                       
                            }
                        }
                    } else if (res.message.error) {
                        frappe.throw(res.message.message)
                    }
                }
            })
        }

        if (!frm.is_new() && frm.doc.docstatus == 0){
            add_custom_workflow_buttons(frm)
        }

        if (frm.doc.company) {
            set_partial_day_option(frm)
        }
    },
    employee: function (frm) {
        
            set_partial_day_option(frm)
    
    }
});

function add_custom_workflow_buttons(frm) {
    // HIDE DEFAULT WORKFLOW PRIMARY BUTTONS
    $('.btn.btn-primary.btn-sm').not('.primary-action').hide();
    frappe.call({
        method: "frappe.model.workflow.get_transitions",
        args: { doc: frm.doc },
        callback: function (r) {
            if (r.message) {
                let unique_buttons = [...new Set(r.message.map(t => t.action))];
                setTimeout(() => {
                    unique_buttons.forEach(action => {
                        frm.add_custom_button(
                            __(action),
                            function () {
                                if (action === "Reject" && frm.doc.custom_reason_for_rejection.length < 1) {
                                    frappe.prompt({
                                        label: 'Reason for rejection',
                                        fieldname: 'reason_for_rejection',
                                        fieldtype: 'Small Text',
                                        reqd: 1
                                    }, (values) => {
                                        if (values.reason_for_rejection) {
                                            frappe.call({
                                                method: "prompt_hr.overrides.attendance_request_override.handle_custom_workflow_action",
                                                args: {
                                                    "doc": frm.doc,
                                                    "action": action,
                                                    "reason_for_rejection": values.reason_for_rejection
                                        
                                                },
                                                callback: function (r) {
                                                    if (r.message) {
                                                        frappe.set_route("Form", "Attendance Request", r.message);
                                                    }
                                                }
                                            });
                                        }
                                    })
                                }
                                else {
                                    frappe.call({
                                        method: "prompt_hr.overrides.attendance_request_override.handle_custom_workflow_action",
                                        args: {
                                            "doc": frm.doc,
                                            "action": action
                                        },
                                        callback: function (r) {
                                            if (r.message) {
                                                frappe.set_route("Form", "Attendance Request", r.message);
                                            }
                                        }
                                    });
                                }
                                
                            },
                            __("Actions")
                        )

                    });
                }, 10);
            }
        }
    });
}


function set_partial_day_option(frm) {
    console.log("Function Ran", frm.doc.company)

    frappe.call({
        method: 'prompt_hr.py.utils.fetch_company_name',
        args: {
            "prompt": 1
        },
        callback: function (res) {

            options = {
                "default_options": ['Work From Home', 'On Duty'],
                "prompt_options": ['Work From Home', 'On Duty', 'Partial Day']
            }

            if (!res.message.error && res.message.company_id == frm.doc.company){
                
                frm.set_df_property('reason', 'options', options["prompt_options"])
                
            }
            else if (res.message.error) {
                frappe.throw(res.message.message)
            }
            else {
                
                frm.set_df_property('reason', 'options', options["default_options"])
            }
        }
    })
}
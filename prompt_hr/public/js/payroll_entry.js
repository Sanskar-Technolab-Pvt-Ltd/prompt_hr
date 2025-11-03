// ? CHILD TABLE BUTTON HANDLER FOR "Process FnF" BUTTON IN EACH ROW
frappe.ui.form.on('Pending FnF Details', {
    process_fnf: function (frm, cdt, cdn) {
        // ? FETCH ROW DATA
        const row = locals[cdt][cdn];

        // ? SAFEGUARD: SKIP IF NO EMPLOYEE
        if (!row.employee) {
            frappe.msgprint("Employee not found in this row.");
            return;
        }

        if (row.fnf_record) {            
            frappe.set_route('Form', "Full and Final Statement", row.fnf_record);
        }
        else {
            frappe.route_options = {
                "employee": row.employee,
                "custom_payroll_entry": frm.doc.name
            }
            frappe.set_route("Form", "Full and Final Statement", "new")



            // const emp = encodeURIComponent(row.employee);
            // // ? REDIRECT TO FULL AND FINAL FORM WITH EMPLOYEE IN URL
            // window.location.href = `${window.location.origin}/app/full-and-final-statement/new-1?employee=${emp}`;            
        }
    }
});


frappe.ui.form.on("Payroll Entry", {
    refresh: (frm) => {
        if (!frm.is_new()) {
            disable_fields_for_completed_steps(frm)
        }
        update_fnf_button(frm)
        // if (frm.doc.docstatus === 0 && !frm.is_new()) {
		// 	frm.page.clear_primary_action();
		// 	frm.add_custom_button(__("Get Employees"), function () {
		// 		console.log("Custom is getting called stl")
		// 		frm.events.get_employee_details(frm);
		// 	}).toggleClass("btn-primary", !(frm.doc.employees || []).length);
		// }


        // ? CODE TO APPLY FILTERS TO EMPLOYEE FIELD IN SALARY WITHHOLDING DETAILS CHILD TABLE BASED ON EMPLOYEES IN EMPLOYEE DETAILS 
        employee_ids = (frm.doc.employees || []).map(row => row.employee).filter(Boolean);
        if (employee_ids) {
            frm.set_query("employee", "custom_salary_withholding_details", function (doc, cdt, cdn) {
                return {
                    "filters": {
                        "name": ["in", employee_ids]
                    },
                };
            });
        }

        // ? REMOVE AUTO BRANCH ADDITION DATA
        empty_branch_field_if_form_is_new(frm);
        send_salary_slip(frm)

        if(frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Import Adhoc Salary Details'), function() {
                let dialog = new frappe.ui.Dialog({
                    title: 'Import Adhoc Salary Details',
                    fields: [
                        {
                            label: 'Upload Excel File',
                            fieldname: 'excel_file',
                            fieldtype: 'Attach',
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Import',
                    primary_action(values) {
                        if (!values.excel_file) {
                            frappe.msgprint('Please upload a Excel file.');
                            return;
                        }
                        // Fetch file content using frappe.call
                        frappe.call({
                            method: "frappe.client.get_value",
                            args: {
                                doctype: "File",
                                filters: { file_url: values.excel_file },
                                fieldname: "file_url"
                            },
                            callback: function(r) {
                                if (r.message && r.message.file_url) {
                                    const file_url = r.message.file_url;
                                    
                                    frappe.call({
                                        method: "prompt_hr.py.payroll_entry.import_adhoc_salary_details",
                                        args: {
                                            payroll_entry_id: frm.doc.name,
                                            file_url: file_url
                                        },
                                        freeze: true,
                                        callback: function(r) {
                                            dialog.hide();
                                            frm.reload_doc();
                                        }
                                    });
                                            
                                }
                            }
                        });
                    }
                });

                // Add Download Template button
                dialog.$wrapper
                    .find('.modal-footer')
                    .prepend(
                        `<button class="btn btn-secondary btn-download-template" style="margin-right: 8px;">
                            Download Template
                        </button>`
                    );

                // Handle Download Template click
                dialog.$wrapper.find('.btn-download-template').on('click', function() {
                    if (!frm.doc.name) {
                        frappe.msgprint("Please save the Payroll Entry first.");
                        return;
                    }
                    window.open(
                        `/api/method/prompt_hr.py.payroll_entry.download_adhoc_salary_template?payroll_entry_id=${frm.doc.name}`
                    );
                });

                dialog.show();
            }, __("Data Import"))

            frm.add_custom_button(__('Import LOP Summary Details'), function() {
                let dialog = new frappe.ui.Dialog({
                    title: 'Import LOP Summary Details',
                    fields: [
                        {
                            label: 'Upload Excel File',
                            fieldname: 'excel_file',
                            fieldtype: 'Attach',
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Import',
                    primary_action(values) {
                        if (!values.excel_file) {
                            frappe.msgprint('Please upload a Excel file.');
                            return;
                        }
                        // Fetch file content using frappe.call
                        frappe.call({
                            method: "frappe.client.get_value",
                            args: {
                                doctype: "File",
                                filters: { file_url: values.excel_file },
                                fieldname: "file_url"
                            },
                            callback: function(r) {
                                if (r.message && r.message.file_url) {
                                    const file_url = r.message.file_url;
                                    
                                    frappe.call({
                                        method: "prompt_hr.py.payroll_entry.import_lop_summary_details",
                                        args: {
                                            payroll_entry_id: frm.doc.name,
                                            file_url: file_url
                                        },
                                        freeze: true,
                                        callback: function(r) {
                                            dialog.hide();
                                            frm.reload_doc();
                                        }
                                    });
                                            
                                }
                            }
                        });
                    }
                });

                // Add Download Template button
                dialog.$wrapper
                    .find('.modal-footer')
                    .prepend(
                        `<button class="btn btn-secondary btn-download-template" style="margin-right: 8px;">
                            Download Template
                        </button>`
                    );

                // Handle Download Template click
                dialog.$wrapper.find('.btn-download-template').on('click', function() {
                    if (!frm.doc.name) {
                        frappe.msgprint("Please save the Payroll Entry first.");
                        return;
                    }
                    window.open(
                        `/api/method/prompt_hr.py.payroll_entry.download_lop_summary_template?payroll_entry_id=${frm.doc.name}`
                    );
                });

                dialog.show();
            }, __("Data Import"))

            frm.add_custom_button(__('Import LOP Reversal Details'), function() {
                let dialog = new frappe.ui.Dialog({
                    title: 'Import LOP Reversal Details',
                    fields: [
                        {
                            label: 'Upload Excel File',
                            fieldname: 'excel_file',
                            fieldtype: 'Attach',
                            reqd: 1
                        }
                    ],
                    primary_action_label: 'Import',
                    primary_action(values) {
                        if (!values.excel_file) {
                            frappe.msgprint('Please upload a Excel file.');
                            return;
                        }
                        // Fetch file content using frappe.call
                        frappe.call({
                            method: "frappe.client.get_value",
                            args: {
                                doctype: "File",
                                filters: { file_url: values.excel_file },
                                fieldname: "file_url"
                            },
                            callback: function(r) {
                                if (r.message && r.message.file_url) {
                                    const file_url = r.message.file_url;
                                    
                                    frappe.call({
                                        method: "prompt_hr.py.payroll_entry.import_lop_reversal_details",
                                        args: {
                                            payroll_entry_id: frm.doc.name,
                                            file_url: file_url
                                        },
                                        freeze: true,
                                        callback: function(r) {
                                            dialog.hide();
                                            frm.reload_doc();
                                        }
                                    });
                                            
                                }
                            }
                        });
                    }
                });

                // Add Download Template button
                dialog.$wrapper
                    .find('.modal-footer')
                    .prepend(
                        `<button class="btn btn-secondary btn-download-template" style="margin-right: 8px;">
                            Download Template
                        </button>`
                    );

                // Handle Download Template click
                dialog.$wrapper.find('.btn-download-template').on('click', function() {
                    if (!frm.doc.name) {
                        frappe.msgprint("Please save the Payroll Entry first.");
                        return;
                    }
                    window.open(
                        `/api/method/prompt_hr.py.payroll_entry.download_lop_reversal_template?payroll_entry_id=${frm.doc.name}`
                    );
                });

                dialog.show();
            }, __("Data Import"))
        }
        // ? ADD CUSTOM BUTTONS FOR LEAVE ACTIONS
        frm.add_custom_button(
            __("Approve Leave"),
            function () {
                handle_leave_action(frm, "approve");
            },
            __("Manage Leave Requests")
        );

        frm.add_custom_button(
            __("Reject Leave"),
            function () {
                handle_leave_action(frm, "reject");
            },
            __("Manage Leave Requests")
        );

        frm.set_query('employee','custom_lop_reversal_details', function(doc, cdt, cdn) {
            // Get the list of employee names from the employees child table
            let employee_list = (frm.doc.employees || []).map(row => row.employee).filter(Boolean);
            return {
                filters: {
                    name: ["in", employee_list]
                }
            };
        });

        frm.set_query('employee','custom_adhoc_salary_details', function(doc, cdt, cdn) {
            // Get the list of employee names from the employees child table
            let employee_list = (frm.doc.employees || []).map(row => row.employee).filter(Boolean);
            return {
                filters: {
                    name: ["in", employee_list]
                }
            };
        });

        frm.set_query('employee','custom_lop_summary', function(doc, cdt, cdn) {
            // Get the list of employee names from the employees child table
            let employee_list = (frm.doc.employees || []).map(row => row.employee).filter(Boolean);
            return {
                filters: {
                    name: ["in", employee_list]
                }
            };
        });

        set_lop_month_options_for_all_rows(frm)
        
    },
    before_save: (frm) => {
        frm.set_value('custom_pending_leave_approval', []);
    },
    add_context_buttons: function (frm) {
		if (
			frm.doc.salary_slips_submitted ||
			(frm.doc.__onload && frm.doc.__onload.submitted_ss)
		) {
			frm.events.add_bank_entry_button(frm);
		} else if (frm.doc.salary_slips_created && frm.doc.status !== "Queued") {   
            inform_account_users(frm)
            if (frm.doc.custom_account_users_informed) {                    
                frm.add_custom_button(__("Submit Salary Slip"), function () {
                        submit_salary_slip(frm);
                }).addClass("btn-primary");
            }
		} else if (!frm.doc.salary_slips_created && frm.doc.status === "Failed") {
			frm.add_custom_button(__("Create Salary Slips"), function () {
				frm.trigger("create_salary_slips");
			}).addClass("btn-primary");
		}
    },

    custom_new_joinee_and_exit_refresh: function (frm) {
        frappe.call({
            method: "prompt_hr.py.payroll_entry.refresh_new_joinee_and_exit_tab",
            args: {
                docname: frm.doc.name
            },
            freeze: true,
            callback: function (r) {
                    frappe.msgprint(__("New Joinee and Exit Tab refreshed successfully."));
                    frm.reload_doc()
            }
        });
    },

    custom_leave_and_attendance_refresh: function (frm) {
        frappe.call({
            method: "prompt_hr.py.payroll_entry.refresh_leave_and_attendance_tab",
            args: {
                docname: frm.doc.name
            },
            freeze: true,
            callback: function (r) {
                    frappe.msgprint(__("Leave And Attendance Updated Succesfully"));
                    frm.reload_doc()
            }
        });
    },

    custom_restricted_salary_refresh: function(frm) {
        frappe.call({
            method: "prompt_hr.py.payroll_entry.refresh_restricted_salary_tab",
            args: {
                docname: frm.doc.name
            },
            freeze: true,
            callback: function (r) {
                    frappe.msgprint(__("Restricted Salary Updated Succesfully"));
                    frm.reload_doc()
            }
        });
    },
    add_bank_entry_button: function (frm) {
		frm.call("has_bank_entries").then((r) => {
            if (!r.message.has_bank_entries) {
                send_salary_slip(frm)
				frm.add_custom_button(__("Make Bank Entry"), function () {
					make_bank_entry(frm);
				}).addClass("btn-primary");
			} else if (!r.message.has_bank_entries_for_withheld_salaries) {
				frm.add_custom_button(__("Release Withheld Salaries"), function () {
					make_bank_entry(frm, (for_withheld_salaries = 1));
				}).addClass("btn-primary");
			}
            else {
                // ? Check if any employee still pending bank entry
                const has_remaining = (frm.doc.custom_salary_withholding_details || []).some(
                    row => !row.is_bank_entry_created
                );
                console.log(has_remaining)
                if (has_remaining) {
                    frm.add_custom_button(__("Make Remaining Bank Entry"), function () {
                        make_remaining_bank_entry(frm, (for_withheld_salaries = 1, is_withheld_salary=1));
                    }).addClass("btn-primary");
                }
            }

		});
	},
    custom_new_joinee_and_exit_step_completed: function(frm) {
        disable_fields_for_completed_steps(frm)
    },
    custom_leave_and_attendance_step_completed: function(frm) {
        disable_fields_for_completed_steps(frm)
    },
    custom_adhoc_salary_adjustment_step_completed: function(frm) {
        disable_fields_for_completed_steps(frm)
    },
    custom_restricted_salary_step_completed: function(frm) {
        disable_fields_for_completed_steps(frm)
    },
    custom_salary_withholding_step_completed: function(frm) {
        disable_fields_for_completed_steps(frm)
    },
});

function disable_fields_for_completed_steps(frm) {
    const stepFieldMap = {
        "custom_new_joinee_and_exit_step_completed": [
            "custom_new_joinee_count",
            "custom_exit_employees_count",
            "custom_pending_fnf_details",
            "custom_new_joinee_employees"
        ],
        "custom_leave_and_attendance_step_completed": [
            "custom_pending_leave_approval",
            "custom_lop_summary",
            "custom_lop_reversal_details"
        ],
        "custom_adhoc_salary_adjustment_step_completed": [
            "custom_adhoc_salary_details"
        ],
        "custom_restricted_salary_step_completed": [
            "custom_remaining_payroll_details",
            "custom_remaining_bank_details",
            "custom_is_salary_slip_created"
        ],
        "custom_salary_withholding_step_completed": [
            "custom_salary_withholding_details",
        ]
    };

    for (let [stepField, fields] of Object.entries(stepFieldMap)) {
        const isCompleted = frm.doc[stepField] ? 1 : 0;
        set_fields_read_only(frm, fields, isCompleted);
    }
}

function set_fields_read_only(frm, fields, flag) {
    fields.forEach(field => {
        console.log(fields)
        frm.set_df_property(field, "read_only", flag);
        frm.refresh_field(field);
    });
}

function update_fnf_button(frm) {

    frm.set_df_property("custom_pending_fnf_details", "cannot_add_rows", 1)
    frm.doc.custom_pending_fnf_details.forEach(function(row, index) {
        let button_label = (row.is_fnf_processed || row.fnf_record) ? 'View FnF' : 'Process FnF';

        frm.fields_dict['custom_pending_fnf_details'].grid.update_docfield_property(
            'process_fnf', 'label', button_label, row.name
        );
    });

    frm.fields_dict['custom_pending_fnf_details'].grid.refresh();
}

// ? FUNCTION TO EMPTY BRANCH FIELD IF FORM IS NEW
function empty_branch_field_if_form_is_new(frm) {
    // ? CHECK IF FORM IS NEW
    if (frm.is_new()) {
        // ? EMPTY BRANCH FIELD
        frm.set_value("branch", "");
    }
}

// ? FUNCTION TO HANDLE LEAVE ACTIONS (APPROVE, REJECT)
function handle_leave_action(frm, action) {
    // * Filter selected rows from the Pending Leave Approval child table
    const selected = frm.doc.custom_pending_leave_approval.filter(row => row.__checked);

    // ! Stop if no leave entries are selected
    if (!selected.length) {
        frappe.msgprint("Please select at least one leave entry.");
        return;
    }

    // * Call server-side method to process leave action
    frappe.call({
        method: "prompt_hr.py.payroll_entry.handle_leave_action",
        args: {
            docname: frm.doc.name,
            doctype: frm.doc.doctype,
            action: action,
            leaves: selected.map(row => row.leave_application), // * Extract leave_application IDs
        },
        callback(r) {
            // * If leaves were successfully processed
            if (r.message && r.message.length > 0) {
                frm.reload_doc(); // * Refresh the form to reflect changes

                const actionPastTense = {
                    approve: "approved",
                    reject: "rejected",
                };
                const pastTense = actionPastTense[action] || `${action}ed`;

                // ? Show success message with number of leaves processed
                setTimeout(() => {
                    frappe.msgprint(`Successfully ${pastTense} ${r.message.length} leave(s).`);
                }, 200); // delay before showing the dialog
            } else {
                // ? No leaves to process
                frappe.msgprint("There are no any leaves to " + action + ".");
            }
        }
    });
}

frappe.ui.form.on("LOP Reversal Details", {
    employee: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const child_table_field = "custom_lop_reversal_details";
        const month_field = "lop_month";
        const actual_lop_days_field = "actual_lop_days";

        if (row.employee && frm.doc.start_date) {
            let field = frm.fields_dict[child_table_field].grid.get_docfield(month_field);
            let options = field.options ? field.options.split('\n') : [];
            let default_month = options.length ? options[options.length - 1] : "";

            // Set the default value for lop_month
            frappe.model.set_value(cdt, cdn, month_field, default_month);
        } else {
            // Reset fields if required values are missing
            frappe.model.set_value(cdt, cdn, month_field, "");
            frappe.model.set_value(cdt, cdn, actual_lop_days_field, 0);
            frappe.model.set_value(cdt, cdn, "lop_reversal_days", 0)
        }
    },

    lop_month: function(frm, cdt, cdn) {
        const actual_lop_days_field = "actual_lop_days";
        const row = locals[cdt][cdn];
        console.log(row)
        if(row){
            frappe.call({
                method: "prompt_hr.py.payroll_entry.get_actual_lop_days",
                args: {
                    employee: row.employee,
                    start_date: row.lop_month
                },
                callback: function(r) {
                    frappe.model.set_value(cdt, cdn, actual_lop_days_field, r.message || 0);
                }
            });
        }
    },

    lop_reversal_days: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        let lop_reversal_days = row.lop_reversal_days ? row.lop_reversal_days : 0;
        let actual_lop_days = row.actual_lop_days ? row.actual_lop_days : 0;

        if(lop_reversal_days > actual_lop_days){
            frappe.throw("LOP Reversal Days cannot be greater than Actual LOP Days.");
        }
    }
});

function set_lop_month_options_for_all_rows(frm) {
    const child_table_field = "custom_lop_reversal_details";
    const month_field = "lop_month";

    if (frm.doc.start_date) {
        let start_date = frappe.datetime.str_to_obj(frm.doc.start_date);
        let selected_month_index = start_date.getMonth();
        let selected_year = start_date.getFullYear();
        let options = [];
        for (let i = 0; i < selected_month_index; i++) {
            let month_name = moment().month(i).format('MMMM');
            options.push(`${month_name}-${selected_year}`);
        }
        frm.fields_dict[child_table_field].grid.update_docfield_property(
            month_field, "options", options.join("\n")
        );
    }
}

// ? FUNCTION TO ADD CUSTOM BUTTON FOR GENERATING AND SENDING SALARY SLIP PDF
function send_salary_slip(frm) {

    frappe.call({
        method: "prompt_hr.py.payroll_entry.linked_bank_entry",
        args: {
            payroll_entry_id: frm.doc.name
        },
        callback: function (res) {
            if (res.message) {
                if (res.message.is_all_submitted == 1) {
                    let remaining_employee = [];

                    (frm.doc.custom_salary_withholding_details || []).forEach(row => {
                        if (row.employee && !row.is_salary_slip_release) {
                            remaining_employee.push(row.employee);
                        }
                    });

                    // ? IF NO remaining employee → do NOT show button
                    if (!remaining_employee.length) {
                        return;
                    }
                    frm.add_custom_button(__('Release Salary Slip'), function () {
                        let d = new frappe.ui.Dialog({
                            title: 'Select Employees',
                            fields: [
                                {
                                    label: 'Company Email',
                                    fieldname: 'company_email',
                                    fieldtype: 'Check',                    
                                },
                                {
                                    label: 'Personal Email',
                                    fieldname: 'personal_email',
                                    fieldtype: 'Check',                    
                                },
                                {  
                                    label: 'Salary Release Withheld – Employees',  
                                    fieldname: 'withheld_employee_table',  
                                    fieldtype: 'Table',  
                                    cannot_add_rows: true,  
                                    cannot_delete_rows: true,
                                    hidden: !hide_field,
                                    fields: [  
                                        {  
                                            fieldname: 'employee',  
                                            fieldtype: 'Link',  
                                            options: 'Employee',  
                                            label: 'Employee',  
                                            in_list_view: 1,  
                                            read_only: 1
                                        },  
                                    ]  
                                }
                            ],
                            primary_action_label: 'Send',
                            primary_action(values) {

                                let selected_employee_ids = [];
                                let unselected_employee_ids = [];

                                if (values.withheld_employee_table && values.withheld_employee_table.length > 0) {
                                    values.withheld_employee_table.forEach(row => {
                                        if (row.__checked) {
                                            selected_employee_ids.push(row.employee);
                                        } else {
                                            unselected_employee_ids.push(row.employee);
                                        }
                                    });
                                }

                
                                frappe.call({
                                        method: 'prompt_hr.py.payroll_entry.send_salary_sleep_to_employee',
                                        args: {
                                            payroll_entry_id: frm.doc.name,
                                            email_details: {
                                                company_email: values.company_email,
                                                personal_email: values.personal_email,
                                                selected_employee_ids: selected_employee_ids,
                                                unselected_employee_ids: unselected_employee_ids
                                            }                            
                                        },
                                        callback: function(r) {
                                            frappe.msgprint(__('Salary Slip PDF has been generated and sending to the employees will be sent shortly.'));
                                        }
                                });
                                d.hide();
                            }
                        });
                
                        d.show();
                        // Add default rows dynamically after dialog is shown
                        let employee_table = d.fields_dict.withheld_employee_table.grid;  
                        
                        remaining_employee.forEach(emp => {  
                            // Add to the grid's data array directly  
                            if (!employee_table.df.data) {  
                                employee_table.df.data = [];  
                            }  
                            
                            employee_table.df.data.push({  
                                idx: employee_table.df.data.length + 1,  
                                employee: emp,  
                                __islocal: true  
                            });  
                        });
                        
                        // Refresh the grid to show the new rows  
                        employee_table.refresh();
                        // frappe.call({
                        //     method: 'prompt_hr.py.payroll_entry.send_salary_sleep_to_employee',
                        //     args: {
                        //         payroll_entry_id: frm.doc.name
                        //     },
                        //     callback: function(r) {
                        //         frappe.msgprint(__('Salary Slip PDF has been generated and sending to the employees will be sent shortly.'));
                        //     }
                        // });
                    });
                }
            }
        }
    })
        
    
}

// * FUNCTION TO INFORM ACCOUNT USERS
function inform_account_users(frm) {
    if (!frm.doc.custom_account_users_informed) {
        frm.add_custom_button(__('Inform Account Department'), function () {
            
            frappe.call({
                method: "prompt_hr.py.payroll_entry.send_payroll_entry",
                args: {
                    payroll_entry_id: frm.doc.name,
                    from_date: frm.doc.start_date,
                    to_date: frm.doc.end_date,
                    company: frm.doc.company
                },
                callback: function (res) {
                    frm.reload_doc()
                }
            })
        });
    }
}

// ? FUNCTION TO CHECK EMPTY ARRAY OR OBJECT
function isEmpty(value) {
    // Check for null/undefined
    if (value == null) return true;

    // Check for empty array
    if (Array.isArray(value)) return value.length === 0;

    // Check for empty object
    if (typeof value === 'object')
        return Object.keys(value).length === 0;

    // For other types (string, number, etc) just check falsy
    return !value;
}

// const custom_submit_salary_slip = function (frm) {
// 	frappe.confirm(
// 		__(
// 			"This will submit Salary Slips and create accrual Journal Entry. Do you want to proceed?",
//         ),
// 		function () {
// 			frappe.call({
// 				method: "submit_salary_slips",
// 				args: {},
// 				doc: frm.doc,
// 				freeze: true,
// 				freeze_message: __("Submitting Salary Slips and creating Journal Entry..."),
//             });
//             frappe.call({
//                 method: "prompt_hr.py.payroll_entry.send_payroll_entry",
//                 args: {
//                     payroll_entry_id: frm.doc.name
//                 }
//             })

// 		},
// 		function () {
// 			if (frappe.dom.freeze_count) {
// 				frappe.dom.unfreeze();
// 			}
// 		},
// 	);
// };

let make_remaining_bank_entry = function (frm, for_withheld_salaries = 0) {
    const doc = frm.doc;

    if (!doc.payment_account) {
        frappe.msgprint(__("Payment Account is mandatory"));
        frm.scroll_to_field("payment_account");
        return;
    }

    // ✅ Pending employees (is_bank_entry_created = 0)
    let pending_rows = (frm.doc.custom_salary_withholding_details || [])
        .filter(r => !r.is_bank_entry_created)
        .map(r => ({
            employee: r.employee,
            select: 1
        }));

    if (!pending_rows.length) {
        frappe.msgprint("No pending employees remaining.");
        return;
    }

    // ✅ DEFINE INLINE TABLE COLUMNS
    let table_fields = [
        {
            fieldname: "employee",
            fieldtype: "Data",
            label: "Employee",
            in_list_view: 1,
            read_only: 1
        }
    ];

    // ✅ Create Dialog with REAL Table field
    let d = new frappe.ui.Dialog({
        title: "Select Employees for Bank Entry",
        size: "extra-large",
        fields: [
            {
                label: "Employees",
                fieldname: "employees",
                fieldtype: "Table",
                cannot_add_rows: true,
                cannot_delete_rows: true,
                in_place_edit: false,
                fields: table_fields
            }
        ],
        primary_action_label: "Make Bank Entry",
        primary_action(values) {
            let selected_emps = (values.employees || [])
                .filter(r =>  r.__checked)
                .map(r => r.employee);

            if (!selected_emps.length) {
                frappe.msgprint("Please select at least one employee.");
                return;
            }

            d.hide();

            // ✅ Backend call
            frappe.call({
                method: "run_doc_method",
                args: {
                    method: "make_bank_entry",
                    dt: "Payroll Entry",
                    dn: frm.doc.name,
                    args: {
                        for_withheld_salaries: for_withheld_salaries,
                        is_withheld_salary: 1,
                        selected_employees: selected_emps
                    }
                },
                freeze: true,
                freeze_message: __("Creating Payment Entries..."),
                callback: () => {
                    frappe.set_route("List", "Journal Entry", {
                        "Journal Entry Account.reference_name": frm.doc.name
                    });
                }
            });
        }
    });

    // ✅ SET DATA INTO TABLE
    d.fields_dict.employees.grid.df.data = pending_rows;
    d.fields_dict.employees.grid.refresh();

    d.show();
};

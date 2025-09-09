frappe.ui.form.on("HR Settings", {
    refresh: function (frm) {
        frm.fields_dict.custom_penalization_criteria_table_for_prompt.grid.get_field('value').get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (row.is_sub_department && row.select_doctype == "Department") {
                return {
                    filters : [
                        ["parent_department", "!=", "All Departments"],
                        ["parent_department", "is", "set"]
                    ]
                };
            } else {
                return {};
            }
        };

        frm.fields_dict.custom_penalization_criteria_table_for_indifoss.grid.get_field('value').get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (row.is_sub_department && row.select_doctype == "Department") {
                return {
                    filters : [
                        ["parent_department", "!=", "All Departments"],
                        ["parent_department", "is", "set"]
                    ]
                };
            } else {
                return {};
            }
        };

        if (frm.doc.custom_deduct_leave_penalty_for_indifoss) {
            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_indifoss", "custom_leave_type_for_indifoss", 0, 1);
        }

        hide_add_row_buttom_of_field_table(frm);

        if (frm.doc.custom_deduct_leave_penalty_weekly_for_indifoss) {
            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_weekly_for_indifoss", "custom_leave_type_weekly_for_indifoss", 0, 1);
        }

        if (frm.doc.custom_deduct_leave_penalty_for_prompt) {
            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_prompt", "custom_leave_type_for_prompt", 1, 0);
        }

        if (frm.doc.custom_deduct_leave_penalty_daily_for_prompt) {
            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_daily_for_prompt", "custom_leave_type_daily_for_prompt", 1, 0);
        }
    },
    
    onload: function (frm) { 
        set_employee_fields_in_penalization_criteria(frm);
        set_employee_fields_in_pre_login_questionnaire(frm)
    },  

    custom_deduct_leave_penalty_for_indifoss: function (frm) {
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_indifoss", "custom_leave_type_for_indifoss", 0, 1);
    },

    custom_deduct_leave_penalty_weekly_for_indifoss: function (frm) {
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_weekly_for_indifoss", "custom_leave_type_weekly_for_indifoss", 0, 1);
    },

    custom_deduct_leave_penalty_for_prompt: function (frm) {
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_prompt", "custom_leave_type_for_prompt", 1, 0);
    },

    custom_deduct_leave_penalty_daily_for_prompt: function (frm) { 
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_daily_for_prompt", "custom_leave_type_daily_for_prompt", 1, 0);
    },

    // Button for Indifoss child table
    custom_set_allowed_fields_for_indifoss: function(frm) {
        openSetAllowedFieldsDialog(frm, 'custom_employee_changes_allowed_fields_for_indifoss', 'Indifoss');
    },

    // Button for Prompt child table  
    custom_set_allowed_fields_for_prompt: function(frm) {
        openSetAllowedFieldsDialog(frm, 'custom_employee_changes_allowed_fields_for_prompt', 'Prompt');
    },

    custom_send_mails_for_prompt: function (frm) { 
        if (frm.doc.custom_attendance_issue_mail_check_date_for_prompt) {
            frappe.call({
                method: "prompt_hr.scheduler_methods.send_attendance_issue_mail_check",
                args: {
                    attendance_check_date: frm.doc.custom_attendance_issue_mail_check_date_for_prompt
                }
            })
        }
    }

});

function apply_filter_for_leave_type(frm, fieldname, leave_type_fieldname, prompt_comp, indifoss) {
    let args = {};
    if (indifoss) args.indifoss = 1;
    if (prompt_comp) args.prompt = 1;

    frappe.call({
        method: "prompt_hr.py.utils.fetch_company_name",
        args: args,
        callback: function (res) {
            if (res.message) {
                if (!res.message.error && res.message.company_id) {
                    if (frm.doc[fieldname] == "Deduct leave without pay") {
                        frm.set_query(leave_type_fieldname, function () {
                            return {
                                filters: {
                                    "custom_company": res.message.company_id,
                                    "is_lwp": 1
                                }
                            };
                        });
                    }
                    if (frm.doc[fieldname] == "Deduct earned leave") {
                        frm.set_query(leave_type_fieldname, function () {
                            return {
                                filters: {
                                    "custom_company": res.message.company_id,
                                    "custom_is_earned_leave_allocation": 1
                                }
                            };
                        });
                    }
                } else {
                    frappe.throw(res.message.message);
                }
            }
        }
    });
}


frappe.ui.form.on("Penalization Criteria", {
    custom_penalization_criteria_table_for_prompt_add: async function (frm, cdt, cdn) {
        let options = await getEmployeeFields();

        if (options.length) {
        
            frm.fields_dict["custom_penalization_criteria_table_for_prompt"].grid.update_docfield_property(
                "employee_field",
                "options",
                options.map(o => o.label)
            );
        }
    },
    employee_field: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (frm.employee_field_map && row.employee_field) {
            row.employee_field_name = frm.employee_field_map[row.employee_field];
            frm.refresh_field("custom_penalization_criteria_table_for_prompt");
        }
    }
})

frappe.ui.form.on("Pre Login Questionnaire", {
    custom_pre_login_questionnaire_add: async function (frm, cdt, cdn) {
        let options = await getEmployeeFields();

        if (options.length) {
            frm.fields_dict["custom_pre_login_questionnaire"].grid.update_docfield_property(
                "field_name",
                "options",
                options.map(o => o.label)
            );
        }
    },
    field_name: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (frm.employee_field_map && row.field_name) {
            row.employee_field_name = frm.employee_field_map[row.field_name];
        }
        if (frm.employee_field_type_map && row.field_name) {
            row.field_type = frm.employee_field_type_map[row.field_name];
        }
        frm.refresh_field("custom_pre_login_questionnaire");
    }
})
async function set_employee_fields_in_penalization_criteria(frm) {
    
    let options = await getEmployeeFields();
    if (options.length) {
        frm.fields_dict["custom_penalization_criteria_table_for_prompt"].grid.update_docfield_property(
            "employee_field",
            "options",
            options.map(o => o.label)
        );

        frm.employee_field_map = {};
        options.forEach(o => {
            frm.employee_field_map[o.label] = o.fieldname;
        });
        frm.refresh_field("custom_penalization_criteria_table_for_prompt");

    }
}

async function set_employee_fields_in_pre_login_questionnaire(frm) {
    
    let options = await getEmployeeFields();
    let type_options = await getEmployeeFieldTypes();
    if (options.length) {
        frm.fields_dict["custom_pre_login_questionnaire"].grid.update_docfield_property(
            "field_name",
            "options",
            options.map(o => o.label)
        );

        frm.employee_field_map = {};
        frm.employee_field_type_map = {};
        options.forEach(o => {
            frm.employee_field_map[o.label] = o.fieldname;
        });
        type_options.forEach(o => {
            frm.employee_field_type_map[o.label] = o.fieldtype;
        });
        frm.refresh_field("custom_pre_login_questionnaire");

    }
}


// Function to fetch Employee DocType fields
async function getEmployeeFields() {
    try {
        const response = await frappe.call({
            method: "prompt_hr.py.employee.get_employee_doctype_fields"
        });

        return response.message.map(field => ({
            label: field.label,
            value: field.label,
            fieldname: field.fieldname,
        }));
    } catch (error) {
        console.error("Error fetching Employee fields:", error);
        frappe.msgprint(__('Could not load Employee fields.'));
        return [];
    }
}

// Function to fetch Employee DocType fields
async function getEmployeeFieldTypes() {
    try {
        const response = await frappe.call({
            method: "prompt_hr.py.employee.get_employee_doctype_fields"
        });

        return response.message.map(field => ({
            label: field.label,
            value: field.label,
            fieldtype: field.fieldtype,
        }));
    } catch (error) {
        console.error("Error fetching Employee fields:", error);
        frappe.msgprint(__('Could not load Employee fields.'));
        return [];
    }
}

// Function to open the dialog for setting allowed fields
async function openSetAllowedFieldsDialog(frm, child_table_fieldname, company_type) {
    const employee_fields = await getEmployeeFields();
    
    if (!employee_fields.length) {
        frappe.msgprint(__('No Employee fields found.'));
        return;
    }

    const dialog = new frappe.ui.Dialog({
        title: __('Set Allowed Fields for {0}', [company_type]),
        fields: [
            {
                label: __('Employee Field'),
                fieldname: 'field_label',
                fieldtype: 'Autocomplete',
                options: employee_fields,
                reqd: 1,
                description: __('Select the employee field to allow for changes')
            },
            {
                label: __('Permission Required'),
                fieldname: 'permission_required',
                fieldtype: 'Check',
                default: 1,
                description: __('Check if approval is required for this field change')
            }
        ],
        size: 'small',
        primary_action_label: __('Add Field'),
        primary_action(values) {
            addFieldToChildTable(frm, child_table_fieldname, company_type, values, dialog);
        }
    });

    dialog.show();
}

// Function to add selected field to respective child table
function addFieldToChildTable(frm, child_table_fieldname, company_type, values, dialog) {
    try {
        console.log("VALUES",values)
        // Check if field already exists in child table
        const existing_field = frm.doc[child_table_fieldname]?.find(
            row => row.field_label === values.field_label
        );

        if (existing_field) {
            frappe.msgprint({
                title: __('Field Already Exists'),
                message: __('This field is already added to the {0} allowed fields list.', [company_type]),
                indicator: 'orange'
            });
            return;
        }

        // Add new row to respective child table
        const child_row = frappe.model.add_child(
            frm.doc, 
            'Employee Changes Allowed Fields', 
            child_table_fieldname
        );

        // Set values
        child_row.field_label = values.field_label;
        child_row.permission_required = values.permission_required ? 1 : 0;

        // Refresh the respective child table
        frm.refresh_field(child_table_fieldname);

        // Show success message
        frappe.msgprint({
            title: __('Field Added'),
            message: __('Field "{0}" has been added to {1} allowed fields list.', [values.field_label, company_type]),
            indicator: 'green'
        });

        // Close dialog
        dialog.hide();

        // Mark document as dirty to show save indicator
        frm.dirty();

    } catch (error) {
        console.error('Error adding field to child table:', error);
        frappe.msgprint({
            title: __('Error'),
            message: __('An error occurred while adding the field. Please try again.'),
            indicator: 'red'
        });
    }
}

function hide_add_row_buttom_of_field_table(frm) {
    frm.set_df_property("custom_employee_changes_allowed_fields_for_indifoss", "cannot_add_rows", 1);
    frm.set_df_property("custom_employee_changes_allowed_fields_for_prompt", "cannot_add_rows", 1);
}

frappe.ui.form.on('Penalization Criteria', {
    is_sub_department: function(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'value', null);
        frm.fields_dict.custom_penalization_criteria_table_for_prompt.grid.refresh_row(cdn);
        frm.fields_dict.custom_penalization_criteria_table_for_indifoss.grid.refresh_row(cdn);
    }
});

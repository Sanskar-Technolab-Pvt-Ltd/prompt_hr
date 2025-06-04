frappe.ui.form.on("HR Settings", {
    refresh: function (frm) {

        frm.fields_dict.custom_penalization_criteria_table_for_prompt.grid.get_field('value').get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            if (row.is_sub_department && row.select_doctype == "Department") {
                return {
                    filters: {
                        parent_department: ['!=', "All Departments"]
                    }
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

// Function to fetch Employee DocType fields
async function getEmployeeFields() {
    try {
        const response = await frappe.call({
            method: "prompt_hr.py.employee.get_employee_doctype_fields"
        });

        return response.message.map(field => ({
            label: field.label,
            value: field.label
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
    }
});

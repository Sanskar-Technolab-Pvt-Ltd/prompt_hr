function set_text_field_height() {
    const fields = [
        'first_name', 'middle_name', 'last_name', 'employee_name', 'salutation',
        'custom_reason_for_suspension', 'custom_agency_name', 'custom_agency_email',
        'custom_verification_remarks', 'cell_number', 'personal_email',
        'prefered_contact_email', 'custom_work_mobile_no', 'custom_preferred_mobile_no',
        'company_email', 'prefered_email', 'custom_current_address_line_1',
        'custom_current_address_line_2', 'custom_current_address_line_3',
        'custom_permanent_address_line_1', 'custom_permanent_address_line_2',
        'custom_permanent_address_line_3', 'person_to_be_contacted',
        'emergency_phone_number', 'relation', 'bank_name', 'bank_ac_no',
        'bank_cb', 'ifsc_code', 'micr_code', 'iban', 'passport_number',
        'valid_upto', 'place_of_issue', 'health_insurance_no', 'new_workplace',
        'old_parent'
    ];

    fields.forEach(field => {
        $(`textarea[data-fieldname='${field}']`).css('height', '40');
    });

}
frappe.ui.form.on("Employee", {
    refresh: function (frm) {
        set_text_field_height();

        addEmployeeDetailsChangesButton(frm);

        // ? EMPLOYEE RESIGNATION BUTTON AND FUNCTIONALITY
        createEmployeeResignationButton(frm);
        if (!frm.doc.department) {
            frm.set_query("custom_subdepartment", () => {
                return {
                    filters: {
                        name: ["is", "not set"]
                    }
                };
            });
        }
        if (frm.doc.department) {
            frappe.db.get_value("Department", frm.doc.department || "", "is_group")
                .then((r) => {
                    if (r && r.message && r.message.is_group) {
                        frm.set_query("custom_subdepartment", () => {
                            return {
                                filters: {
                                    parent_department: frm.doc.department,
                                    company: frm.doc.company,
                                }
                            };
                        });
                    }
                    else {
                        frm.set_query("custom_subdepartment", () => {
                            return {
                                filters: {
                                    name: ["is", "not set"]
                                }
                            };
                        });
                    }
                })
                .catch((err) => {
                    console.error("Error fetching Department Type:", err);
                });
        }
        frm.add_custom_button(__("Release Service Level Agreement"), function () {
            frappe.dom.freeze(__('Releasing Letter...'));
            frappe.call({
                method: "prompt_hr.py.employee.send_service_agreement",
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                    }
                },
                always: function () {
                    frappe.dom.unfreeze();
                }
            });
        }, __("Release Letters"));

        frm.add_custom_button(__("Release Confirmation Letter"), function () {
            frappe.dom.freeze(__('Releasing Letter...'));
            frappe.call({
                method: "prompt_hr.py.employee.send_confirmation_letter",
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                    }
                },
                always: function () {
                    frappe.dom.unfreeze();
                }
            });
        }, __("Release Letters"));
        frm.add_custom_button(__("Release Probation Extension Letter"), function () {
            frappe.dom.freeze(__('Releasing Letter...'));
            frappe.call({
                method: "prompt_hr.py.employee.send_probation_extension_letter",
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                    }
                },
                always: function () {
                    frappe.dom.unfreeze();
                }
            });
        }, __("Release Letters"));

        if (frm.doc.custom_state) {
            frm.set_query("custom_festival_holiday_list", () => {
                return {
                    filters: {
                        state: frm.doc.custom_state
                    }
                };
            });
        }
    },
    department: function (frm) {
        console.log("Employee Form Refreshed");
        if (frm.doc.department) {
            frappe.db.get_value("Department", frm.doc.department || "", "is_group")
                .then((r) => {
                    if (r && r.message && r.message.is_group) {
                        frm.set_query("custom_subdepartment", () => {
                            return {
                                filters: {
                                    parent_department: frm.doc.department,
                                    company: frm.doc.company,
                                }
                            };
                        });
                    }
                    else {
                        frm.set_query("custom_subdepartment", () => {
                            return {
                                filters: {
                                    name: ["is", "not set"]
                                }
                            };
                        });
                    }
                })
                .catch((err) => {
                    console.error("Error fetching Department Type:", err);
                });
        }
        else {
            frm.set_query("custom_subdepartment", () => {
                return {
                    filters: {
                        name: ["is", "not set"]
                    }
                };
            });
        }
    },
    custom_current_address_is_permanent_address: function (frm) {
        if (frm.doc.custom_current_address_is_permanent_address) {
            console.log(frm.doc.custom_current_address_is_permanent_address)
            frm.set_value("custom_permanent_address_line_1", frm.doc.custom_current_address_line_1);
            frm.set_value("custom_permanent_address_line_2", frm.doc.custom_current_address_line_2);
            frm.set_value("custom_permanent_address_line_3", frm.doc.custom_current_address_line_3);
            frm.set_value("custom_permanent_city", frm.doc.custom_current_city);
            frm.set_value("custom_permanent_state", frm.doc.custom_current_state);

            frm.set_value("custom_permanent_zip_code", frm.doc.custom_current_zip_code)
            frm.set_value("custom_permanent_district", frm.doc.custom_current_district)
            frm.set_value("custom_permanent_sub_district", frm.doc.custom_current_sub_district)
            frm.set_value("custom_permanent_country", frm.doc.custom_current_country)

        }
        else {
            frm.set_value("custom_permanent_address_line_1", "");
            frm.set_value("custom_permanent_address_line_2", "");
            frm.set_value("custom_permanent_address_line_3", "");
            frm.set_value("custom_permanent_city", "");
            frm.set_value("custom_permanent_state", "");
            frm.set_value("custom_permanent_zip_code", "")
            frm.set_value("custom_permanent_district", "")
            frm.set_value("custom_permanent_sub_district", "")
            frm.set_value("custom_permanent_country", "")
        }
    },


    // refresh: function (frm){
    //     prompt_probation_period = frappe.db.get_single_value("HR Settings","custom_probation_period_for_prompt")
    //     indifoss_probation_period = frappe.db.get_single_value("HR Settings","custom_probation_period_for_indifoss")
    //     if (frm.doc.company == "Prompt Equipments Pvt Ltd"){

    //     }
    // }

});

// ? FUNCTION TO CREATE EMPLOYEE RESIGNATION BUTTON AND HANDLE RESIGNATION PROCESS
function createEmployeeResignationButton(frm) {
    frm.add_custom_button(__("Raise Resignation"), function () {
        console.log(frm.doc.notice_number_of_days);

        // ? FETCH RESIGNATION QUESTIONS FROM BACKEND
        frappe.call({
            method: "prompt_hr.py.employee.get_raise_resignation_questions",
            args: {"company": frm.doc.company},
            callback: function (res) {
                if (res.message && res.message.length > 0) {
                    const questions = res.message;

                    // ? BUILD DYNAMIC DIALOG FIELDS BASED ON QUESTIONS
                    const fields = questions.map(q => ({
                        label: q.question_detail || q.question,
                        fieldname: q.question,
                        fieldtype: "Data",
                        reqd: true
                    }));

                    // ? CREATE RESIGNATION DIALOG
                    const dialog = new frappe.ui.Dialog({
                        title: __('Resignation Details'),
                        fields: fields,
                        primary_action_label: __('Submit'),

                        // ? ON SUBMIT, COLLECT RESPONSES AND CALL BACKEND
                        primary_action(values) {
                            frappe.dom.freeze(__('Creating Resignation...'));

                            // ? PREPARE USER RESPONSES
                            const answers = questions.map(q => ({
                                question_name: q.question,
                                question: q.question_detail || q.question,
                                answer: values[q.question]
                            }));

                            // ? CREATE RESIGNATION RECORD IN BACKEND
                            frappe.call({
                                method: "prompt_hr.py.employee.create_resignation_quiz_submission",
                                args: {
                                    employee: frm.doc.name,
                                    user_response: answers,
                                    notice_number_of_days: frm.doc.notice_number_of_days,
                                },
                                callback: function (r) {
                                    console.log(answers);
                                    if (r.message) {
                                        frappe.msgprint(r.message);
                                        dialog.hide();
                                    }
                                },
                                always: function () {
                                    frappe.dom.unfreeze();
                                }
                            });
                        }
                    });

                    // ? DISPLAY THE DIALOG
                    dialog.show();

                } else {
                    frappe.msgprint(__('No resignation questions found.'));
                }
            }
        });
    });
}

// ? FUNCTION TO ADD A CUSTOM BUTTON ON THE EMPLOYEE FORM
function addEmployeeDetailsChangesButton(frm) {
    // ? ADD BUTTON TO FORM HEADER
    frm.add_custom_button("Apply for Changes", () => {
        loadDialogBox(frm);
    });
}

// ? FUNCTION TO FETCH LIST OF CHANGEABLE EMPLOYEE FIELDS FROM BACKEND
async function getEmployeeChangableFields(frm) {
    try {
        // ? CALL BACKEND METHOD TO GET FIELD METADATA
        const response = await frappe.call({
            method: "prompt_hr.py.employee.get_employee_changable_fields",
            args: { emp_id: frm.doc.name }
        });

        // ? RETURN FIELD LIST OR EMPTY ARRAY
        return response.message || [];
    } catch (err) {
        // ? LOG ERROR AND RETURN EMPTY LIST
        console.error("ERROR FETCHING EMPLOYEE CHANGEABLE FIELDS:", err);
        return [];
    }
}

// ? FUNCTION TO LOAD DIALOG BOX FOR EMPLOYEE CHANGE REQUEST
async function loadDialogBox(frm) {
    let employee_fields = [];
    let field_meta = [];

    try {
        // ? FETCH FIELD METADATA FROM BACKEND
        field_meta = await getEmployeeChangableFields(frm);

        // ? IF NO FIELDS FOUND, SHOW ERROR AND EXIT
        if (!field_meta.length) {
            frappe.msgprint(__("There are currently no personal details you're allowed to update. Please contact HR if you believe this is an error."));
            return;
        }

        // ? PREPARE AUTOCOMPLETE OPTIONS FROM LABELS
        employee_fields = field_meta.map(f => ({
            label: f.label,
            value: f.label 
        }));

    } catch (error) {
        frappe.msgprint(__('Could not load changeable fields.'));
        return;
    }

    // ? INITIALIZE DIALOG WITH STATIC FIELD SETUP
    const dialog = new frappe.ui.Dialog({
        title: 'Select Employee Field',
        fields: [
            {
                label: 'Employee Field',
                fieldname: 'employee_field',
                fieldtype: 'Autocomplete',
                options: employee_fields,
                reqd: 1
            },
            {
                label: 'Old Value',
                fieldname: 'old_value',
                fieldtype: 'Data',
                read_only: 1
            },
            {
                label: 'New Value',
                fieldname: 'new_value',
                fieldtype: 'Data' // ? DYNAMICALLY REPLACED BASED ON FIELD TYPE
            }
        ],
        primary_action_label: 'Submit',

        // ? ON SUBMIT, CONVERT LABEL TO FIELDNAME AND SEND REQUEST
        primary_action(values) {
            const selected_field = field_meta.find(f => f.label === values.employee_field);
            if (!selected_field) {
                frappe.msgprint(__('Selected field metadata not found.'));
                return;
            }

            handleFieldChangeRequest(frm, {
                employee_field: selected_field.fieldname,
                field_label: selected_field.label, // ? ADD FIELD LABEL
                old_value: values.old_value,
                new_value: values.new_value
            }, dialog);
        }
    });

    // ? DISPLAY THE DIALOG
    dialog.show();

    // ? HANDLE FIELD CHANGE (ON SELECT FROM AUTOCOMPLETE)
    dialog.fields_dict.employee_field.df.onchange = () => {
        const selected_label = dialog.get_value('employee_field');

        // ? FIND METADATA USING SELECTED LABEL
        const selected_meta = field_meta.find(f => f.label === selected_label);
        if (!selected_meta) return;

        // ? SET OLD VALUE FROM CURRENT EMPLOYEE DOC
        const old_val = frm.doc[selected_meta.fieldname] || '';
        dialog.set_value('old_value', old_val);

        // ? GET FIELD DEFINITION FROM CURRENT FORM
        const field_df = cur_frm.fields_dict[selected_meta.fieldname]?.df;

        // ? PREPARE CONFIG FOR NEW VALUE FIELD BASED ON FIELD TYPE
        const new_field_config = {
            label: 'New Value',
            fieldname: 'new_value',
            fieldtype: field_df?.fieldtype || 'Data',
            options: field_df?.options || undefined
        };

        // ? ADD OR UPDATE THE FIELD IN THE DIALOG
        dialog.fields_dict.new_value.df = new_field_config;
        dialog.refresh();


        // ? REPLACE EXISTING FIELD WITH CORRECT TYPE
        dialog.replace_field('new_value', new_field_config);
    };
}

// ? FUNCTION TO HANDLE FIELD CHANGE REQUEST SUBMISSION
function handleFieldChangeRequest(frm, values, dialog) {
    // ? SHOW LOADING INDICATOR
    frappe.dom.freeze(__('Submitting change request...'));

    // ? MAKE BACKEND CALL TO CREATE CHANGE REQUEST
    frappe.call({
        method: "prompt_hr.py.employee.create_employee_details_change_request",
        args: {
            employee_id: frm.doc.name,
            field_name: values.employee_field,
            field_label: values.field_label, // ? ADD FIELD LABEL TO API CALL
            old_value: values.old_value,
            new_value: values.new_value
        },

        // ? HANDLE RESPONSE FROM SERVER
        callback: function (r) {
            frappe.dom.unfreeze();

            const status = r.message?.status;
            const msg = r.message?.message || __('Failed to create change request.');

            // ? DISPLAY APPROPRIATE SUCCESS/ERROR MESSAGE
            frappe.msgprint({
                title: status === 1 ? __('Request Submitted') : __('Request Failed'),
                message: msg + '<br><i>Refreshing in 3 seconds...</i>',
                indicator: status === 1 ? 'green' : 'red'
            });

            // ? REFRESH PAGE AFTER SHORT DELAY
            setTimeout(() => {
                if (dialog) dialog.hide();

                window.location.reload();
            }, 3000);
        },

        // ? HANDLE SERVER-SIDE ERRORS
        error: function (err) {
            frappe.dom.unfreeze();
            frappe.msgprint({
                title: __('Error'),
                message: __('Something went wrong while creating the request.') + '<br><i>Refreshing in 3 seconds...</i>',
                indicator: 'red'
            });

            console.error("CHANGE REQUEST ERROR:", err);

            setTimeout(() => {
                if (dialog) dialog.hide();
                window.location.reload();
            }, 3000);
        }
    });
}
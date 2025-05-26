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
    refresh: function(frm) {
        set_text_field_height();


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
        if (frm.doc.department){
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
                    else{
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
    department: function(frm) {
        console.log("Employee Form Refreshed");
        if (frm.doc.department){
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
                    else{
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
        else{
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
            frm.set_value("custom_permanent_zip_code",frm.doc.custom_current_zip_code)
            frm.set_value("custom_permanent_district",frm.doc.custom_current_district)
            frm.set_value("custom_permanent_sub_district",frm.doc.custom_current_sub_district)
            frm.set_value("custom_permanent_country",frm.doc.custom_current_country)
        }
        else{
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

// ? FUNCTION TO CREATE EMPLOYEE RESIGNATION BUTTON AND FUNCTIONALITY
function createEmployeeResignationButton(frm) {
    frm.add_custom_button(__("Raise Resignation"), function () {
        console.log(frm.doc.notice_number_of_days)
        // ? FETCH QUESTIONS FROM PYTHON BACKEND
        frappe.call({
            method: "prompt_hr.py.employee.get_raise_resignation_questions",
            callback: function (res) {
                if (res.message && res.message.length > 0) {
                    const questions = res.message;

                    // ? BUILD DYNAMIC FIELDS USING QUESTION DATA
                    const fields = questions.map(q => ({
                        label: q.question_detail || q.question,
                        fieldname: q.question,
                        fieldtype: "Data",
                        reqd: true
                    }));

                    // ? CREATE THE DIALOG
                    const dialog = new frappe.ui.Dialog({
                        title: __('Resignation Details'),
                        fields: fields,
                        primary_action_label: __('Submit'),
                        primary_action(values) {
                            frappe.dom.freeze(__('Creating Resignation...'));

                            // ? PREPARE ANSWERS AS A LIST OF {question, answer}
                            const answers = questions.map(q => ({
                                question_name: q.question,
                                question: q.question_detail || q.question,
                                answer: values[q.question]
                            }));

                            // ? CALL BACKEND METHOD TO CREATE RESIGNATION
                            frappe.call({
                                method: "prompt_hr.py.employee.create_resignation_quiz_submission",
                                args: {
                                    employee: frm.doc.name,
                                    user_response: answers,
                                    notice_number_of_days: frm.doc.notice_number_of_days,
                                },
                                callback: function (r) {
                                    console.log(answers)
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

                    dialog.show();

                } else {
                    frappe.msgprint(__('No resignation questions found.'));
                }
            }
        });
    });
}


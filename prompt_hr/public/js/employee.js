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
        'old_parent', "custom_home_phone", "custom_father_name", "custom_mother_name", "custom_spouse_name", "custom_children_names", "custom_name_as_per_bank_account", "custom_source_of_hire", "custom_employee_referral_name", "custom_mrf_number"
    ];

    fields.forEach(field => {
        $(`textarea[data-fieldname='${field}']`).css('height', '40');
    });

}
frappe.ui.form.on("Employee", {

    onload(frm) {

        if (frappe.route_options && frappe.route_options.show_update_message) {
            setTimeout(() => {
                frappe.msgprint("Please update Notice Period, Leave Policy, and Leave Policy Change Date.");
            }, 1000);

            frappe.route_options = {};
        }
    },

    after_save(frm) {
        set_field_visibility(frm)
    },

    refresh: function (frm) {
        // ? SET AUTOCOMPLETE OPTIONS FOR CURRENT AND PERMANENT STATE
        set_state_options(frm, "custom_current_state", "custom_current_country");
        set_state_options(frm, "custom_permanent_state", "custom_permanent_country");


        // ? SET FILTERS FOR CURRENT AND PERMANENT DISTRICT, SUB DISTRICT kk
        handle_location_change(frm, "custom_current")
        handle_location_change(frm, "custom_permanent")

        set_text_field_height();
        set_field_visibility(frm)
        addEmployeeDetailsChangesButton(frm);
        // ? ADD APPROVAL BUTTON FOR LOGIN QUESTIONNAIRE TO EMPLOYEE
        if (!frm.is_new() && !frm.doc.custom_employees_all_response_approve) {
            addApproveEmployeeDetailsButton(frm);
        }
        add_profile_completion_percentage(frm)

        frm.set_query("custom_leave_policy", () => {
            return {
                query: "prompt_hr.overrides.leave_policy_assignment_override.filter_leave_policy_for_display",
                filters: {
                    gender: frm.doc.gender,
                    company: frm.doc.company,
                },
            };
        });
        // ? EMPLOYEE RESIGNATION BUTTON AND FUNCTIONALITY
        createEmployeeActionButtons(frm);
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
        // ? ONLY VISIBLE TO HR MANAGER, HR USER AND SYSTEM MANAGER
        if (frappe.user_roles.includes("S - HR Director (Global Admin)") || frappe.user_roles.includes("System Manager")) {
            frm.add_custom_button("Release Service Level Agreement", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Releasing Letter...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Service Agreement - Prompt"},
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // No approval → Show dialog directly
                        if (!record) {
                            show_service_letter_send_dialog(frm, already_sent);
                            return;
                        }

                        // Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Service Level Agreement is under approval."));
                            return;
                        }

                        // Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Service Letter",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Service Level Agreement") {
                                    show_service_letter_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_service_letter_to_cc_dialog(frm);
                                }

                            },
                            "Service Level Agreement Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));

            frm.add_custom_button("Release Confirmation Letter", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Checking approval...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Confirmation Letter - Prompt"},
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // 1️⃣ No approval → Show dialog directly
                        if (!record) {
                            show_confirmation_send_dialog(frm, already_sent);
                            return;
                        }

                        // 2️⃣ Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Confirmation Letter is under approval."));
                            return;
                        }

                        // 3️⃣ Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Confirmation Letter Directly",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Confirmation Letter Directly") {
                                    show_confirmation_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_confirmation_to_cc_dialog(frm);
                                }

                            },
                            "Confirmation Letter Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));

            frm.add_custom_button("Release Probation Extension Letter", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Release Probation Extension Letter...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Probation Extension Letter - Prompt"},
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // 1No approval → Show dialog directly
                        if (!record) {
                            show_probation_letter_send_dialog(frm, already_sent);
                            return;
                        }

                        // Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Release Probation Extension Letter is under approval."));
                            return;
                        }

                        // Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Release Probation Extension",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Probation Extension Letter") {
                                    show_probation_letter_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_probation_letter_to_cc_dialog(frm);
                                }

                            },
                            "Probation Letter Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));

            // 
            frm.add_custom_button("Release Non-Disclosure Agreement", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Non-Disclosure Agreement...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Non-Disclosure Agreement - Prompt" },
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // No approval → Show dialog directly
                        if (!record) {
                            show_non_disclosure_send_dialog(frm, already_sent);
                            return;
                        }

                        // Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Non-Disclosure Agreement is under approval."));
                            return;
                        }

                        // Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Non-Disclosure Agreement",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Non-Disclosure Agreement") {
                                    show_non_disclosure_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_non_disclosure_to_cc_dialog(frm);
                                }

                            },
                            "Non-Disclosure Agreement Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));

            //  
            frm.add_custom_button("Release Consultant Service Completion Letter", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Consultant Service Completion Letter...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Consultant Service Completion Letter - Prompt" },
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // No approval → Show dialog directly
                        if (!record) {
                            show_consultant_service_letter_completion_send_dialog(frm, already_sent);
                            return;
                        }

                        // Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Consultant Service Completion Letter is under approval."));
                            return;
                        }

                        // Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Consultant Service Completion Letter",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Consultant Service Completion Letter") {
                                    show_consultant_service_letter_completion_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_consultant_service_to_cc_dialog(frm);
                                }

                            },
                            "Consultant Service Completion Letter Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));

            //
            frm.add_custom_button("Release Consultant Contract Letter", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Consultant Contract Letter...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Consultant Contract Letter - Prompt" },
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // No approval → Show dialog directly
                        if (!record) {
                            show_consultant_contract_letter_send_dialog(frm, already_sent);
                            return;
                        }

                        // Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Consultant Contract Letter is under approval."));
                            return;
                        }

                        // Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Consultant Contract Letter",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Consultant Contract Letter") {
                                    show_consultant_contract_letter_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_consultant_contract_letter_to_cc_dialog(frm);
                                }

                            },
                            "Consultant Contract Letter Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));

            //
            frm.add_custom_button("Relieving Experience Letter", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Relieving-Experience Letter...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Relieving-Experience Letter - Prompt"},
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // No approval → Show dialog directly
                        if (!record) {
                            show_relieving_experience_letter_send_dialog(frm, already_sent);
                            return;
                        }

                        // Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Relieving Experience Letter is under approval."));
                            return;
                        }

                        // Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Relieving Experience Letter",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Relieving Experience Letter") {
                                    show_relieving_experience_letter_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_relieving_letter_to_cc_dialog(frm);
                                }

                            },
                            "Relieving Experience Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));

            //
            frm.add_custom_button("Promotion Letter", function () {

                const already_sent = frm.doc.custom_confirmation_letter_sent === 1;

                frappe.dom.freeze("Promotion Letter...");

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "Employee Letter Approval",
                        fields: ["name", "workflow_state"],
                        filters: { record_link: frm.doc.name, letter: "Promotion Letter - Prompt"},
                        order_by: "creation desc",
                        limit_page_length: 1
                    },
                    callback(r) {

                        frappe.dom.unfreeze();

                        const record = r.message?.[0];

                        // No approval → Show dialog directly
                        if (!record) {
                            show_promotion_letter_send_dialog(frm, already_sent);
                            return;
                        }

                        // Approval exists but not final → Block
                        if (record.workflow_state !== "Final Approval") {
                            frappe.msgprint(__("Promotion Letter is under approval."));
                            return;
                        }

                        // Final Approval → Ask how to send
                        frappe.prompt(
                            [
                                {
                                    fieldname: "action",
                                    fieldtype: "Select",
                                    label: "Choose Action",
                                    reqd: 1,
                                    options: [
                                        "Resend Promotion Letter",
                                        "Send with TO/CC"
                                    ]
                                }
                            ],
                            (values) => {

                                if (values.action === "Resend Promotion Letter") {
                                    show_promotion_letter_send_dialog(frm, already_sent);
                                }

                                if (values.action === "Send with TO/CC") {
                                    show_promotion_letter_to_cc_dialog(frm);
                                }

                            },
                            "Promotion Letter Approved",
                            "Continue"
                        );
                    }
                });

            }, __("Release Letters"));
        }

        // ? AUTO-CLICK "Raise Resignation" BUTTON IF URL PARAMETER IS PRESENT
        raise_resignation_button_auto_click_from_url(frm);
        disable_employee_fields_for_left_employee(frm);

        // ? Update notice_period_days in Exit Approval Process
        calculate_notice_days_employee(frm);
    },
    custom_current_country(frm) {
        set_state_options(frm, "custom_current_state", "custom_current_country");
        handle_location_change(frm, "custom_current")

    },
    custom_permanent_country(frm) {
        set_state_options(frm, "custom_permanent_state", "custom_permanent_country");
        handle_location_change(frm, "custom_permanent")

    },
    custom_current_district(frm) {
        if (frm.doc.custom_current_country == "India") {
            set_city_autocomplete_options(frm, "custom_current_city", { state: frm.doc.custom_current_state, district: frm.doc.custom_current_district });
            handle_location_change(frm, "custom_current")
        }
    },
    custom_permanent_district(frm) {
        if (frm.doc.custom_current_country == "India") {
            set_city_autocomplete_options(frm, "custom_permanent_city", { state: frm.doc.custom_permanent_state, district: frm.doc.custom_permanent_district });
            handle_location_change(frm, "custom_permanent")

        }
    },
    custom_current_state(frm) {
        if (frm.doc.custom_current_country == "India") {
            set_city_autocomplete_options(frm, "custom_current_city", { state: frm.doc.custom_current_state });
            handle_location_change(frm, "custom_current")

        }
    },
    custom_permanent_state(frm) {
        if (frm.doc.custom_permanent_country == "India") {
            set_city_autocomplete_options(frm, "custom_permanent_city", { state: frm.doc.custom_permanent_state });
            handle_location_change(frm, "custom_permanent")
        }
    },

    custom_current_sub_district(frm) {
        if (frm.doc.custom_current_country == "India") {
            set_city_autocomplete_options(frm, "custom_current_city", { state: frm.doc.custom_current_state, district: frm.doc.custom_current_district, sub_district: frm.doc.custom_current_sub_district });
            handle_location_change(frm, "custom_current")

        }
    },

    custom_permanent_sub_district(frm) {
        if (frm.doc.custom_permanent_country == "India") {
            set_city_autocomplete_options(frm, "custom_permanent_city", { state: frm.doc.custom_permanent_state, district: frm.doc.custom_permanent_district, sub_district: frm.doc.custom_permanent_sub_district });
            handle_location_change(frm, "custom_permanent")
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

    custom_probation_status: function (frm) {
        if (frm.doc.custom_probation_status === "Confirmed") {
            frm.set_df_property("notice_number_of_days", "reqd", 1)
            frm.set_value("notice_number_of_days", "")
            frm.set_value("custom_leave_policy", "")
        }
    },
    // refresh: function (frm){
    //     prompt_probation_period = frappe.db.get_single_value("HR Settings","custom_probation_period_for_prompt")
    //     indifoss_probation_period = frappe.db.get_single_value("HR Settings","custom_probation_period_for_indifoss")
    //     if (frm.doc.company == "Prompt Equipments Pvt Ltd"){

    //     }
    // }


    resignation_letter_date(frm) {
        calculate_notice_days_employee(frm);
    },

    before_save(frm) {
        if (!frm.doc.relieving_date || !frm.doc.name) return;

        frappe.db.get_value(
            "Exit Approval Process",
            { employee: frm.doc.name },
            "name",
            function (r) {
                if (r && r.name) {
                    frappe.db.set_value(
                        "Exit Approval Process",
                        r.name,
                        "last_date_of_working",
                        frm.doc.relieving_date
                    );
                }
            }
        );
    },

    relieving_date(frm) {
        calculate_notice_days_employee(frm);
    }
});

// service letter employee approval
function show_service_letter_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Service Letter Agreement'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_employee_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Service Agreement - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}

// probation letter employee approval
function show_probation_letter_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Confirmation Letter'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_probation_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Probation Extension Letter - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}

// confirmation letter employee approval
function show_confirmation_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Confirmation Letter'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_confirmation_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Confirmation Letter - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}

// Non Disclosure letter employee approval
function show_non_disclosure_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Non-Disclosure Agreement Letter'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_non_disclosure_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Non-Disclosure Agreement - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}

// Consultant Service letter employee approval
function show_consultant_service_letter_completion_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Confirmation Letter'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_consultant_service_letter_completion_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Confirmation Letter - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}

// Consultant Contract letter employee approval
function show_consultant_contract_letter_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Consultant Contract Letter'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_consultant_contract_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Consultant Contract Letter - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}

// Relieving Experience letter employee approval
function show_relieving_experience_letter_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Relieving Letter'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_relieving_experience_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Relieving-Experience Letter - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}

// Promation letter employee approval
function show_promotion_letter_send_dialog(frm, already_sent) {
    const employee_id = frm.doc.employee || frm.doc.custom_employee;

    if (!employee_id) {
        frappe.throw("Employee ID not found on this document.");
        return;
    }

    frappe.db.get_value("Employee", employee_id, ["company_email", "personal_email"])
    .then(emp => {

        const company_email = emp.message.company_email || "";
        const personal_email = emp.message.personal_email || "";

        const dlg = new frappe.ui.Dialog({
            title: __('Send Confirmation Letter'),
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

                if (!values.send_company_email && !values.send_personal_email) {
                    frappe.throw("Select at least one email to send.");
                }

                frappe.dom.freeze("Creating approval record...");

                frappe.db.get_value(
                    "Employee",
                    { "user_id": frappe.session.user },
                    ["name", "employee_name"]
                ).then(emp => {

                    const released_by =
                        emp?.message
                            ? `${emp.message.name} - ${emp.message.employee_name}`
                            : frappe.session.user;

                    frappe.call({
                        method: "prompt_hr.py.employee.create_promotion_letter_approval",
                        args: {
                            employee_id: employee_id,
                            letter: "Promotion Letter - Prompt",
                            send_company_email: values.send_company_email ? 1 : 0,
                            send_personal_email: values.send_personal_email ? 1 : 0,
                            company_email: company_email,
                            personal_email: personal_email,
                            record: frm.doc.doctype,
                            record_link: frm.doc.name,
                            released_by_emp_code_and_name: released_by
                        },
                        callback(r) {
                            frappe.dom.unfreeze();

                            if (r.message?.status === "success") {
                                frappe.msgprint({ message: r.message.message, indicator: "green" });
                                dlg.hide();
                                frm.reload_doc();
                            } else {
                                frappe.msgprint({
                                    message: r.message?.message || "Failed to create approval.",
                                    indicator: "red"
                                });
                            }
                        }
                    });
                });
            }
        });

        dlg.show();
    });
}


// to cc service letter
function show_service_letter_to_cc_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: "Send Service Level Agreement",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });
            console.log("to_users", to_users)
            console.log("cc_users", cc_users)

            frappe.call({
                method: "prompt_hr.py.employee.send_service_agreement",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Service Letter Agreement Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}

// to cc probation letter letter
function show_probation_letter_to_cc_dialog(frm) {

    const d = new frappe.ui.Dialog({
        title: "Send Probation Letter",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            frappe.call({
                method: "prompt_hr.py.employee.send_probation_extension_letter",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "probation Letter Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}

// to cc confirmation letter
function show_confirmation_to_cc_dialog(frm) {

    const d = new frappe.ui.Dialog({
        title: "Send Confirmation Letter",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            frappe.call({
                method: "prompt_hr.py.employee.send_confirmation_letter",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Confirmation Letter Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}


function show_non_disclosure_to_cc_dialog(frm) {

    const d = new frappe.ui.Dialog({
        title: "Send Confirmation Letter",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            frappe.call({
                method: "prompt_hr.py.employee.send_non_disclosure_letter",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Confirmation Letter Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}

function show_consultant_service_to_cc_dialog(frm) {

    const d = new frappe.ui.Dialog({
        title: "Send Confirmation Letter",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            frappe.call({
                method: "prompt_hr.py.employee.send_consultant_service_letter",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Confirmation Letter Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}

function show_consultant_contract_letter_to_cc_dialog(frm) {

    const d = new frappe.ui.Dialog({
        title: "Send Confirmation Letter",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            frappe.call({
                method: "prompt_hr.py.employee.send_consultant_contract_letter",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Confirmation Letter Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}

function show_relieving_letter_to_cc_dialog(frm) {

    const d = new frappe.ui.Dialog({
        title: "Send Confirmation Letter",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            frappe.call({
                method: "prompt_hr.py.employee.send_relieving_letter",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Confirmation Letter Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}

function show_promotion_letter_to_cc_dialog(frm) {

    const d = new frappe.ui.Dialog({
        title: "Send Confirmation Letter",
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
                        reqd: 1,
                        in_list_view: 1
                    },
                    {
                        fieldtype: "Link",
                        fieldname: "user",
                        label: "User",
                        options: "User",
                        reqd: 1,
                        in_list_view: 1
                    }
                ]
            }
        ],

        primary_action_label: "Send Letter",

        primary_action(values) {

            let to_users = [];
            let cc_users = [];

            // default TO should be employee’s email
            if (frm.doc.company_email) {
                to_users.push(frm.doc.company_email);
            }

            values.recipient_table.forEach(row => {
                if (row.recipient_type === "To") {
                    to_users.push(row.user);
                } else {
                    cc_users.push(row.user);
                }
            });

            frappe.call({
                method: "prompt_hr.py.employee.send_promation_letter",
                args: {
                    name: frm.doc.name,
                    to: to_users,
                    cc: cc_users
                },
                callback(r) {
                    frappe.msgprint(r.message || "Confirmation Letter Sent");
                    d.hide();
                }
            });
        }
    });

    d.show();
}


frappe.ui.form.on("Probation Extension", {

    // custom_probation_extension_details_add: function (frm, cdt, cdn) {
    //     let row = locals[cdt][cdn]
    //     if (frm.doc.custom_probation_end_date && !row.probation_end_date) {
    //         row.probation_end_date = frm.doc.custom_probation_end_date
    //     }
    // },
    form_render: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn]
        if (frm.doc.custom_probation_end_date && !row.probation_end_date) {
            row.probation_end_date = frm.doc.custom_probation_end_date
            frm.refresh_field("custom_probation_extension_details")
        }
        else {
            console.log("Has Value", row.probation_end_date)
        }
    },
    probation_end_date: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn]

        if (row.probation_end_date && row.extended_period) {
            extended_days = 0
            if (row.extended_period == "30 Days") {
                extended_days = 30;
            }
            else if (row.extended_period == "60 Days") {
                extended_days = 60;
            }
            else if (row.extended_period == "90 Days") {
                extended_days = 90;
            }


            row.extended_date = frappe.datetime.add_days(row.probation_end_date, extended_days)
            frm.refresh_field("custom_probation_extension_details")
        }

    },
    extended_period: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn]

        if (row.probation_end_date && row.extended_period) {
            extended_days = 0
            if (row.extended_period == "30 Days") {
                extended_days = 30;
            }
            else if (row.extended_period == "60 Days") {
                extended_days = 60;
            }
            else if (row.extended_period == "90 Days") {
                extended_days = 90;
            }

            row.extended_date = frappe.datetime.add_days(row.probation_end_date, extended_days)
            frm.refresh_field("custom_probation_extension_details")
        }
    }
})

// ? FUNCTION TO CALCULATE notice_period_days = resignation_letter_date - relieving_date
async function calculate_notice_days_employee(frm) {
    if (!frm.doc.resignation_letter_date) return;

    // Get Exit Approval details
    let r = await frappe.db.get_value(
        "Exit Approval Process",
        { employee: frm.doc.name },
        ["name", "last_date_of_working"]
    );

    if (!r.message || !r.message.name || !r.message.last_date_of_working) return;

    // Convert dates
    let start = frappe.datetime.str_to_obj(frm.doc.resignation_letter_date);
    let end = frappe.datetime.str_to_obj(r.message.last_date_of_working);

    let days = frappe.datetime.get_diff(end, start);

    // Update notice_period_days
    await frappe.db.set_value(
        "Exit Approval Process",
        r.message.name,
        "notice_period_days",
        days
    );
}

// ? FUNCTION TO APPROVE/REJECT DETAILS UPLOADED BY EMPLOYEE
function addApproveEmployeeDetailsButton(frm) {
    frm.add_custom_button(__("Approve Employee Responses"), function () {
        let pendingRows = (frm.doc.custom_pre_login_questionnaire_response || []);
        if (!pendingRows.length) {
            frappe.msgprint("No pending responses to approve or reject.");
            return;
        }

        let approvedFields = [];
        let pendingFields = [];
        let takeActionFields = [];

        pendingRows.forEach((row, idx) => {
            const employeeResponseIsFile = typeof row.employee_response === 'string' &&
                (row.employee_response.startsWith('http') || /\.(pdf|docx?|xlsx?|png|jpg|jpeg|gif)$/i.test(row.employee_response));
            const employeeResponseIsTable = (() => {
                try {
                    let parsed = JSON.parse(row.employee_response);

                    // ! RETURN FALSE IF EMPTY ARRAY OR EMPTY OBJECT
                    if (Array.isArray(parsed)) {
                        return parsed.length > 0;
                    }
                    if (parsed && typeof parsed === "object") {
                        return Object.keys(parsed).length > 0;
                    }

                    return false;
                } catch {
                    return false;
                }
            })();

            let fieldBlock = [
                {
                    fieldname: `section_break_${idx}`,
                    fieldtype: 'Section Break',
                },
                {
                    fieldname: `field_label_${idx}`,
                    fieldtype: 'Data',
                    label: 'Field',
                    default: row.field_label,
                    read_only: 1,
                },
                { fieldtype: 'Column Break' },
                ...(employeeResponseIsFile ? [
                    {
                        fieldname: `employee_response_button_${idx}`,
                        fieldtype: 'Button',
                        label: '📂 Open Response File',
                        click: () => window.open(row.employee_response, '_blank')
                    }
                ] : employeeResponseIsTable ? [
                    {
                        fieldname: `employee_response_table_btn_${idx}`,
                        fieldtype: 'Button',
                        label: '📊 View Table Response',
                        click: () => {
                            try {
                                let parsed = JSON.parse(row.employee_response);
                                let tableDialog = new frappe.ui.Dialog({
                                    title: `Table Response - ${row.field_label}`,
                                    size: "large",
                                    fields: [{ fieldname: 'html_preview', fieldtype: 'HTML' }]
                                });

                                let html = `<div style="max-height:400px; overflow:auto;">
                                                <table class="table table-bordered table-striped">
                                                <thead class="table-dark">`;

                                if (parsed.length) {
                                    const ignoreFields = ["_row_id", "idx", "name", "__islocal"];
                                    let columnsToShow = [];
                                    Object.keys(parsed[0]).forEach(key => {
                                        if (!ignoreFields.includes(key)) {
                                            let hasValue = parsed.some(r => r[key] && r[key].value !== "");
                                            if (hasValue) columnsToShow.push(key);
                                        }
                                    });

                                    // header
                                    html += "<tr>";
                                    columnsToShow.forEach(colKey => {
                                        html += `<th style="padding:6px; text-align:center;">${frappe.utils.escape_html(parsed[0][colKey].label)}</th>`;
                                    });
                                    html += "</tr></thead><tbody>";

                                    // rows
                                    parsed.forEach(r => {
                                        html += "<tr>";
                                        columnsToShow.forEach(colKey => {
                                            let value = r[colKey]?.value || "";
                                            if (typeof value === "string" && value.startsWith("/private/files/")) {
                                                let fileUrl = frappe.urllib.get_full_url(value);
                                                value = `<a href="${fileUrl}" target="_blank">${frappe.utils.escape_html(value.split("/").pop())}</a>`;
                                            }
                                            html += `<td style="padding:6px;">${value}</td>`;
                                        });
                                        html += "</tr>";
                                    });

                                    html += "</tbody></table></div>";
                                } else {
                                    html = "<p class='text-muted'>No rows found in table response.</p>";
                                }

                                tableDialog.fields_dict.html_preview.$wrapper.html(html);
                                tableDialog.show();
                            } catch (e) {
                                frappe.msgprint("Invalid table data");
                            }
                        }
                    }
                ] : [
                    {
                        fieldname: `employee_response_${idx}`,
                        fieldtype: 'Data',
                        label: 'Employee Response',
                        default: (!row.employee_response || row.employee_response === "null" || row.employee_response === "[]" ||
                            row.employee_response === "{}") ? "" : row.employee_response,
                        read_only: 1
                    }
                ]),
                { fieldtype: 'Column Break' },
                {
                    fieldname: `status_${idx}`,
                    fieldtype: 'Select',
                    label: 'Action',
                    options: ['Approve', 'Reject'],
                    default: row.status === "Approve" ? "Approve" : "",
                    read_only: (row.status === "Approve" || !row.employee_response || row.employee_response === "null" || row.employee_response === "[]" ||
                        row.employee_response === "{}") ? 1 : 0
                },
                ...(row.attach ? [{
                    fieldname: `attachment_${idx}`,
                    fieldtype: 'Button',
                    label: '📎 Open Attachment',
                    click: () => window.open(row.attach, '_blank')
                }] : [])
            ];

            // Grouping logic
            if (row.status === "Approve") {
                approvedFields.push(...fieldBlock);
            } else if (
                !row.employee_response ||
                row.employee_response === "[]" ||
                row.employee_response === "{}"
            ) {
                pendingFields.push(...fieldBlock);
            } else {
                takeActionFields.push(...fieldBlock);
            }
        });

        let dialogFields = [
            ...buildSection("⏳ Pending Responses", "section_break_pending", pendingFields, "No pending responses."),
            ...buildSection("📝 Take Action Responses", "section_break_take_action", takeActionFields, "No action required."),
            ...buildSection("✅ Approved Responses", "section_break_approve", approvedFields, "No approved responses.")

        ];

        let dialog = new frappe.ui.Dialog({
            title: 'Approve/Reject Employee Responses',
            fields: dialogFields,
            primary_action_label: 'Submit',
            primary_action(values) {
                pendingRows.forEach((row, idx) => {
                    let action = values[`status_${idx}`];
                    if (!action) return;

                    if (action === 'Reject') {
                        row.status = 'Pending';
                        frappe.model.set_value(row.doctype, row.name, "employee_response", "");
                    } else if (action === 'Approve') {
                        row.status = 'Approve';

                        // ? HANDLE TABLE RESPONSES
                        try {
                            let parsed = JSON.parse(row.employee_response);
                            if (Array.isArray(parsed)) {
                                // CLEAR EXISTING CHILD TABLE AND REPOPULATE
                                frm.clear_table(row.employee_field_name);

                                parsed.forEach(r => {
                                    // CREATE CLEAN CHILD ENTRY
                                    let child = frm.add_child(row.employee_field_name);

                                    // LOOP THROUGH KEYS AND SET ONLY VALID FIELDS
                                    Object.keys(r).forEach(key => {
                                        if (["_row_id", "idx", "name", "__islocal"].includes(key)) return;

                                        if (r[key] && typeof r[key] === "object" && "value" in r[key]) {
                                            // SET FIELD VALUE
                                            child[key] = r[key].value;
                                        }
                                    });
                                });

                                // REFRESH CHILD TABLE
                                frm.refresh_field(row.employee_field_name);
                            } else {
                                // NORMAL FIELD
                                frm.set_value(row.employee_field_name, row.employee_response);
                            }
                        } catch {
                            // FALLBACK TO NORMAL FIELD
                            frm.set_value(row.employee_field_name, row.employee_response);
                        }

                    }
                });

                frm.refresh_field('custom_pre_login_questionnaire_response');
                dialog.hide();

                frm.save().then(() => {
                    // ? CALL PYTHON METHOD TO UPDATE PROFILE COMPLETION PERCENTAGE
                    frappe.call({
                        method: "prompt_hr.py.employee.set_profile_completion_percentage",
                        args: {
                            doc: frm.doc
                        },
                        callback: function (r) {
                            let allApproved = (frm.doc.custom_pre_login_questionnaire_response || [])
                                .every(r => r.status === "Approve");

                            if (allApproved) {
                                frm.save().then(() => {
                                    frappe.msgprint("All responses approved. Employee fields updated successfully.");
                                });
                            } else {
                                frappe.msgprint("Responses updated and saved successfully.");
                            }
                        }
                    });
                });

            }
        });

        dialog.show();
    }, __("Actions"));
}

function set_state_options(frm, state_field_name, country_field_name) {
    const state_field = frm.get_field(state_field_name);
    const country = frm.get_field(country_field_name).value;
    if (country !== "India") {
        state_field.set_data([]);
        return;
    }
    state_field.set_data(frappe.boot.india_state_options || []);
}

// ? FUNCTION TO CREATE BOTH BUTTONS FOR RESIGNATION & TERMINATION
function createEmployeeActionButtons(frm) {
    frm.add_custom_button(__("Raise Resignation"), function () {
        handleEmployeeExitOrTermination(frm, "Resignation");
    }, __("Actions"));

    // ? TERMINATION ALLOWED FOR HR ROLES ONLY
    const allowed_roles = [
        "S - HR Leave Approval", "S - HR leave Report", "S - HR L6",
        "S - HR L5", "S - HR L4", "S - HR L3", "S - HR L2", "S - HR L1",
        "S - HR Director (Global Admin)", "S - HR L2 Manager",
        "S - HR Supervisor (RM)", "System Manager"
    ];

    const can_show_hr_button =
        frappe.user_roles.some(role => allowed_roles.includes(role)) ||
        frappe.session.user === "Administrator"

    if (!can_show_hr_button) {
        add_terminate_button(frm);
        return;
    }

    if (frappe.session.user) {
        frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name")
            .then(r => {
                const emp_id = r.message ? r.message.name : "";
                const is_reporting_manager = emp_id && frm.doc.reports_to === emp_id;

                if (is_reporting_manager) {
                    add_termination_button(frm);
                }
            })
            .catch(err => console.error("Error fetching employee:", err));
    }
}


function add_terminate_button(frm) {
    frm.add_custom_button(__("Raise Termination"), function () {
        handleEmployeeExitOrTermination(frm, "Termination");
    }, __("Actions"));
}


// ? FUNCTION TO HANDLE EXIT OR TERMINATION DIALOG CREATION
function handleEmployeeExitOrTermination(frm, typeOfExit) {

    // ? FETCH QUESTIONS BASED ON TYPE (EXIT OR TERMINATION)
    frappe.call({
        method: "prompt_hr.py.employee.get_raise_resignation_questions",
        args: {
            company: frm.doc.company,
            employee: frm.doc.name,
            type_of_exit: typeOfExit
        },
        callback: function (res) {
            if (res.message && res.message.length > 0) {
                const questions = res.message;

                // ? DYNAMICALLY BUILD DIALOG FIELDS BASED ON QUESTIONS
                const fields = questions.map(q => {
                    let field = {
                        label: q.question_detail || q.question,
                        fieldname: q.question,
                        reqd: true
                    };

                    if (q.type !== "Open Ended" || !q.custom_input_type) {
                        field.fieldtype = "Data";
                        return field;
                    }

                    switch (q.custom_input_type) {
                        case "Checkbox":
                            field.fieldtype = "MultiCheck";
                            field.label = (stripHtml(q.question_detail) || q.question) + " <span style='color:#f1afb0'>*</span>";
                            field.options = (q.custom_multi_checkselect_options || "")
                                .split("\n")
                                .map(opt => opt.trim())
                                .filter(opt => opt)
                                .map(opt => ({ label: opt, value: opt }));
                            break;

                        case "Dropdown":
                            field.fieldtype = "Select";
                            field.options = (q.custom_multi_checkselect_options || "")
                                .split("\n")
                                .map(opt => opt.trim())
                                .filter(opt => opt)
                                .join("\n");
                            break;

                        case "Yes/No/NA":
                            field.fieldtype = "Select";
                            field.options = "Yes\nNo\nNA";
                            break;

                        case "Date":
                            field.fieldtype = "Date";
                            break;

                        case "Single Line Input":
                            field.fieldtype = "Data";
                            break;

                        case "Small Text":
                            field.fieldtype = "Small Text";
                            break;

                        default:
                            field.fieldtype = "Data";
                    }

                    return field;
                });

                // ? ADD DATE FIELD (ONLY FOR HR ROLES)
                const allowed_roles = [
                    "S - HR Leave Approval", "S - HR leave Report", "S - HR L6",
                    "S - HR L5", "S - HR L4", "S - HR L3", "S - HR L2", "S - HR L1",
                    "S - HR Director (Global Admin)", "S - HR L2 Manager",
                    "S - HR Supervisor (RM)", "System Manager"
                ];

                const can_show_button = frappe.user_roles.some(role => allowed_roles.includes(role));
                if (can_show_button || frappe.session.user === "Administrator") {
                    fields.push({
                        label: `${typeOfExit} Date`,
                        fieldname: `${typeOfExit.toLowerCase()}_date`,
                        fieldtype: "Date",
                        default: frappe.datetime.nowdate()
                    });
                }

                // ? CREATE AND DISPLAY DIALOG
                const dialog = new frappe.ui.Dialog({
                    title: __(typeOfExit + ' Details'),
                    fields: fields,
                    primary_action_label: __('Submit'),

                    // ? WHEN SUBMIT IS CLICKED
                    primary_action(values) {
                        frappe.dom.freeze(__('Processing...'));

                        const answers = questions.map(q => {
                            let answer = values[q.question];
                            if (Array.isArray(answer)) {
                                answer = answer.join("\n");
                            }
                            return {
                                question_name: q.question,
                                question: strip_html(q.question_detail) || q.question,
                                answer: answer
                            };
                        });

                        // ? CREATE EXIT/TERMINATION RECORD
                        frappe.call({
                            method: "prompt_hr.py.employee.create_resignation_quiz_submission",
                            args: {
                                employee: frm.doc.name,
                                user_response: answers,
                                notice_number_of_days: frm.doc.notice_number_of_days,
                                resignation_date: values[`${typeOfExit.toLowerCase()}_date`] || frappe.datetime.nowdate(),
                                type_of_exit: typeOfExit
                            },
                            callback: function (r) {
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

                // ? STYLING MULTICHECK OPTIONS
                dialog.$wrapper.find('.frappe-control[data-fieldtype="MultiCheck"] .checkbox').css({
                    display: "inline-block",
                    marginRight: "10px",
                    minWidth: "120px"
                });

            } else {
                frappe.msgprint(__("No " + typeOfExit.toLowerCase() + " questions found or process already initiated."));
            }
        }
    });
}

// ? STRIP HTML HELPER FUNCTION
function stripHtml(html) {
    let tempDiv = document.createElement("div");
    tempDiv.innerHTML = html;
    return tempDiv.textContent || tempDiv.innerText || "";
}

// ? FUNCTION TO ADD A CUSTOM BUTTON ON THE EMPLOYEE FORM
function addEmployeeDetailsChangesButton(frm) {
    // ? ADD BUTTON TO FORM HEADER
    frm.add_custom_button("Apply for Changes", () => {
        loadDialogBox(frm);
    }, __("Actions"));
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
                reqd: 1,
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
            reqd: 1,
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

/**
 * ? APPLY CASCADING LOCATION FILTERS AND DYNAMIC CITY AUTOCOMPLETE
 * @param {object} frm - Frappe Form Object
 * @param {object} fields - Fields mapping (state, district, sub_district, city)
 */
function apply_location_filters(frm, fields, country) {
    const {
        state_field,
        district_field,
        sub_district_field,
        city_field
    } = fields;

    if (country === "India") {
        // ? APPLY FILTER: DISTRICT BY STATE
        if (state_field && district_field) {
            frm.set_query(district_field, () => {
                if (!frm.doc[state_field]) {
                    frappe.msgprint("Please select State first.");
                    frm.set_value(district_field, null);
                    return { filters: { name: "none" } }
                }
                return { filters: { state: frm.doc[state_field] } }
            });
        }

        // ? APPLY FILTER: SUB-DISTRICT BY DISTRICT
        if (district_field && sub_district_field) {
            frm.set_query(sub_district_field, () => {
                if (!frm.doc[district_field]) {
                    frappe.msgprint("Please select District first.");
                    frm.set_value(sub_district_field, null);
                    return { filters: { name: "none" } };
                }
                return { filters: { district: frm.doc[district_field] } };
            });
        }

        // ? SETUP AUTOCOMPLETE FOR CITY BY SUB-DISTRICT (OR HIGHER FILTERS)
        if (city_field && sub_district_field) {
            frm.set_query(city_field, () => {
                if (!frm.doc[sub_district_field]) {
                    frappe.msgprint("Please select Sub District first.");
                    return;
                }
            });
            set_city_autocomplete_options(frm, {
                state: frm.doc[state_field],
                district: frm.doc[district_field],
                sub_district: frm.doc[sub_district_field]
            });
        }

    } else {
        // ? REMOVE ALL CUSTOM LOCATION FILTERS FOR NON-INDIA COUNTRY
        if (district_field) frm.set_query(district_field, null);
        if (sub_district_field) frm.set_query(sub_district_field, null);
        if (city_field) frm.set_query(city_field, null);

        // ? RESET CITY FIELD TO PLAIN DATA (NO AUTOCOMPLETE)
        reset_city_field_to_data(frm, city_field);
    }
}

/**
 * Set autocomplete options for city field based on filters
 * @param {object} frm - Frappe Form Object
 * @param {string} fieldname - Field to set options for
 * @param {object} filters - Filters for frappe.client.get_list
 */
function set_city_autocomplete_options(frm, fieldname, filters = {}) {
    const setOptions = options => {
        const field = frm.fields_dict[fieldname];
        if (field?.set_data) field.set_data(options);
        else if (field?.$input?.autocomplete) field.$input.autocomplete({ source: options });
    };

    if (!filters.sub_district) return setOptions([]);

    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Village or City",
            fields: ["name"],
            filters,
            order_by: "name asc",
            limit_page_length: 0
        },
        callback: r => setOptions(r.message?.map(doc => doc.name) || [])
    });
}


/**
 * ? RESET CITY FIELD TO SIMPLE DATA (WITHOUT AUTOCOMPLETE) FOR NON-INDIA COUNTRY
 * @param {object} frm - Frappe Form Object
 * @param {string} city_field - Fieldname for city
 */
function reset_city_field_to_data(frm, city_field) {
    if (frm.fields_dict[city_field]) {
        // ? REMOVE ANY AUTOCOMPLETE DATA/OPTIONS
        if (frm.fields_dict[city_field].set_data) {
            frm.fields_dict[city_field].set_data([]);
        }
        if (frm.fields_dict[city_field].$input && frm.fields_dict[city_field].$input.autocomplete) {
            frm.fields_dict[city_field].$input.autocomplete({ source: [] });
        }
        // ? ENSURE THE FIELD IS ENABLED FOR USER INPUT
        frm.toggle_enable(city_field, true);
    }
}

// ? HANDLE LOCATION CHANGE LOGIC AND CALL APPLY_LOCATION_FILTERS FUNCTION
function handle_location_change(frm, prefix) {
    const country = frm.doc[`${prefix}_country`];
    if (country !== "India") return;

    // ! FIELD MAPPING
    const fields = {
        state_field: `${prefix}_state`,
        district_field: `${prefix}_district`,
        sub_district_field: `${prefix}_sub_district`,
        city_field: `${prefix}_city`
    };

    apply_location_filters(frm, fields, country);
}

function add_profile_completion_percentage(frm) {
    // Find the container that holds all indicator chips, not a single chip itself
    let $chips_container = frm.page.wrapper.find(".indicator-pill").parent(); // Get parent container

    if (!$chips_container.length) return;

    frm.page.wrapper.find(".custom-profile-chip").remove();

    if (frm.doc.custom_profile_completion_percentage != null) {
        let percent = frm.doc.custom_profile_completion_percentage;
        let color = percent > 80 ? "green" : "red";  // green or red hex

        let $chip = $(`
            <span class="custom-profile-chip" style="
                background-color: ${color};
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                margin-left: 8px;
                display: inline-block;
                line-height: 1.3;
                user-select: none;
            ">
                ${percent}% completed
            </span>
        `);

        // Append custom chip alongside original chips, not inside
        $chips_container.append($chip);
    }
}

function buildSection(label, fieldname, fields, emptyMessage) {
    let section = [];

    if (fields.length) {
        // If the first field is a Section Break, drop it
        if (fields[0].fieldtype === "Section Break") {
            fields = fields.slice(1);
        }

        // Always add our labeled Section Break
        section.push({
            fieldtype: "Section Break",
            label: label,
            fieldname: fieldname,
        });

        section.push(...fields);
    } else {
        section.push({
            fieldtype: "Section Break",
            label: label,
            fieldname: fieldname,
        });
        section.push({
            fieldtype: "HTML",
            options: `<p class='text-muted text-center'>${emptyMessage}</p>`
        });
    }

    return section;
}

function stripHtml(html) {
    let temp = document.createElement("div");
    temp.innerHTML = html;
    return temp.textContent || temp.innerText || "";
}

// ? FUNCTION TO AUTO-CLICK "Raise Resignation" BUTTON IF URL PARAMETER IS PRESENT
function raise_resignation_button_auto_click_from_url(frm) {

    // ? ONLY TRIGGER WHEN URL PARAM IS PRESENT
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("raise_resignation") === "1") {

        // ? TRIGGER "Raise Resignation" BUTTON FROM cur_frm.custom_buttons
        if (cur_frm.custom_buttons["Raise Resignation"]) {
            cur_frm.custom_buttons["Raise Resignation"].click();
        }

        // ? REMOVE PARAM TO PREVENT RE-TRIGGER ON NEXT REFRESH
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

// ? FUNCTION TO CHANGE PERM LEVEL OF EMPLOYEE FOR CERTAIN FIELDS VISIBILITY
function set_field_visibility(frm) {
    let current_user = frappe.session.user;

    // ? GET USER LINKED TO THIS EMPLOYEE
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { name: frm.doc.name },
            fieldname: "user_id"
        },
        callback: function (r) {
            if (r && r.message && r.message.user_id) {
                let employee_user = r.message.user_id;

                // ? CHECK IF LOGGED-IN USER IS SAME AS EMPLOYEE'S USER
                if (employee_user === current_user) {
                    // ? CALL BACKEND TO GET FIELD VISIBILITY SETTINGS
                    frappe.call({
                        method: "prompt_hr.py.employee.get_field_visibility_settings",
                        args: {
                            employee: frm.doc.name,
                            user: current_user
                        },
                        callback: function (res) {
                            if (res && res.message) {
                                Object.entries(res.message).forEach(([field, value]) => {
                                    let field_obj = frm.fields_dict[field];
                                    if (field_obj) {
                                        if (field_obj.df.permlevel > 0) {
                                            has_perm = frappe.perm.has_perm("Employee", "read", employee_user, permlevel = field_obj.df.permlevel)
                                            if (!has_perm) {
                                                frm.set_df_property(field, "permlevel", 0)
                                                frm.set_value(field, value, null, true)
                                                frm.refresh_field(field)
                                            }
                                        }
                                        else {
                                            if (!frm.doc.field) {
                                                frm.set_value(field, value, null, true)
                                                frm.refresh_field(field)
                                            }

                                        }

                                    }
                                });
                            }
                        }
                    });
                }
            }
        }
    });
}

function disable_employee_fields_for_left_employee(frm) {
    const should_lock = frm.doc.status === "Left" && !frm.is_dirty();

    if (should_lock) {
        frappe.after_ajax(() => {
            frm.fields.forEach((field) => {
                if (field.df.fieldname !== "status") {
                    frm.set_df_property(field.df.fieldname, "read_only", 1);
                }
            });
            hide_employee_buttons(frm);
        });
    }
}

function hide_employee_buttons(frm) {
    // ? Hide sidebar actions (Attach, Assign, Share)
    $(frm.wrapper).find(".form-sidebar").hide();

    // ? Hide top-right buttons (Save, Menu, Print, Refresh)
    $(frm.wrapper).find(".form-inner-toolbar").hide();

    // ? Hide secondary buttons
    $(frm.wrapper).find(".btn-default").hide();

    // ✅ Clear toolbar actions
    frm.page.clear_actions();
    frm.page.clear_menu();

    // ? Hide custom buttons inserted by scripts
    $(frm.wrapper)
        .find(".custom-actions, .custom-btn, .btn-custom")
        .hide();
}

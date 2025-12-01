// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Confirmation Evaluation Form", {
    refresh: function (frm) {
        // * Making the rh_rating and dh_rating fields read-only based on the logged-in user is either the reporting manager or head of department

        const user = frappe.session.user;
        const reporting_manager = frm.doc.reporting_manager;
        const head_of_department = frm.doc.hod;

        console.log("User:", user);

        frappe.call({
            "method": "frappe.client.get_value",
            "args": {
                "doctype": "Employee",
                "filters": {
                    "user_id": user
                },
                "fieldname": ["name"]
            },
            "callback": function (response) {
                if (response.message) {

                    rh_fields = ["confirmed_by_rh", "further_to_by_rh", "reason_for_extension_by_rh", "extension_period_by_rh", "reason_for_termination_by_rh", "mention_strengths_of_employee", "mention_areas_of_improvement", "recommend_trainings_if_any"]

                    rh_reqd_fields = ["mention_strengths_of_employee", "mention_areas_of_improvement", "recommend_trainings_if_any"]

                    dh_fields = ["confirmed_by_dh", "further_to_by_dh", "reason_for_extension_by_dh", "extension_period_by_dh", "reason_for_termination_by_dh"]
                    const hr_manager_roles = ["S - HR L1", "S - HR Director (Global Admin)"];

                    const user_employee_name = response.message.name;

                    if (user_employee_name === reporting_manager && frm.doc.workflow_state === "Pending") {
                        console.log("User is Reporting Manager");

                        frm.fields_dict.table_txep.grid.update_docfield_property('rh_rating', 'read_only', 0);
                        frm.fields_dict.table_txep.grid.update_docfield_property('remarks_if_any', 'read_only', 1);

                        frm.set_df_property("department_head_status_section", "hidden", 1)

                        rh_reqd_fields.forEach(field => {
                            frm.set_df_property(field, "reqd", 1)
                        })
                        rh_fields.forEach(field => {
                            frm.set_df_property(field, "read_only", 0)
                        })

                        dh_fields.forEach(field => {
                            frm.set_df_property(field, "read_only", 1)
                        })

                    }
                    else if (user_employee_name === head_of_department && frm.doc.workflow_state === "Submitted by RM") {

                        frm.fields_dict.table_txep.grid.update_docfield_property('rh_rating', 'read_only', 1);

                        frm.set_df_property("department_head_status_section", "hidden", 0)

                        rh_fields.forEach(field => {
                            frm.set_df_property(field, "read_only", 1)
                        })

                        dh_fields.forEach(field => {
                            frm.set_df_property(field, "read_only", 0)
                        })
                    }
                    else {
                        $.each(frm.fields_dict, function (fieldname, field) {
                            frm.set_df_property(fieldname, "read_only", 1);
                        });
                    }

                    // } else if (hr_manager_roles.some(role=>frappe.user.has_role(role))) {

                    //     frm.set_df_property("reporting_head_status_section", "hidden", 0)
                    //     frm.set_df_property("department_head_status_section", "hidden", 0)

                    //     rh_fields.forEach(field => {
                    //         frm.set_df_property(field, "read_only", 1)
                    //     })

                    //     dh_fields.forEach(field => {
                    //         frm.set_df_property(field, "read_only", 1)
                    //     })

                    // }
                }

            }
        })

        // * Applying filters to the 'parameters' field in the 'table_txep' child table based on the selected 'category'
        frm.fields_dict['table_txep'].grid.get_field('parameters').get_query = function (doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            console.log("get_query (refresh) - Category:", row.category);
            if (row.category) {
                return {
                    filters: [
                        ['category', '=', row.category]
                    ]
                };
            }
            return { filters: {} };
        };
        frm.fields_dict['table_txep'].grid.refresh();

        // Show approval note to reporting manager when state is 'Pending'
        if (!frm.doc.__islocal && frm.doc.workflow_state === "Pending") {
            if (frm.doc.reporting_manager) {
                frappe.db.get_value("Employee", frm.doc.reporting_manager, "user_id")
                    .then(r => {
                        let manager_user = r.message.user_id;

                        // Check if logged-in user is the reporting manager
                        if (manager_user === frappe.session.user) {
                            frm.dashboard.clear_headline();
                            frm.dashboard.set_headline_alert(
                                "Approve this document using the action button to confirm",
                                "blue"
                            );
                        }
                    });
            }
        }

        // Show approval note to department head when state is 'Submitted by RM'
        if (frm.doc.workflow_state === "Submitted by RM") {
            if (frm.doc.department) {
                frappe.db.get_value("Department", frm.doc.department, "custom_department_head")
                    .then(r => {
                        if (!r || !r.message || !r.message.custom_department_head) return;

                        let dept_head_employee = r.message.custom_department_head;

                        // Now fetch the user_id of that employee
                        frappe.db.get_value("Employee", dept_head_employee, "user_id")
                            .then(emp => {
                                if (!emp || !emp.message || !emp.message.user_id) return;

                                let dept_head_user = emp.message.user_id;

                                // Compare with currently logged-in user
                                if (dept_head_user === frappe.session.user) {
                                    frm.dashboard.clear_headline();
                                    frm.dashboard.set_headline_alert(
                                        "Approve this document using the action button to confirm.",
                                        "blue"
                                    );
                                }
                            });
                    });
            }
        }
    },

    before_workflow_action: async function (frm) {

        if (frm.selected_workflow_action === "Submit" && frm.doc.workflow_state === "Pending") {
            frappe.dom.unfreeze();

            await frappe.call({
                method: "is_probation_feedback_rating_added",
                doc: frm.doc,
            })

            await frappe.call({
                method: "ratings_added_by_rm_and_send_mail",
                doc: frm.doc,

            })
        }

        if (frm.selected_workflow_action === "Submit" && frm.doc.workflow_state === "Submitted by RM") {
            frappe.dom.unfreeze()
            console.log("This is getting called")
            await frappe.call({
                "method": "ratings_added_by_dh_and_send_mail",
                doc: frm.doc
            })
        }
        // frappe.throw("test")
    },
    after_save(frm) {

        if (frm.doc.docstatus == 1) {
            console.log("this is getting caed")
            if (frm.doc.probation_status === "Confirm" && frm.doc.employee) {
                console.log("This Ran")
                frappe.route_options = {
                    show_update_message: 1
                }

                frappe.set_route('Form', 'Employee', frm.doc.employee);
            }
        }
        else {
            console.log("This rsdfssddfs")
        }
    },
    probation_status: function (frm) {
        // *CALCULATING THE LAST DATE OF WORK FROM THE DATE WHEN PROBATION STATUS IS SET TO TERMINATE TO BASED ON THE NOTICE PERIOD DAYS

        if (frm.doc.probation_status === "Terminate") {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["notice_number_of_days"]
                },
                callback: function (r) {
                    if (r.message) {
                        const notice_number_of_days = r.message.notice_number_of_days;
                        let today = frappe.datetime.get_today();
                        console.log("Today:", today);
                        const last_work_date = frappe.datetime.add_days(today, notice_number_of_days);
                        console.log("last work date", last_work_date, "after", notice_number_of_days, "days");


                        frm.set_value("last_work_date", last_work_date);
                    }
                }
            });

        }

    }
});

frappe.ui.form.on('Confirmation Evaluation', {

    rh_rating: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.rh_rating < 1 || row.rh_rating > 5) {
            frappe.throw("Rating must be between 1 and 5");
        }
    }

})
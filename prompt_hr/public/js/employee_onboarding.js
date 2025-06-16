frappe.ui.form.on("Employee Onboarding", {
    
    // ? RUN ON FORM REFRESH
    refresh: async function (frm) {
        // update_first_activity_if_needed(frm);
        let applicants = await frappe.db.get_list("Job Applicant", {
            fields: ["name"],
            or_filters: [
                ["status", "=", "Accepted"],
                ["custom_is_offer_required_while_onboarding", "=", 0]
            ],
        });
        frm.set_query("job_applicant", function () {
            return {
                filters: [
                    ["name", "in",applicants.map(applicant => applicant.name)],
                ]
            };
        });
        if (frm.doc.job_applicant) {
            frappe.db.get_doc("Job Applicant", frm.doc.job_applicant).then(applicant_data => {
                if (!applicant_data.custom_is_offer_required_while_onboarding) {
                    frm.toggle_reqd("job_offer", 0);
                } else {
                    frm.toggle_reqd("job_offer", 1);
                }
            });
        }

        if (!frm.is_new() && frm.doc.employee_onboarding_template) {

            // ? INVITE FOR DOCUMENT COLLECTION BUTTON
            createInviteButton(frm);
        }
    },
    // ? WHEN ONBOARDING TEMPLATE IS SELECTED
    employee_onboarding_template: function (frm) {
        handle_template_selection(frm);
    },
    job_applicant: function (frm) {
        if (frm.doc.job_applicant) {
            frappe.db.get_doc("Job Applicant", frm.doc.job_applicant).then(applicant_data => {
                if (!applicant_data.custom_is_offer_required_while_onboarding) {
                    frm.toggle_reqd("job_offer", 0);
                } else {
                    frm.toggle_reqd("job_offer", 1);
                }
            });
        }
    }
});

// ? HANDLE TEMPLATE SELECTION: CLEAR + FETCH + POPULATE
function handle_template_selection(frm) {
    clear_activities(frm);

    if (frm.doc.employee_onboarding_template) {
        fetch_template_activities(frm.doc.employee_onboarding_template, function (activities) {
            populate_activities(frm, activities);
        });
    }
}

// ? CLEAR EXISTING ACTIVITIES CHILD TABLE
function clear_activities(frm) {
    frm.set_value("activities", "");
}

// ? FETCH ACTIVITIES FROM SERVER BASED ON TEMPLATE
function fetch_template_activities(template_name, callback) {
    frappe.call({
        method: "prompt_hr.py.employee_onboarding.get_onboarding_details",
        args: {
            parent: template_name,
            parenttype: "Employee Onboarding Template",
        },

        // ? WHEN DATA IS RETURNED
        callback: function (r) {
            if (r.message) {
                callback(r.message);
            } else {
                callback([]);
            }
        }
    });
}

// ? POPULATE ACTIVITIES CHILD TABLE AND REFRESH FIELD
function populate_activities(frm, activities) {
    activities.forEach((d) => {
        frm.add_child("activities", d);
    });
    refresh_field("activities");
}

// ? SET FIRST ACTIVITY custom_is_raised TO 1 IF IT'S 0
function update_first_activity_if_needed(frm) {
    const first_activity = frm.doc.activities && frm.doc.activities[0];

    if (first_activity && first_activity.custom_is_raised == 0) {

        // ? UPDATE VALUE
        first_activity.custom_is_raised = 1;

        // ? REFRESH CHILD TABLE
        refresh_field("activities");

        // ? SAVE FORM
        frm.save();
    }
}

// ? CREATE INVITE FOR DOCUMENT COLLECTION BUTTON
function createInviteButton(frm) {
    frm.add_custom_button(__('Invite for Document Collection'), function () {

        // ? CREATE A DIALOG TO COLLECT EXTRA DETAILS
        let dialog = new frappe.ui.Dialog({
            title: 'Invite for Document Collection',
            fields: [
                {
                    label: 'Joining Document Checklist',
                    fieldname: 'joining_document_checklist',
                    fieldtype: 'Link',
                    options: 'Joining Document Checklist',
                    reqd: 1,
                    onchange: function () {

                        // ?  FETCH DOCUMENTS FROM THE SELECTED CHECKLIST USING A CUSTOM METHOD
                        if (dialog.get_value('joining_document_checklist')) {
                            dialog.set_df_property('documents', 'data', []);

                            frappe.call({
                                method: "prompt_hr.py.utils.get_checklist_documents",
                                args: {
                                    checklist: dialog.get_value('joining_document_checklist')
                                },
                                callback: function (r) {

                                    // ?  HIDE LOADING INDICATOR
                                    frappe.hide_progress();

                                    // ?  DEBUG RESPONSE
                                    console.log("API Response:", r);

                                    // ?  CHECK FOR ERROR IN RESPONSE
                                    if (r.exc) {
                                        frappe.msgprint({
                                            title: __("Error"),
                                            message: __("Error fetching documents: ") + r.exc,
                                            indicator: "red"
                                        });
                                        return;
                                    }
                                    // ?  VALIDATE DOCUMENTS DATA
                                    if (r.message && r.message.documents) {
                                        let documents = r.message.documents;
                                        console.log("Documents received:", documents);

                                        if (!documents.length) {
                                            frappe.msgprint({
                                                title: __("Info"),
                                                message: __("No documents found in the selected checklist."),
                                                indicator: "blue"
                                            });
                                            return;
                                        }
                                        // ?  UPDATE THE DATA FOR THE DOCUMENTS FIELD
                                        dialog.fields[3].data = documents;

                                        dialog.fields_dict.documents.grid.refresh();
                                    } else {
                                        console.error("Invalid response format:", r.message);
                                        frappe.msgprint({
                                            title: __("Error"),
                                            message: __("Invalid response format from server."),
                                            indicator: "red"
                                        });
                                    }
                                }
                            });
                        }
                    }
                },
                {
                    label: 'Document Collection Stage',
                    fieldname: 'document_collection_stage',
                    fieldtype: 'Link',
                    options: 'Document Collection Stage',
                    onchange: function () {
                        // ? UPDATE ALL ROWS WITH THE SELECTED STAGE
                        let stage = dialog.get_value('document_collection_stage');
                        if (stage) {

                            let documents = dialog.fields[3].data
                            let newDocuments = documents.filter(doc => {
                                return doc.document_collection_stage == stage;
                            });

                            // ?  UPDATE THE DATA FOR THE DOCUMENTS FIELD
                            dialog.fields[3].data = newDocuments;
                            dialog.fields_dict.documents.grid.refresh();
                        }
                    }
                },
                {
                    label: 'Documents',
                    fieldname: 'documents',
                    fieldtype: 'Table',
                    cannot_add_rows: true,
                    fields: [
                        {
                            label: 'Required Document',
                            fieldname: 'required_document',
                            fieldtype: 'Link',
                            options: 'Required Document Applicant',
                            in_list_view: 1,
                            read_only: 1
                        },
                        {
                            label: 'Document Collection Stage',
                            fieldname: 'document_collection_stage',
                            fieldtype: 'Link',
                            options: 'Document Collection Stage',
                            in_list_view: 1,
                            read_only: 1
                        }
                    ],
                    data: []
                }
            ],
            primary_action_label: 'Send Invite',
            primary_action(values) {

                // ?  VALIDATE THAT WE HAVE DOCUMENTS
                if (!dialog.fields_dict.documents.grid.grid_rows || !dialog.fields_dict.documents.grid.grid_rows.length) {
                    frappe.msgprint({
                        title: __("Warning"),
                        message: __("No documents selected for collection. Please select a valid checklist."),
                        indicator: "yellow"
                    });
                    return;
                }
                dialog.hide();

                // ?  GET SELECTED DOCUMENTS FROM THE CHILD TABLE
                let selected_documents = [];
                dialog.fields_dict.documents.grid.grid_rows.forEach(row => {
                    if (row && row.doc) {
                        selected_documents.push({
                            required_document: row.doc.required_document,
                            document_collection_stage: row.doc.document_collection_stage
                        });
                    }
                });

                // ? TRIGGER BACKEND METHOD WITH EXTRA INFO
                frappe.call({
                    method: "prompt_hr.py.utils.invite_for_document_collection",
                    args: {
                        args: {
                            name: frm.doc.job_applicant,
                            joining_document_checklist: values.joining_document_checklist,
                            document_collection_stage: values.document_collection_stage,
                            documents: selected_documents,
                        },
                        joining_document_checklist: values.joining_document_checklist,
                        document_collection_stage: values.document_collection_stage,
                        documents: selected_documents,
                        child_table_fieldname: "new_joinee_documents"
                    },
                    callback: function (r) {
                        if (r.message === "Already invited for document collection.") {
                            frappe.msgprint({
                                title: __("Info"),
                                message: __("This candidate has already been invited for document collection."),
                                indicator: "blue"
                            });
                        } else if (r.message === "An error occurred while inviting for document collection.") {
                            frappe.msgprint({
                                title: __("Error"),
                                message: __("Oops! Something went wrong while sending the invite. Please try again or check the logs."),
                                indicator: "red"
                            });
                        } else {
                            frappe.msgprint({
                                title: __("Success"),
                                message: __("Invite for document collection has been sent successfully!"),
                                indicator: "green"
                            });
                        }
                    }
                });
            }
        });

        dialog.show();
    });
}
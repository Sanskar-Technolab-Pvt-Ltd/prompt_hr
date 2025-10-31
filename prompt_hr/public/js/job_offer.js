

frappe.ui.form.on('Job Offer', {
    // ? MAIN ENTRY POINT — EXECUTES ON FORM REFRESH
    refresh: async function (frm) {
        const is_candidate = frappe.session.user === "candidate@promptdairytech.com";
        const hr_roles_response = await frappe.call({
            method: "prompt_hr.py.expense_claim.get_roles_from_hr_settings",
            args: { role_type: "hr" },
        });
        const hr_roles = hr_roles_response?.message || [];
        const hr_system_roles = ["System Manager", ...hr_roles];
        if (is_candidate) {
            handle_candidate_access(frm);
        } else if ((hr_system_roles || frappe.session.user == "Administrator") && frm.doc.workflow_state == "Approved") {
            // ? SHOW RELEASE JOB OFFER BUTTON ONLY TO HR ROLES
            add_release_offer_button(frm);
        }

        // ? CREATE INVITE BUTTON FOR DOCUMENT COLLECTION
        createInviteButton(frm);

        // ? ADD UPDATE CANDIDATE PORTAL BUTTON AND FUNCTIONALITY
        updateCandidatePortal(frm);

        // ? ADD ACCEPT CHANGES BUTTON
        acceptChangesButton(frm);

        viewCandidatePortalButton(frm)

        // ? ADD RELEASE LOI LETTER BUTTON
        if (frm.doc.workflow_state == "Approved") {
            frm.add_custom_button(__("Release LOI Letter"), function () {
                frappe.dom.freeze(__('Releasing Letter...'));
                frappe.call({
                    method: "prompt_hr.py.job_offer.send_LOI_letter",
                    args: { name: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint(r.message);
                            frm.reload_doc();
                        }
                    },
                    always: function () {
                        frappe.dom.unfreeze();
                    }
                });
            }, 'Offer Actions');
        }
        
    }
});

// ? HANDLE ACCESS FOR CANDIDATE USER
function handle_candidate_access(frm) {
    const is_verified = sessionStorage.getItem("job_offer_verified") === "true";

    if (!is_verified) {
        frappe.msgprint({
            title: "Access Denied",
            message: "🚫 You are not authorized to view this page.",
            indicator: "red"
        });
        window.location.href = "/app";
        return;
    }

    // ? CANDIDATE IS VERIFIED — SHOW ALL FIELDS
    frm.fields.forEach(field => {
        frm.set_df_property(field.df.fieldname, 'hidden', false);
    });
}

// ? ADD "RELEASE / RESEND OFFER LETTER" BUTTON FOR HR MANAGER
function add_release_offer_button(frm) {
    const already_sent = frm.doc.custom_offer_letter_sent === 1;
    const button_label = already_sent ? "Resend Offer Letter" : "Release Offer Letter";

    frm.add_custom_button(button_label, () => {
        frappe.confirm(
            `Are you sure you want to ${already_sent ? "resend" : "release"} the offer letter?`,
            () => release_offer_letter(frm, already_sent)
        );
    }, 'Offer Actions');
}

function viewCandidatePortalButton(frm) {
    frm.add_custom_button('View Candidate Portal', function() {
        const applicant = frm.doc.job_applicant
        const offer_name = frm.doc.name
        frappe.db.get_value("Candidate Portal", { applicant_email: applicant, job_offer:offer_name}, "name")
        .then(r => {
            if (r.message && r.message.name) {
                frappe.set_route("Form", "Candidate Portal", r.message.name);
            } else {
                frappe.msgprint("No Candidate Portal Found.");
            }
        });
    })
}

// ? FUNCTION TO ADD UPDATE CANDIDATE PORTAL BUTTON
function updateCandidatePortal(frm) {
    frm.add_custom_button(__('Update Candidate Portal'), function () {
        frappe.call({
            method: "prompt_hr.py.job_offer.sync_candidate_portal_from_job_offer",
            args: { job_offer: frm.doc.name },
            callback: function (r) {
                frappe.msgprint({
                    title: r.message ? "Success" : "Error",
                    message: r.message ? "Candidate Portal Updated Successfully!" : "Failed to Update Candidate Portal.",
                    indicator: r.message ? "green" : "red"
                });
                frm.reload_doc();
            }
        });
    }, 'Candidate Portal');
}

// ? FUNCTION TO ADD ACCEPT CHANGES BUTTON
function acceptChangesButton(frm) {
    frm.add_custom_button(__('Accept Changes'), function () {
        frappe.call({
            method: "prompt_hr.py.job_offer.accept_changes",
            args: {
                job_offer: frm.doc.name,
                custom_candidate_date_of_joining: frm.doc.custom_candidate_date_of_joining,
                custom_candidate_offer_acceptance: frm.doc.custom_candidate_offer_acceptance,
                custom_candidate_condition_for_offer_acceptance: frm.doc.custom_candidate_condition_for_offer_acceptance,
            },
            callback: function (r) {
                frappe.msgprint({
                    title: r.message ? "Success" : "Error",
                    message: r.message ? "Changes Updated Successfully!" : "Failed to Update Changes.",
                    indicator: r.message ? "green" : "red"
                });
                frm.reload_doc();
            }
        });
    }, 'Candidate Portal');
}

// ? FUNCTION TO RELEASE OR RESEND OFFER LETTER TO CANDIDATE
function release_offer_letter(frm, is_resend = false) {

    // ? CHOOSE NOTIFICATION TEMPLATE BASED ON ACTION
    const notification_name = is_resend ? "Resend Job Offer" : "Job Application";

    // ? MAKE BACKEND CALL TO RELEASE OFFER
    frappe.call({
        method: "prompt_hr.py.job_offer.release_offer_letter",
        args: {
            doctype: frm.doctype,
            docname: frm.doc.name,
            is_resend,
            notification_name
        },
        callback: function (r) {
            console.log(r)
            if (r.exc || r.message?.status === "error") {
                frappe.msgprint({
                    title: "Error",
                    message: r.message?.message || "⚠️ Something went wrong while processing the offer.",
                    indicator: "red"
                });
                return;
            }

            

            // ? MARK AS SENT ONLY IF IT’S A FIRST-TIME RELEASE
            if (!is_resend) {
                frm.set_value("custom_offer_letter_sent", 1).then(() => {
                    frm.save_or_update();
                });
            }

            frappe.show_alert({
            message: 'Offer Letter sent successfully!',
            indicator: 'green'
            }, 5);
            
        },
        error: function (err) {
            frappe.msgprint({
                title: "Server Error",
                message: "Could not complete the request. Please try again.",
                indicator: "red"
            });
            console.error("Error releasing/resending offer letter:", err);
        }
    });
}


// ? CREATE INVITE FOR DOCUMENT COLLECTION BUTTON
function createInviteButton(frm) {
    frm.add_custom_button(__('Invite for Document Collection'), function () {
        let dialog = new frappe.ui.Dialog({
            title: 'Invite for Document Collection',
            fields: [
                {
                    label: 'Joining Document Checklist',
                    fieldname: 'joining_document_checklist',
                    fieldtype: 'Link',
                    options: 'Joining Document Checklist',
                    reqd: 1,
                    onchange: function() {
                        if (dialog.get_value('joining_document_checklist')) {
                            dialog.set_df_property('documents', 'data', []);
                            frappe.call({
                                method: "prompt_hr.py.utils.get_checklist_documents",
                                args: {
                                    checklist: dialog.get_value('joining_document_checklist')
                                },
                                callback: function(r) {
                                    frappe.hide_progress();
                                    if (r.exc) {
                                        frappe.msgprint({
                                            title: __("Error"),
                                            message: __("Error fetching documents: ") + r.exc,
                                            indicator: "red"
                                        });
                                        return;
                                    }
                                    if (r.message && r.message.documents) {
                                        let documents = r.message.documents;
                                        if (!documents.length) {
                                            frappe.msgprint({
                                                title: __("Info"),
                                                message: __("No documents found in the selected checklist."),
                                                indicator: "blue"
                                            });
                                            return;
                                        }
                                        dialog.fields[3].data = documents;
                                        dialog.fields_dict.documents.grid.refresh();
                                    } else {
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
                    onchange: function() {
                        let stage = dialog.get_value('document_collection_stage');
                        if (stage) {
                            let documents = dialog.fields[3].data;
                            let newDocuments = documents.filter(doc => doc.document_collection_stage == stage);
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
                if (!dialog.fields_dict.documents.grid.grid_rows || !dialog.fields_dict.documents.grid.grid_rows.length) {
                    frappe.msgprint({
                        title: __("Warning"),
                        message: __("No documents selected for collection. Please select a valid checklist."),
                        indicator: "yellow"
                    });
                    return;
                }

                dialog.hide();
                let selected_documents = [];
                dialog.fields_dict.documents.grid.grid_rows.forEach(row => {
                    if (row && row.doc) {
                        selected_documents.push({
                            required_document: row.doc.required_document,
                            document_collection_stage: row.doc.document_collection_stage
                        });
                    }
                });

                frappe.call({
                    method: "prompt_hr.py.utils.invite_for_document_collection",
                    args: {
                        args: {
                            name: frm.doc.job_applicant,
                            joining_document_checklist: values.joining_document_checklist,
                            document_collection_stage: values.document_collection_stage,
                            documents: selected_documents
                        },
                        joining_document_checklist: values.joining_document_checklist,
                        document_collection_stage: values.document_collection_stage,
                        documents: selected_documents,
                        child_table_fieldname: "documents"
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
                                message: __("Oops! Something went wrong while sending the invite."),
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
    }, 'Candidate Portal');
}

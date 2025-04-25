

frappe.ui.form.on('Job Offer', {
    // ? MAIN ENTRY POINT — EXECUTES ON FORM REFRESH
    refresh: function (frm) {
        const is_candidate = frappe.session.user === "candidate@sanskartechnolab.com";

        if (is_candidate) {
            handle_candidate_access(frm);
        } else if (frappe.user_roles.includes("HR Manager")) {
            add_release_offer_button(frm);
        }

        // ? CREATE INVITE BUTTON FOR DOCUMENT COLLECTION
        createInviteButton(frm);

        // ? ADD UPDATE CANDIDATE PORTAL BUTTON AND FUNCTIONALITY
        updateCandidatePortal(frm);

        // ? ADD ACCEPT CHANGES BUTTON
        acceptChangesButton(frm);
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
    });
}

// ? FUNCTION TO ADD UPDATE CANDIDATE PORTAL BUTTON AND FUNCTIONALITY
function updateCandidatePortal(frm) {
    frm.add_custom_button(__('Update Candidate Portal'), function () {
        frappe.call({
            method: "prompt_hr.py.job_offer.sync_candidate_portal_from_job_offer",
            args: {
                job_offer: frm.doc.name
            },
            callback: function (r) {
                if (r.message) {
                    frappe.msgprint({
                        title: "Success",
                        message: "Candidate Portal Updated  Successfully!",
                        indicator: "green"
                    });
                } else {
                    frappe.msgprint({
                        title: "Error",
                        message: "Failed to Update Candidate Portal.",
                        indicator: "red"
                    });
                }

                frm.reload_doc();
            }
        });
    });
}

// ? FUNCTION TO ADD UPDATE CANDIDATE PORTAL BUTTON AND FUNCTIONALITY
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
                if (r.message) {
                    frappe.msgprint({
                        title: "Success",
                        message: "Changes Updated Successfully!",
                        indicator: "green"
                    });
                } else {
                    frappe.msgprint({
                        title: "Error",
                        message: "Failed to Update Changes.",
                        indicator: "red"
                    });
                }
                frm.reload_doc();
            }
        });
    });
}

// ? CALL BACKEND TO RELEASE OR RESEND OFFER LETTER
function release_offer_letter(frm, is_resend) {

    let notification_name = "Job Application"

    if (is_resend) {
        notification_name = "Resend Job Offer"
    }

    frappe.call({
        method: "prompt_hr.py.job_offer.release_offer_letter",
        args: {
            doctype: frm.doctype,
            docname: frm.doc.name,
            is_resend: is_resend,
            notification_name: notification_name
        },
        callback: function (r) {
            if (r.exc) {
                frappe.msgprint({
                    title: "Error",
                    message: "⚠️ Something went wrong while processing the offer.",
                    indicator: "red"
                });
                return;
            }

            // ? UPDATE FLAG IF FIRST TIME
            if (!is_resend) {
                frm.set_value("custom_offer_letter_sent", 1).then(() => {
                    frm.save_or_update();
                });
            }

            frappe.msgprint({
                title: "Success",
                message: `Offer Letter ${is_resend ? "Resent" : "Released"}!`,
                indicator: "green"
            });

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
                    onchange: function() {
                        // ? FETCH DOCUMENTS FROM THE SELECTED CHECKLIST USING A CUSTOM METHOD
                        if (dialog.get_value('joining_document_checklist')) {
                            dialog.set_df_property('documents', 'data', []);
                            
                            frappe.call({
                                method: "prompt_hr.py.utils.get_checklist_documents",
                                args: {
                                    checklist: dialog.get_value('joining_document_checklist')
                                },
                                callback: function(r) {
                                    // ? HIDE LOADING INDICATOR
                                    frappe.hide_progress();
                                    
                                    // ? DEBUG RESPONSE
                                    console.log("API Response:", r);
                                    
                                    // ? CHECK FOR ERROR IN RESPONSE
                                    if (r.exc) {
                                        frappe.msgprint({
                                            title: __("Error"),
                                            message: __("Error fetching documents: ") + r.exc,
                                            indicator: "red"
                                        });
                                        return;
                                    }
                                    
                                    // ? VALIDATE DOCUMENTS DATA
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
                                        
                                        // ? UPDATE THE DATA FOR THE DOCUMENTS FIELD
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
                    onchange: function() {
                        // ? UPDATE ALL ROWS WITH THE SELECTED STAGE
                        let stage = dialog.get_value('document_collection_stage');
                        if (stage) {
                            
                            let documents = dialog.fields[3].data
                            let newDocuments = documents.filter(doc => {
                                return doc.document_collection_stage == stage;
                            });
                            
                            console.log("Filtered documents:", newDocuments);

                            // ? UPDATE THE DATA FOR THE DOCUMENTS FIELD
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

                // ? VALIDATE THAT WE HAVE DOCUMENTS
                if (!dialog.fields_dict.documents.grid.grid_rows || !dialog.fields_dict.documents.grid.grid_rows.length) {
                    frappe.msgprint({
                        title: __("Warning"),
                        message: __("No documents selected for collection. Please select a valid checklist."),
                        indicator: "yellow"
                    });
                    return;
                }
                
                dialog.hide();
                
                // ? GET SELECTED DOCUMENTS FROM THE CHILD TABLE
                let selected_documents = [];
                dialog.fields_dict.documents.grid.grid_rows.forEach(row => {
                    if (row && row.doc) {
                        selected_documents.push({
                            required_document: row.doc.required_document,
                            document_collection_stage: row.doc.document_collection_stage
                        });
                    }
                });
                
                console.log("Selected documents:", selected_documents);
                
                // ? TRIGGER BACKEND METHOD WITH EXTRA INFO
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
                        documents: selected_documents
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
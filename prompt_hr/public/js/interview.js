const original_add_custom_buttons = frappe.ui.form.handlers.Interview?.add_custom_buttons;
const original_submit_feedback = frappe.ui.form.handlers.Interview?.submit_feedback;
frappe.ui.form.off("Interview", "submit_feedback")
frappe.ui.form.on("Interview", {
    refresh: function (frm) {
        
        // ?  FETCH AVAILABLE INTERVIEWERS ON REFRESH
        fetchAvailableInterviewers(frm);

        // ?  TOGGLE DISPLAY OF CUSTOM_AVAILABLE_INTERVIEWERS FIELD ONLY IF THE FORM IS NEW
        frm.toggle_display("custom_available_interviewers", frm.is_new());

        if (frm.is_new()) {
            return;
        }

        if (frm.doc.status == "Cleared") {

            createInviteButton(frm);
        }
        // ?  ADD "NOTIFY INTERVIEWER" BUTTON
        frm.add_custom_button(__("Notify Interviewer"), function () {
            frappe.dom.freeze(__('Notifying Interviewers...'));
            frappe.call({
                method: "prompt_hr.py.interview_availability.send_interview_schedule_notification",
                args: {
                    name: frm.doc.name,
                    applicant_name: frm.doc.job_applicant,
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frm.reload_doc();
                    }
                },
                always: function () {
                    // ?  REMOVE THE FREEZE AFTER CALL IS DONE
                    frappe.dom.unfreeze();
                }
            });
        }).removeClass('btn-default').addClass('btn btn-primary btn-sm primary-action');


        // ?  CHECK IF CURRENT USER HAS SHARED ACCESS TO THIS DOCUMENT
        frappe.call({
            method: "frappe.share.get_users",
            args: {
                doctype: frm.doctype,
                name: frm.doc.name
            },
            callback: function (r) {
                if (r.message && r.message.some(function (shared_user) {
                    return shared_user.user === frappe.session.user;
                })) {
                    // ?  FIRST CHECK IF THE USER EXISTS IN INTERVIEW_DETAILS
                    let current_user = frappe.session.user;
                    let is_internal_interviewer_not_confirmed = false;
                    let is_external_interviewer_not_confirmed = false;
                    // ?  CHECK INTERNAL INTERVIEWERS
                    if (frm.doc.interview_details && frm.doc.interview_details.length) {
                        frm.doc.interview_details.forEach(function(interviewer) {
                            if (interviewer.custom_interviewer_employee) {
                                if (interviewer.custom_is_confirm === 0) {
                                    frappe.call({
                                        method: "prompt_hr.py.interview_availability.get_employee_user_id",
                                        args: {
                                            employee_id: interviewer.custom_interviewer_employee
                                        },
                                        callback: function (r) {
                                            if (r.message === current_user) {
                                                frm.remove_custom_button(__("Notify Interviewer"));
                                                is_internal_interviewer_not_confirmed = true;
                                                showConfirmButton();
                                            }
                                        }
                                    });
                                }
                                else {
                                    frappe.call({
                                        method: "prompt_hr.py.interview_availability.get_employee_user_id",
                                        args: {
                                            employee_id: interviewer.custom_interviewer_employee
                                        },
                                        callback: function (r) {
                                            if (r.message === current_user) {
                                                frm.remove_custom_button(__("Notify Interviewer"));
                                            }
                                        }
                                    });
                                }
                            }
                        });
                    }

                    // ?  CHECK EXTERNAL INTERVIEWERS
                    if (frm.doc.custom_external_interviewers && frm.doc.custom_external_interviewers.length) {
                        console.log("External Interviewers:", frm.doc.custom_external_interviewers);
                        frm.doc.custom_external_interviewers.forEach(function (interviewer) {
                            if (interviewer.user) {
                                if (interviewer.is_confirm === 0) {
                                    frappe.call({
                                        method: "prompt_hr.py.interview_availability.get_supplier_custom_user",
                                        args: {
                                            supplier_name: interviewer.user
                                        },
                                        callback: function (r) {
                                            if (r.message === current_user) {
                                                frm.remove_custom_button(__("Notify Interviewer"));
                                                console.log("External Interviewer:", interviewer.user);
                                                is_external_interviewer_not_confirmed = true;
                                                showConfirmButton();
                                            }
                                        }
                                    });
                                }
                                else {
                                    frappe.call({
                                        method: "prompt_hr.py.interview_availability.get_supplier_custom_user",
                                        args: {
                                            supplier_name: interviewer.user
                                        },
                                        callback: function (r) {
                                            console.log(r)
                                            if (r.message === current_user) {
                                                frm.remove_custom_button(__("Notify Interviewer"));
                                            }
                                        }
                                    });
                                }

                            }

                        });
                    }

                    function showConfirmButton() {
                        if (!frm.custom_button_added) {
                            frm.custom_button_added = true;
                            frm.add_custom_button(__("Confirm"), function () {
                                frappe.dom.freeze(__('Confirming Your Availability...'));
                                frappe.call({
                                    method: "prompt_hr.py.interview_availability.send_notification_to_hr_manager",
                                    args: {
                                        name: frm.doc.name,
                                        company: frm.doc.custom_company,
                                        user: frappe.session.user
                                    },
                                    callback: function (res) {
                                        frappe.msgprint(res.message || __("Your availability has been confirmed."));
                                        // ?  RELOAD THE FORM TO REFLECT CHANGES
                                        frm.reload_doc();
                                    }
                                });
                            }).removeClass('btn-default').addClass('btn btn-primary btn-sm primary-action');
                        }
                    }
                }
            },
            always: function () {
                // ?  REMOVE THE FREEZE AFTER CALL IS DONE
                frappe.dom.unfreeze();
            }
        });
    },
    add_custom_buttons: async function (frm) {
        // ?  CALL THE ORIGINAL FUNCTION IF IT EXISTS
        if (typeof original_add_custom_buttons === "function") {
            await original_add_custom_buttons(frm);
        }

        // ?  SKIP IF DOC IS CANCELED OR NOT SAVED
        if (frm.doc.docstatus === 2 || frm.doc.__islocal) return;

        // ?  CHECK IF FEEDBACK ALREADY SUBMITTED
        const has_submitted_feedback = await frappe.db.get_value(
            "Interview Feedback",
            {
                interviewer: frappe.session.user,
                interview: frm.doc.name,
                docstatus: ["!=", 2],
            },
            "name"
        )?.message?.name;

        if (has_submitted_feedback) return;

        // ?  CHECK INTERNAL INTERVIEWERS
        let allow_internal = false;
        for (const interviewer of frm.doc.interview_details || []) {
            if (interviewer.custom_interviewer_employee) {
                const r = await frappe.call({
                    method: "prompt_hr.py.interview_availability.get_employee_user_id",
                    args: { employee_id: interviewer.custom_interviewer_employee },
                });
                if (r?.message === frappe.session.user) {
                    allow_internal = true;
                    break;
                }
            }
        }

        // ?  Check external interviewers
        let allow_external = false;
        for (const ext of frm.doc.custom_external_interviewers || []) {
            if (ext.user) {
                const r = await frappe.call({
                    method: "prompt_hr.py.interview_availability.get_supplier_custom_user",
                    args: { supplier_name: ext.user },
                });
                if (r?.message === frappe.session.user) {
                    allow_external = true;
                    break;
                }
            }
        }
        if (allow_internal || allow_external) {
            // ?  ENABLE "SUBMIT FEEDBACK" BUTTONS
            frappe.after_ajax(() => {
                setTimeout(() => {
                    $('button').filter(function () {
                        return $(this).text().trim() === "Submit Feedback";
                    }).each(function () {
                        $(this)
                            .prop("disabled", false)
                            .removeAttr("title")
                            .removeAttr("data-original-title")
                            .tooltip('dispose');
                    });
                }, 100);
            });
        }
    },
    submit_feedback: async function (frm) {
        frappe.call({
            method: "prompt_hr.py.interview_availability.submit_feedback",
            args: {
                doc_name: frm.doc.name,
                interview_round: frm.doc.interview_round,
                job_applicant: frm.doc.job_applicant,
                custom_company: frm.doc.custom_company
            },
            callback: function (r) {
                if (r.message) {
                    console.log("Feedback submitted successfully.");
                    window.location.href = r.message;
                } else {
                    frappe.call({
                        method: "hrms.hr.doctype.interview.interview.get_expected_skill_set",
                        args: {
                            interview_round: frm.doc.interview_round,
                        },
                        callback: function (r) {
                            frm.events.show_feedback_dialog(frm, r.message);
                            frm.refresh();
                        },
                    });
                }
            }
        });
    },
    scheduled_on: function (frm) {
        updateInterviewerAvailability(frm);
    },

    from_time: function (frm) {
        updateInterviewerAvailability(frm)
    },

    to_time: function (frm) {
        updateInterviewerAvailability(frm)
    },

    after_save: function (frm) {
        // ? HIDE THE AVAILABLE INTERVIEWERS FIELD AFTER SAVING
        frm.toggle_display("custom_available_interviewers", false);
    }
});



// ? FUNCTION TO FETCH AVAILABLE INTERVIEWERS AND UPDATE ONLY NEW ONES
function fetchAvailableInterviewers(frm) {
    if (!frm.doc.scheduled_on || !frm.doc.from_time || !frm.doc.to_time || !frm.doc.designation) {
        frm.clear_table("custom_available_interviewers");
        frm.refresh_field("custom_available_interviewers");
        return;
    }

    frappe.call({
        method: "prompt_hr.prompt_hr.doctype.interview_availability_form.interview_availability_form.fetch_latest_availability",
        args: {
            'param_date': frm.doc.scheduled_on,
            'param_from_time': frm.doc.from_time,
            'param_to_time': frm.doc.to_time,
            'designation': frm.doc.designation
        },
        callback: function (r) {
            if (r.message) {
                let availableInterviewers = r.message.record || [];

                // ? GET EXISTING INTERVIEWERS (NO NEED TO JOIN FOR COMPARISON)
                let existingInterviewers = frm.doc.custom_available_interviewers || [];

                // ? FILTER NEW INTERVIEWERS (AVOID DUPLICATES)
                let newInterviewers = availableInterviewers.filter(user =>
                    !existingInterviewers.some(row => row.user === user)
                );

                // ? APPEND ONLY NEW INTERVIEWERS
                if (newInterviewers.length > 0) {
                    // ? APPEND ONLY NEW INTERVIEWERS
                    if (newInterviewers.length > 0) {
                        newInterviewers.forEach(interviewer => {
                            let row = frm.add_child("custom_available_interviewers");
                            row.user = interviewer; 
                            console.log("New Interviewer:", row.user);
                        });

                        frm.refresh_field("custom_available_interviewers");

                        // ? APPLY FORMATTING IN UI
                        setTimeout(() => {
                            let formattedInterviewers = (frm.doc.custom_available_interviewers || [])
                                .map(row => row.user)
                                .join('<br>'); 

                            $(".control-value[data-fieldname='custom_available_interviewers']").html(formattedInterviewers);
                        }, 100);
                    }

                }

            }
        }
    });
}

// ? FUNCTION TO UPDATE INTERVIEWER AVAILABILITY
function updateInterviewerAvailability(frm) {
    fetchAvailableInterviewers(frm);
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

                            console.log("Filtered documents:", newDocuments);

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
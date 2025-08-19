frappe.ui.form.on('Job Applicant', {
    refresh: function (frm) {

        // ? CREATE INVITE FOR DOCUMENT COLLECTION BUTTON
        createInviteButton(frm);

        // ? ADD CUSTOM BUTTON TO INVITE OR RE-INVITE FOR SCREEN TEST
        screenInviteButton(frm);

        // ? ADD CUSTOM BUTTTON TO SEND EMAIL FOR REJECTION AND ON HOLD
        sendEmailButton(frm);
    }
});

// ? FUNCTION TO ADD CUSTOM BUTTON

function sendEmailButton(frm){
        // Add dropdown for email actions
        frm.add_custom_button('Send Rejection Email', function() {
            frappe.call({
                method: 'prompt_hr.py.job_applicant.send_rejection_notification',
                args: { job_applicant: frm.doc.name }
            });
        }, "Send Email");
        
        frm.add_custom_button('Send On Hold Email', function() {
            frappe.call({
                method: 'prompt_hr.py.job_applicant.send_on_hold_notification',
                args: { job_applicant: frm.doc.name }
            });
        }, "Send Email");
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
                        // Fetch documents from the selected checklist using a custom method
                        if (dialog.get_value('joining_document_checklist')) {
                            dialog.set_df_property('documents', 'data', []); // Clear existing data

                            frappe.call({
                                method: "prompt_hr.py.utils.get_checklist_documents",
                                args: {
                                    checklist: dialog.get_value('joining_document_checklist')
                                },
                                callback: function (r) {
                                    // HIDE LOADING INDICATOR
                                    frappe.hide_progress();

                                    // CHECK FOR ERROR IN RESPONSE
                                    if (r.exc) {
                                        frappe.msgprint({
                                            title: __("Error"),
                                            message: __("Error fetching documents: ") + r.exc,
                                            indicator: "red"
                                        });
                                        return;
                                    }

                                    // VALIDATE DOCUMENTS DATA
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

                                        // UPDATE THE DATA FOR THE DOCUMENTS FIELD
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

                            // UPDATE THE DATA FOR THE DOCUMENTS FIELD
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

                // VALIDATE THAT WE HAVE DOCUMENTS
                if (!dialog.fields_dict.documents.grid.grid_rows || !dialog.fields_dict.documents.grid.grid_rows.length) {
                    frappe.msgprint({
                        title: __("Warning"),
                        message: __("No documents selected for collection. Please select a valid checklist."),
                        indicator: "yellow"
                    });
                    return;
                }

                dialog.hide();

                // GET SELECTED DOCUMENTS FROM THE CHILD TABLE
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
                            name: frm.doc.name,
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

// ? FUNCTION TO ADD CUSTOM BUTTON TO INVITE OR RE-INVITE FOR SCREEN TEST
function screenInviteButton(frm) {

    frm.add_custom_button(
        frm.doc.custom_active_quiz === 1 ? 'Invite for Repeat Screen Test' : 'Invite for Screen Test',
        () => {

            // ? VALIDATE IF JOB OPENING IS LINKED
            if (!frm.doc.job_title) {
                frappe.msgprint(__('No Job Opening linked.'));
                return;
            }

            // ? CALL SERVER METHOD TO CHECK TEST AND INVITE
            frappe.call({
                method: "prompt_hr.py.job_applicant.check_test_and_invite",
                args: {
                    job_applicant: frm.doc.name
                },
                callback: function (r) {
                    console.log(r)
                    // ? IF NO ERROR RETURNED
                    if (!r.message?.error) {

                        // ? RESET ACTIVE QUIZ IF IT WAS A REPEAT INVITE
                        if (frm.doc.custom_active_quiz === 1) {
                            frappe.db.set_value("Job Applicant", frm.doc.name, "custom_active_quiz", 0);
                        }

                        // ? IF TEST INVITATION SENT
                        if (r.message.message === "invited") {
                            frappe.msgprint("Screening Test invitation sent successfully.");

                            // ? IF QUIZ TEMPLATE IS MISSING, REDIRECT TO JOB OPENING
                        } else if (r.message.message === "redirect") {
                            frappe.set_route("Form", "Job Opening", frm.doc.job_title);
                            frappe.msgprint("Please create a Screening Test for the job opening before inviting the applicant.");

                            // ? SCROLL TO SCREENING TEST FIELD
                            frappe.after_ajax(() => {
                                setTimeout(() => {
                                    let fieldname = 'custom_applicable_screening_test';
                                    if (cur_frm?.doc.doctype === 'Job Opening') {
                                        let $field = cur_frm.fields_dict[fieldname]?.$wrapper;
                                        if ($field) frappe.utils.scroll_to($field);
                                    }
                                }, 600);
                            });
                        }

                        // ? HANDLE ERROR RESPONSE
                    } else {
                        frappe.throw(r.message.message);
                    }
                }
            });
        }
    );

}




frappe.ui.form.on('Job Applicant', {
    refresh: function(frm) {
        frm.add_custom_button(__('Resume Parsing'), function() {
            if (!frm.doc.job_title || !frm.doc.designation) {
                frappe.msgprint(__('Please first select Job Opening and Designation before parsing the resume.'));
                return;
            }

            // Open file upload dialog
            let dialog = new frappe.ui.Dialog({
                title: __('Upload Resume'),
                fields: [
                    {
                        label: 'Upload File',
                        fieldname: 'resume_file',
                        fieldtype: 'Attach',
                        reqd: true
                    }
                ],
                primary_action_label: __('Parse Resume'),
                primary_action(values) {
                    if (!values.resume_file) {
                        frappe.msgprint(__('Please upload a resume file.'));
                        return;
                    }

                    frm.set_value('resume_attachment', values.resume_file);

                    frappe.call({
                        method: "prompt_hr.api.resume_parsing.parse_resume",
                        args: {
                            file_url: values.resume_file
                        },
                        callback: function(r) {
                            if (r.message && r.message.length > 0) {
                                console.log(r.message);
                                var resume_data = r.message[0];
                                var missing_fields = [];
                        
        
                                frm.set_value("applicant_name", resume_data.raw_name || "");
                                if (!resume_data.raw_name) missing_fields.push("Applicant Name");
                        
                                // frm.set_value("designation", resume_data.profession || "");
                                // if (!resume_data.profession) missing_fields.push("Designation");
                        
                                frm.set_value("custom_date_of_birth", resume_data.date_of_birth || "");
                                if (!resume_data.date_of_birth) missing_fields.push("Date of Birth");
                        
                                frm.set_value("email_id", resume_data.email || "");
                                if (!resume_data.email) missing_fields.push("Email");
                        
                                frm.set_value("phone_number", resume_data.phone_number || "");
                                if (!resume_data.phone_number) missing_fields.push("Phone Number");
                        
                                frm.set_value("country", resume_data.country || "");
                                if (!resume_data.country) missing_fields.push("Country");
                        
                                frm.set_value("custom_gender", resume_data.gender || "");
                                if (!resume_data.gender) missing_fields.push("Gender");
                        
                                // frm.set_value("custom_experience", resume_data.total_years_experience || 0);
                                // if (resume_data.total_years_experience === null || resume_data.total_years_experience === undefined) {
                                //     missing_fields.push("Total Experience");
                                // }
                        
                                frm.set_value("custom_key_skills", resume_data.skills ? resume_data.skills.join(", ") : "");
                                if (!resume_data.skills) missing_fields.push("Key Skills");
        
                                frm.set_value("custom_address", resume_data.address || "");
                                frm.set_value("lower_range", resume_data.current_salary || "");
                                frm.set_value("upper_range", resume_data.expected_salary || "");
        
                                frm.clear_table("custom_education_details_table");
                                frm.clear_table("custom_experience_table");
                        
                                
                                if (resume_data.education && resume_data.education.length > 0) {
                                    resume_data.education.forEach(function(edu) {
                                        var child = frm.add_child("custom_education_details_table");
                                        if (edu.university) {
                                            child.custom_university_board = edu.university;
                                        } else if (edu.school) {
                                            child.school_univ = edu.school;
                                        } else {
                                            child.custom_university_board = edu.organization;
                                        }
                        
                                        child.level = edu.level || (edu.school ? "Under Graduate" : "");
                                        child.qualification = edu.education;
                                        child.year_of_passing = edu.dates_rawText;
                                        child.class_per = edu.grade_raw;
                                        child.maj_opt_subj = edu.matchStr;
                                    });
                                } else {
                                    missing_fields.push("Education Details");
                                }
                        
                                
                                if (resume_data.work_experience && resume_data.work_experience.length > 0) {
                                    resume_data.work_experience.forEach(function(exp) {
                                        var child = frm.add_child("custom_experience_table");
                                        child.company_name = exp.organization;
                                        child.designation = exp.job_title;
                                        // child.address = exp.location_formatted;
                                        child.total_experience = exp.months_in_position;
                                        child.custom_working_duration = exp.dates_rawText;
                                    });
                                } else {
                                    missing_fields.push("Work Experience");
                                }
                        
                                frm.refresh();
                        
                                setTimeout(() => {
                                if (missing_fields.length > 0) {
                                    frappe.msgprint({
                                        title: "Missing Data",
                                        message: "The following fields were not set and may need to be filled manually:<br><ul>" +
                                                    missing_fields.map(f => `<li>${f}</li>`).join("") + "</ul>",
                                        indicator: "orange"
                                    });
                                }
                            }, 500); 
                            }
                        },
                        
                        freeze: true,
                        freeze_message: "Please wait while we map and set resume details."
                    });

                    dialog.hide();
                }
            });

            dialog.show();
        });
    }
});

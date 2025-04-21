
frappe.ui.form.on("Interview", {
    refresh: function(frm) {
        // Fetch available interviewers on refresh
        fetchAvailableInterviewers(frm);
    
        // Toggle display of custom_available_interviewers field only if the form is new
        frm.toggle_display("custom_available_interviewers", frm.is_new());
    
        // Add "Notify Interviewer" button
        frm.add_custom_button(__("Notify Interviewer"), function() {
            frappe.dom.freeze(__('Notifying Interviewers...'));
            frappe.call({
                method: "prompt_hr.py.interview_availability.send_interview_schedule_notification",
                args: {
                    name: frm.doc.name,
                    applicant_name: frm.doc.job_applicant,
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                        frm.reload_doc();
                    }
                },
                always: function() {
                    // Remove the freeze after call is done
                    frappe.dom.unfreeze();
                }
            });
        }).removeClass('btn-default').addClass('btn btn-primary btn-sm primary-action');
        if (frm.is_new()) {
            return;
        }
        // Check if current user has shared access to this document
        frappe.call({
            method: "frappe.share.get_users",
            args: {
                doctype: frm.doctype,
                name: frm.doc.name
            },
            callback: function(r) {
                if (r.message && r.message.some(function(shared_user) {
                    return shared_user.user === frappe.session.user;
                })) {
                    // First check if the user exists in interview_details
                    let current_user = frappe.session.user;
                    let is_internal_interviewer_not_confirmed = false;
                    let is_external_interviewer_not_confirmed = false;
                    // Check internal interviewers
                    if (frm.doc.interview_details && frm.doc.interview_details.length) {
                        frm.doc.interview_details.forEach(function(interviewer) {
                            if (interviewer.custom_interviewer_employee && interviewer.custom_is_confirm === 0) {
                                // Get the user_id for this employee
                                frappe.db.get_value("Employee", interviewer.custom_interviewer_employee, "user_id", function(r) {
                                    if (r && r.user_id === current_user) {
                                        is_internal_interviewer_not_confirmed = true;
                                        showConfirmButton();
                                    }
                                });
                            }
                        });
                    }
                    
                    // Check external interviewers
                    if (frm.doc.custom_external_interviewers && frm.doc.custom_external_interviewers.length) {
                        console.log("External Interviewers:", frm.doc.custom_external_interviewers);
                        frm.doc.custom_external_interviewers.forEach(function(interviewer) {
                            if (interviewer.user && interviewer.is_confirm === 0) {
                                frappe.call({
                                    method: "prompt_hr.py.interview_availability.get_supplier_custom_user",
                                    args: {
                                        supplier_name: interviewer.user
                                    },
                                    callback: function (r) {
                                        if (r.message === frappe.session.user) {
                                            console.log("External Interviewer:", interviewer.user);
                                            is_external_interviewer_not_confirmed = true;
                                            showConfirmButton();
                                        }
                                    }
                                });
                            }
                        });
                    }
                    
                    function showConfirmButton() {
                        if (!frm.custom_button_added) {
                            frm.custom_button_added = true;
                            frm.add_custom_button(__("Confirm"), function() {
                                frappe.dom.freeze(__('Confirming Your Availability...'));
                                frappe.call({
                                    method: "prompt_hr.py.interview_availability.send_notification_to_hr_manager",
                                    args: {
                                        name: frm.doc.name,
                                        company: frm.doc.custom_company,
                                        user: frappe.session.user
                                    },
                                    callback: function(res) {
                                        frappe.msgprint(res.message || __("Your availability has been confirmed."));
                                        // Reload the form to reflect changes
                                        frm.reload_doc();
                                    }
                                });
                            }).removeClass('btn-default').addClass('btn btn-primary btn-sm primary-action');
                        }
                    }
                }
            },
            always: function () {
                // Remove the freeze after call is done
                frappe.dom.unfreeze();
            }
        });
    },
    
    scheduled_on: function(frm) {
        updateInterviewerAvailability(frm);
    },

    from_time: function(frm) {
        updateInterviewerAvailability(frm)
    },

    to_time: function(frm) {
        updateInterviewerAvailability(frm)
    },

    after_save: function(frm) {
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
        callback: function(r) {
            if (r.message) {
                let availableInterviewers = r.message.record || [];
                console.log("Fetched Interviewers:", availableInterviewers);
                
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
                            row.user = interviewer;  // Store plain text (no <br>)
                            console.log("New Interviewer:", row.user);
                        });

                        frm.refresh_field("custom_available_interviewers");

                        // ? APPLY FORMATTING IN UI
                        setTimeout(() => {
                            let formattedInterviewers = (frm.doc.custom_available_interviewers || [])
                                .map(row => row.user)
                                .join('<br>'); // Add HTML line break

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


const original_add_custom_buttons = frappe.ui.form.handlers.Interview?.add_custom_buttons;
const original_submit_feedback = frappe.ui.form.handlers.Interview?.submit_feedback;
frappe.ui.form.off("Interview", "submit_feedback")
frappe.ui.form.on("Interview", {
    refresh: function(frm) {
        // Fetch available interviewers on refresh
        fetchAvailableInterviewers(frm);
    
        // Toggle display of custom_available_interviewers field only if the form is new
        frm.toggle_display("custom_available_interviewers", frm.is_new());
        if (frm.is_new()) {
            return;
        }
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
                            console.log("Internal Interviewers:", interviewer.custom_interviewer_employee);
                            if (interviewer.custom_interviewer_employee) {
                                if (interviewer.custom_is_confirm === 0 ) {
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
                    
                    // Check external interviewers
                    if (frm.doc.custom_external_interviewers && frm.doc.custom_external_interviewers.length) {
                        console.log("External Interviewers:", frm.doc.custom_external_interviewers);
                        frm.doc.custom_external_interviewers.forEach(function(interviewer) {
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
                                else{
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
    add_custom_buttons: async function(frm) {
        // Call the original function if it exists
        if (typeof original_add_custom_buttons === "function") {
            await original_add_custom_buttons(frm);
        }
    
        // Skip if doc is canceled or not saved
        if (frm.doc.docstatus === 2 || frm.doc.__islocal) return;
    
        // Check if feedback already submitted
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
    
        // Check internal interviewers
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
    
        // Check external interviewers
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
            // Enable "Submit Feedback" buttons
            frappe.after_ajax(() => {
                setTimeout(() => {
                    $('button').filter(function() {
                        return $(this).text().trim() === "Submit Feedback";
                    }).each(function() {
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
            callback: function(r) {
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


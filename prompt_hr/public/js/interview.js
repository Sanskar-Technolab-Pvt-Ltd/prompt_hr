
frappe.ui.form.on("Interview", {
    refresh: function(frm) {

        // ? ? FETCH AVAILABLE INTERVIEWERS ON REFRESH
        fetchAvailableInterviewers(frm);
        frm.toggle_display("custom_available_interviewers", frm.is_new());

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
        method: "prompt_hr.prompt_hr.doctype.interview_availabilty_form.interview_availabilty_form.fetch_latest_availability",
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


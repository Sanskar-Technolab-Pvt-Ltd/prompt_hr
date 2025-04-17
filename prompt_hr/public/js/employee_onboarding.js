frappe.ui.form.on("Employee Onboarding", {
    
    // ? RUN ON FORM REFRESH
    refresh: async function (frm) {
        update_first_activity_if_needed(frm);
        let applicants = await frappe.db.get_list("Job Applicant", {
            fields: ["name"],
            or_filters: [
                ["status", "=", "Job Offer Accepted"],
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

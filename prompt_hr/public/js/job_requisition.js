frappe.ui.form.on("Job Requisition", {
    refresh(frm) {
        console.log("Job Requisition Form Refreshed");

        // ? AUTO-FILL 'REQUESTED_BY' ON NEW FORM
        if (frm.is_new()) {
            frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name")
                .then(r => {
                    if (r.message?.name) {
                        frm.set_value("requested_by", r.message.name);
                    }
                });
        }

        // ? HANDLE JOB OPENING BUTTONS IF APPROVED
        if (frm.doc.workflow_state === "Final Approval") {
            show_job_opening_buttons(frm);
        }
    }
});

// ? FUNCTION TO SHOW EITHER "CREATE" OR "VIEW" JOB OPENING BUTTONS
function show_job_opening_buttons(frm) {
    frappe.db.get_list("Job Opening", {
        filters: { custom_job_requisition_record: frm.doc.name },
        fields: ["name", "job_title"],
        limit: 100
    }).then(job_openings => {
        if (!job_openings.length) {
            // ? CREATE JOB OPENING BUTTON
            frm.add_custom_button(__("Create Job Opening"), () => {
                window.location.href = `/app/job-opening?job_requisition=${frm.doc.name}`;
            });
        } else {
            // ? VIEW JOB OPENINGS BUTTON GROUP
            const group = __("View Job Opening(s)");

            frm.add_custom_button(group, null, __("Actions"));

            job_openings.forEach(job => {
                frm.add_custom_button( job.name, () => {
                    frappe.set_route("Form", "Job Opening", job.name);
                }, group);
            });
        }
    });
}

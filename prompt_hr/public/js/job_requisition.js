frappe.ui.form.on("Job Requisition", {
    refresh: function (frm) {
        console.log("Job Requisition Form Refreshed");
        // ? FUNCTION TO ADD "CREATE JOB OPENING" BUTTON AFTER FINAL APPROVAL
        create_job_opening_button(frm);

        // ? FUNCTION TO AUTO-FILL 'REQUESTED_BY' FOR NEW REQUISITIONS
        if (frm.is_new()) {
            let current_user = frappe.session.user;

            frappe.db.get_value("Employee", { "user_id": current_user }, "name", function (r) {
                if (r && r.name) {
                    frm.set_value("requested_by", r.name);
                }
            });
        }
    }
});

// ? FUNCTION TO ADD A CUSTOM BUTTON TO REDIRECT TO EXTERNAL JOB OPENING URL
function create_job_opening_button(frm) {
    if (frm.doc.workflow_state == "Final Approval") {
        frm.add_custom_button(__("Create Job Opening"), function () {
            const base_url = frappe.urllib.get_base_url();
            const redirect_url = `${base_url}/app/job-opening/new?custom_job_requisition_record=${frm.doc.name}`;
            window.open(redirect_url, "_blank");
        });
    }
}

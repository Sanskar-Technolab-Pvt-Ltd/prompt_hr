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
        if (!frm.is_new()) {
            make_workflow_details(frm)
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
                window.location.href = `/app/job-opening/new-?custom_job_requisition_record=${frm.doc.name}`;
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

function make_workflow_details(frm) {
    if (!frm.doc.company || !frm.doc.doctype || !frm.doc.name) return;

    frappe.call({
        method: "prompt_hr.py.job_requisition.get_workflow_approvals",
        args: {
            company: frm.doc.company,
            doctype: frm.doc.doctype,
            docname: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length) {
                const data = r.message;

                // 🧱 BUILD TABLE HEADER
                let html = `
                    <table class="table table-bordered table-sm mt-2">
                        <thead style="background-color: #f8f9fa;">
                            <tr>
                                <th>State</th>
                                <th>Action</th>
                                <th>Next State</th>
                                <th>Allowed By</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                // POPULATE TABLE ROWS
                data.forEach(row => {
                    html += `
                        <tr>
                            <td>${row.state || '-'}</td>
                            <td>${row.action || '-'}</td>
                            <td>${row.next_state || '-'}</td>
                            <td>${row.allowed_by || '-'}</td>
                            <td>${row.value || '-'}</td>
                        </tr>
                    `;
                });

                html += `
                        </tbody>
                    </table>
                `;
                // SET HTML FIELD VALUE
                frm.fields_dict.custom_workflow_details.$wrapper.html(html);
            } else {
                frm.fields_dict.custom_workflow_details.$wrapper.html(
                    `<p style="color: #888; margin-top:10px;">No applicable workflow approval found.</p>`
                );
            }
        }
    });
}

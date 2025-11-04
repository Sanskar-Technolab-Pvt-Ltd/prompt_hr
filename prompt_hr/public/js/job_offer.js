

frappe.ui.form.on('Job Offer', {
    // ? MAIN ENTRY POINT — EXECUTES ON FORM REFRESH
    refresh: async function (frm) {
        const is_candidate = frappe.session.user === "candidate@promptdairytech.com";
        const hr_roles_response = await frappe.call({
            method: "prompt_hr.py.expense_claim.get_roles_from_hr_settings",
            args: { role_type: "hr" },
        });
        const hr_roles = hr_roles_response?.message || [];
        const hr_system_roles = ["System Manager", ...hr_roles];
        if (is_candidate) {
            handle_candidate_access(frm);
        } else if ((hr_system_roles || frappe.session.user == "Administrator") && frm.doc.workflow_state == "Approved") {
            // ? SHOW RELEASE JOB OFFER BUTTON ONLY TO HR ROLES
            add_release_offer_button(frm);
        }

        // ? ADD CREATE EMPLOYEE ONBOARDING BUTTON
        create_employee_onboarding_button(frm)

        // ? CREATE INVITE BUTTON FOR DOCUMENT COLLECTION
        createInviteButton(frm);

        // ? ADD UPDATE CANDIDATE PORTAL BUTTON AND FUNCTIONALITY
        updateCandidatePortal(frm);

        // ? ADD ACCEPT CHANGES BUTTON
        acceptChangesButton(frm);

        viewCandidatePortalButton(frm)

        show_salary_breakup_preview_button(frm)

        // ? ADD RELEASE LOI LETTER BUTTON
        if (frm.doc.workflow_state == "Approved") {
            frm.add_custom_button(__("Release LOI Letter"), function () {
                frappe.dom.freeze(__('Releasing Letter...'));
                frappe.call({
                    method: "prompt_hr.py.job_offer.send_LOI_letter",
                    args: { name: frm.doc.name },
                    callback: function (r) {
                        if (r.message) {
                            frappe.msgprint(r.message);
                            frm.reload_doc();
                        }
                    },
                    always: function () {
                        frappe.dom.unfreeze();
                    }
                });
            }, 'Offer Actions');
        }
        
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

async function create_employee_onboarding_button(frm) {
    if (
        frm.doc.workflow_state === "Approved" &&
        (frm.doc.status === "Accepted" || frm.doc.status === "Accepted with Condition")
    ) {

        // ✅ Check if onboarding exists
        const existing = await frappe.db.get_value(
            "Employee Onboarding",
            { job_offer: frm.doc.name },
            "name"
        );

        // ✅ Dynamic button title based on existence
        let button_label = existing?.message?.name
            ? __("View Employee Onboarding")
            : __("Create Employee Onboarding");

        frm.add_custom_button(button_label, function () {

            if (existing && existing.message && existing.message.name) {
                // ✅ Open existing onboarding
                frappe.set_route("Form", "Employee Onboarding", existing.message.name);
                return;
            }

            // ✅ Create new onboarding
            frappe.new_doc("Employee Onboarding", {
                job_offer: frm.doc.name,
                job_applicant: frm.doc.job_applicant,
                designation: frm.doc.designation,
            });
        });
    }
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
    }, 'Offer Actions');
}

function viewCandidatePortalButton(frm) {
    frm.add_custom_button('View Candidate Portal', function() {
        const applicant = frm.doc.job_applicant
        const offer_name = frm.doc.name
        frappe.db.get_value("Candidate Portal", { applicant_email: applicant, job_offer:offer_name}, "name")
        .then(r => {
            if (r.message && r.message.name) {
                frappe.set_route("Form", "Candidate Portal", r.message.name);
            } else {
                frappe.msgprint("No Candidate Portal Found.");
            }
        });
    }, 'Candidate Portal')
}

// ? FUNCTION TO ADD UPDATE CANDIDATE PORTAL BUTTON
function updateCandidatePortal(frm) {
    frm.add_custom_button(__('Update Candidate Portal'), function () {
        frappe.call({
            method: "prompt_hr.py.job_offer.sync_candidate_portal_from_job_offer",
            args: { job_offer: frm.doc.name },
            callback: function (r) {
                frappe.msgprint({
                    title: r.message ? "Success" : "Error",
                    message: r.message ? "Candidate Portal Updated Successfully!" : "Failed to Update Candidate Portal.",
                    indicator: r.message ? "green" : "red"
                });
                frm.reload_doc();
            }
        });
    }, 'Candidate Portal');
}

// ? FUNCTION TO ADD ACCEPT CHANGES BUTTON
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
                frappe.msgprint({
                    title: r.message ? "Success" : "Error",
                    message: r.message ? "Changes Updated Successfully!" : "Failed to Update Changes.",
                    indicator: r.message ? "green" : "red"
                });
                frm.reload_doc();
            }
        });
    }, 'Candidate Portal');
}

// ? FUNCTION TO RELEASE OR RESEND OFFER LETTER TO CANDIDATE
function release_offer_letter(frm, is_resend = false) {

    // ? CHOOSE NOTIFICATION TEMPLATE BASED ON ACTION
    const notification_name = is_resend ? "Resend Job Offer" : "Job Application";

    // ? MAKE BACKEND CALL TO RELEASE OFFER
    frappe.call({
        method: "prompt_hr.py.job_offer.release_offer_letter",
        args: {
            doctype: frm.doctype,
            docname: frm.doc.name,
            is_resend,
            notification_name
        },
        callback: function (r) {
            console.log(r)
            if (r.exc || r.message?.status === "error") {
                frappe.msgprint({
                    title: "Error",
                    message: r.message?.message || "⚠️ Something went wrong while processing the offer.",
                    indicator: "red"
                });
                return;
            }

            

            // ? MARK AS SENT ONLY IF IT’S A FIRST-TIME RELEASE
            if (!is_resend) {
                frm.set_value("custom_offer_letter_sent", 1).then(() => {
                    frm.save_or_update();
                });
            }

            frappe.show_alert({
            message: 'Offer Letter sent successfully!',
            indicator: 'green'
            }, 5);
            
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
                        if (dialog.get_value('joining_document_checklist')) {
                            dialog.set_df_property('documents', 'data', []);
                            frappe.call({
                                method: "prompt_hr.py.utils.get_checklist_documents",
                                args: {
                                    checklist: dialog.get_value('joining_document_checklist')
                                },
                                callback: function(r) {
                                    frappe.hide_progress();
                                    if (r.exc) {
                                        frappe.msgprint({
                                            title: __("Error"),
                                            message: __("Error fetching documents: ") + r.exc,
                                            indicator: "red"
                                        });
                                        return;
                                    }
                                    if (r.message && r.message.documents) {
                                        let documents = r.message.documents;
                                        if (!documents.length) {
                                            frappe.msgprint({
                                                title: __("Info"),
                                                message: __("No documents found in the selected checklist."),
                                                indicator: "blue"
                                            });
                                            return;
                                        }
                                        dialog.fields[3].data = documents;
                                        dialog.fields_dict.documents.grid.refresh();
                                    } else {
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
                        let stage = dialog.get_value('document_collection_stage');
                        if (stage) {
                            let documents = dialog.fields[3].data;
                            let newDocuments = documents.filter(doc => doc.document_collection_stage == stage);
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
                if (!dialog.fields_dict.documents.grid.grid_rows || !dialog.fields_dict.documents.grid.grid_rows.length) {
                    frappe.msgprint({
                        title: __("Warning"),
                        message: __("No documents selected for collection. Please select a valid checklist."),
                        indicator: "yellow"
                    });
                    return;
                }

                dialog.hide();
                let selected_documents = [];
                dialog.fields_dict.documents.grid.grid_rows.forEach(row => {
                    if (row && row.doc) {
                        selected_documents.push({
                            required_document: row.doc.required_document,
                            document_collection_stage: row.doc.document_collection_stage
                        });
                    }
                });

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
                                message: __("Oops! Something went wrong while sending the invite."),
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
    }, 'Candidate Portal');
}

function show_salary_breakup_preview_button(frm) {
    // Do not show button for new documents
    if (frm.doc.__islocal) return;

    // Avoid duplicate buttons
    frm.remove_custom_button("Preview Salary Breakup");

    // Add the button
    frm.add_custom_button(
        "Preview Salary Breakup",
        () => show_salary_breakup_preview(frm),
    );
}


function show_salary_breakup_preview(frm) {
    let earnings = frm.doc.custom_earnings || [];
    let deductions = frm.doc.custom_deductions || [];

    // Scoped CSS styles
    const styles = `
        <style>
            .salary-preview-container {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }
            
            .salary-preview-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
                margin: -15px -15px 20px -15px;
            }
            
            .salary-preview-header h3 {
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }
            
            .salary-section-card {
                background: #ffffff;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
                margin-bottom: 20px;
                overflow: hidden;
                border: 1px solid #e8e8e8;
            }
            
            .salary-section-header {
                padding: 16px 20px;
                border-bottom: 2px solid #f0f0f0;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .salary-section-header.earnings {
                background: linear-gradient(90deg, #f0fdf4 0%, #dcfce7 100%);
                border-bottom-color: #86efac;
            }
            
            .salary-section-header.deductions {
                background: linear-gradient(90deg, #fef2f2 0%, #fee2e2 100%);
                border-bottom-color: #fca5a5;
            }
            
            .salary-section-icon {
                width: 32px;
                height: 32px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
            }
            
            .salary-section-icon.earnings {
                background: #22c55e;
                color: white;
            }
            
            .salary-section-icon.deductions {
                background: #ef4444;
                color: white;
            }
            
            .salary-section-title {
                font-size: 18px;
                font-weight: 600;
                color: #1f2937;
                margin: 0;
            }
            
            .salary-preview-table {
                width: 100%;
                border-collapse: collapse;
            }
            
            .salary-preview-table thead th {
                background: #f9fafb;
                padding: 12px 20px;
                text-align: left;
                font-size: 13px;
                font-weight: 600;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 2px solid #e5e7eb;
            }
            
            .salary-preview-table thead th.salary-amount-col {
                text-align: right;
            }
            
            .salary-preview-table tbody tr {
                transition: background-color 0.2s ease;
            }
            
            .salary-preview-table tbody tr:hover {
                background: #f9fafb;
            }
            
            .salary-preview-table tbody td {
                padding: 14px 20px;
                border-bottom: 1px solid #f3f4f6;
                color: #374151;
                font-size: 14px;
            }
            
            .salary-preview-table tbody tr:last-child td {
                border-bottom: none;
            }
            
            .salary-component-name {
                font-weight: 500;
            }
            
            .salary-amount-value {
                text-align: right;
                font-weight: 600;
                color: #111827;
            }
            
            .salary-summary-box {
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                border-radius: 12px;
                padding: 24px;
                margin-top: 24px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
            
            .salary-summary-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .salary-summary-row:last-child {
                border-bottom: none;
                margin-top: 8px;
                padding-top: 20px;
                border-top: 2px solid rgba(255, 255, 255, 0.2);
            }
            
            .salary-summary-label {
                font-size: 15px;
                color: #cbd5e1;
                font-weight: 500;
            }
            
            .salary-summary-value {
                font-size: 18px;
                font-weight: 700;
                color: #ffffff;
            }
            
            .salary-summary-value.earnings-color {
                color: #86efac;
            }
            
            .salary-summary-value.deductions-color {
                color: #fca5a5;
            }
            
            .salary-summary-value.net-pay {
                font-size: 24px;
                color: #fbbf24;
            }
            
            .salary-empty-state {
                text-align: center;
                padding: 40px 20px;
                color: #9ca3af;
            }
            
            .salary-empty-icon {
                font-size: 48px;
                margin-bottom: 12px;
                opacity: 0.5;
            }
        </style>
    `;

    // Build earnings table
    let earnings_html = `
        <div class="salary-section-card">
            <div class="salary-section-header earnings">
                <div class="salary-section-icon earnings">↑</div>
                <h4 class="salary-section-title">Earnings</h4>
            </div>
    `;

    if (earnings.length > 0) {
        earnings_html += `
            <table class="salary-preview-table">
                <thead>
                    <tr>
                        <th>Component</th>
                        <th class="salary-amount-col">Amount</th>
                    </tr>
                </thead>
                <tbody>
        `;

        earnings.forEach(row => {
            earnings_html += `
                <tr>
                    <td class="salary-component-name">${row.salary_component}</td>
                    <td class="salary-amount-value">${format_currency(row.amount)}</td>
                </tr>
            `;
        });

        earnings_html += `</tbody></table>`;
    } else {
        earnings_html += `
            <div class="salary-empty-state">
                <div class="salary-empty-icon">📋</div>
                <p>No earnings components added</p>
            </div>
        `;
    }

    earnings_html += `</div>`;

    // Build deductions table
    let deductions_html = `
        <div class="salary-section-card">
            <div class="salary-section-header deductions">
                <div class="salary-section-icon deductions">↓</div>
                <h4 class="salary-section-title">Deductions</h4>
            </div>
    `;

    if (deductions.length > 0) {
        deductions_html += `
            <table class="salary-preview-table">
                <thead>
                    <tr>
                        <th>Component</th>
                        <th class="salary-amount-col">Amount</th>
                    </tr>
                </thead>
                <tbody>
        `;

        deductions.forEach(row => {
            deductions_html += `
                <tr>
                    <td class="salary-component-name">${row.salary_component}</td>
                    <td class="salary-amount-value">${format_currency(row.amount)}</td>
                </tr>
            `;
        });

        deductions_html += `</tbody></table>`;
    } else {
        deductions_html += `
            <div class="salary-empty-state">
                <div class="salary-empty-icon">📋</div>
                <p>No deduction components added</p>
            </div>
        `;
    }

    deductions_html += `</div>`;

    // Totals
    let total_earnings = earnings.reduce((t, r) => t + (r.amount || 0), 0);
    let total_deductions = deductions.reduce((t, r) => t + (r.amount || 0), 0);
    let net_pay = total_earnings - total_deductions;

    // Summary HTML
    let summary_html = `
        <div class="salary-summary-box">
            <div class="salary-summary-row">
                <span class="salary-summary-label">Total Earnings</span>
                <span class="salary-summary-value earnings-color">${format_currency(total_earnings)}</span>
            </div>
            <div class="salary-summary-row">
                <span class="salary-summary-label">Total Deductions</span>
                <span class="salary-summary-value deductions-color">${format_currency(total_deductions)}</span>
            </div>
            <div class="salary-summary-row">
                <span class="salary-summary-label">Net Pay</span>
                <span class="salary-summary-value net-pay">${format_currency(net_pay)}</span>
            </div>
        </div>
    `;

    // Dialog
    let d = new frappe.ui.Dialog({
        title: "Salary Breakup Preview",
        size: "large",
        fields: [
            {
                fieldname: "container_html",
                fieldtype: "HTML"
            }
        ]
    });

    // Combine all HTML with scoped container
    d.fields_dict.container_html.$wrapper.html(`
        ${styles}
        <div class="salary-preview-container">
            <div class="salary-preview-header">
                <h3>💰 Salary Structure Breakdown</h3>
            </div>
            ${earnings_html}
            ${deductions_html}
            ${summary_html}
        </div>
    `);

    d.show();
}

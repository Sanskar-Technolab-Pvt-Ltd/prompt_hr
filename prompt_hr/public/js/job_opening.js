frappe.ui.form.off("Job Opening","company")
frappe.ui.form.on("Job Opening", {
    refresh: (frm) => {
        handleInternalJobPosting(frm);
        handleEmployeeReferral(frm);

        // ? FUNCTION TO APPLY FILTER ON JOB REQUISITION WITH STATUS == "FINAL APPROVAL"
        applyJobRequisitionFilter(frm)
        if (!frm.is_new()) {
            frm.events.make_dashboard(frm);
        }
        const current_user = frappe.session.user;
        let hide_notify_buttons = false;
        // Check if current user is an internal recruiter
        (frm.doc.custom_internal_recruiter || []).forEach(rec => {
            if (rec.user) {
                frappe.db.get_value("Employee", rec.user, "user_id", function (r) {
                    if (r.user_id === current_user) {
                        hide_notify_buttons = true;
                    }
                });
            }
        });

        // Check if current user is an external recruiter
        (frm.doc.custom_external_recruiter || []).forEach(rec => {
            if (rec.user) {
                frappe.call({
                    method: "prompt_hr.py.interview_availability.get_supplier_custom_user",
                    args: {
                        supplier_name: rec.user
                    },
                    callback: function (r) {
                        if (r.message === current_user) {
                            hide_notify_buttons = true;
                        }
                    }
                });
            }
        });

        // Check if current user is an internal interviewer
        (frm.doc.custom_internal_interviewers || []).forEach(rec => {
            if (rec.user) {
                frappe.db.get_value("Employee", rec.user, "user_id", function (r) {
                    if (r.user_id === current_user) {
                        hide_notify_buttons = true;
                    }
                });
            }
        });

        // Check if current user is an external interviewer
        (frm.doc.custom_external_interviewers || []).forEach(rec => {
            if (rec.user) {
                frappe.call({
                    method: "prompt_hr.py.interview_availability.get_supplier_custom_user",
                    args: {
                        supplier_name: rec.user
                    },
                    callback: function (r) {
                        if (r.message === current_user) {
                            hide_notify_buttons = true;
                        }
                    }
                });
            }
        });

        setTimeout(() => {
            if (!hide_notify_buttons) {
                frm.add_custom_button(__("Notify Interviewers"), function () {
                    frappe.dom.freeze(__('Notifying Interviewers...'));
                    frappe.call({
                        method: "prompt_hr.py.job_opening.send_job_opening_interview_notification",
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
                }, __("Notify"));

                frm.add_custom_button(__("Notify Recruiters"), function () {
                    frappe.dom.freeze(__('Notifying Recruiters...'));
                    frappe.call({
                        method: "prompt_hr.py.job_opening.send_job_opening_recruiter_notification",
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
                }, __("Notify"));
            }

        }, 100);
    },

    // ? CALLED ON FORM LOAD/REFRESH TO SHOW JOB APPLICANT SUMMARY DASHBOARD
    make_dashboard: function (frm) {
        // * FETCH DASHBOARD SUMMARY VIA WHITELISTED PYTHON METHOD
        frappe.call({
            method: "prompt_hr.py.job_opening.get_job_applicant_summary",
            args: {
                job_opening: frm.doc.name,
            },
            callback: function (r) {
                if (r.message) {
                    // ! Remove previous dashboard section if exists
                    $("div").remove(".form-dashboard-section.custom");

                    // * Extract offer-related data
                    const summary = r.message.data;

                    // * Begin building the HTML block
                    let html = `
                        <div class="form-dashboard-section custom mt-2 mb-3">
                            <div class="row font-weight-bold pb-2" style="border-bottom: 2px solid #dee2e6;">
                    `;

                    const labels = Object.keys(summary);

                    // * Render headers with vertical borders
                    labels.forEach((label, index) => {
                        html += `
                            <div class="col text-center" style="
                                border-right: ${index < labels.length - 1 ? '1px solid #dee2e6' : 'none'};
                            ">
                                ${frappe.utils.escape_html(label)}
                            </div>
                        `;
                    });

                    html += `</div><div class="row pt-2">`;

                    // * Render values, converting to string to retain 0s
                    labels.forEach((label, index) => {
                        html += `
                            <div class="col text-center" style="
                                border-right: ${index < labels.length - 1 ? '1px solid #dee2e6' : 'none'};
                            ">
                                ${frappe.utils.escape_html(String(summary[label]))}
                            </div>
                        `;
                    });

                    html += `</div></div>`;

                    // * Add section to dashboard
                    frm.dashboard.add_section(html, __("Job Opening Summary"));
                }
            }
        });
    },


    company: function (frm) {
        frm.set_value("custom_referral_bonus_policy", "");

        if (frm.doc.custom_allow_employee_referance && frm.doc.company) {
            fetchReferralBonusPolicy(frm);
        }
    },

    custom_allow_employee_referance: function (frm) {
        if (frm.doc.custom_allow_employee_referance && frm.doc.company) {
            fetchReferralBonusPolicy(frm);
        } else {
            frm.set_value("custom_referral_bonus_policy", "");
        }

        handleEmployeeReferral(frm);
    },
    custom_job_requisition_record(frm) {
            if (frm.doc.custom_job_requisition_record) {
                frappe.db.get_value('Job Requisition', frm.doc.custom_job_requisition_record, 'designation')
                    .then(({ message }) => {
                        if (message && message.designation) {
                            frm.set_value('designation', message.designation);
                        }
                    });
            }
        }
    
});

function fetchReferralBonusPolicy(frm) {
    frappe.db.get_value("Referral Bonus Policy", { company: frm.doc.company }, "name")
        .then((r) => {
            if (r?.message?.name) {
                frm.set_value("custom_referral_bonus_policy", r.message.name);
            }
        })
        .catch((err) => {
            console.error("Error fetching Referral Bonus Policy:", err);
        });
}

// ? INTERNAL JOB POSTING
function handleInternalJobPosting(frm) {
    if (frm.doc.custom_job_opening_type === "Internal") {
        frm.add_custom_button(__('Release for Internal Application'), () => {

            frappe.confirm(
                'Are you sure you want to send the internal job opening notification?',
                () => {
                    //? YES clicked - send email
                    frappe.call({
                        method: "prompt_hr.py.job_opening.send_job_opening_notification",
                        args: {
                            company: frm.doc.company,
                            due_date: frm.doc.custom_due_date_for_applying_job,
                            min_tenure_in_company: frm.doc.custom_minimum_tenure_in_company_in_months,
                            min_tenure_in_current_role: frm.doc.custom_minimum_tenure_in_current_role_in_months,
                            allowed_department: (frm.doc.custom_can_refer_from_department_internal || []).map(item => item.department),
                            allowed_location: (frm.doc.custom_can_refer_from_work_location_internal || []).map(item => item.work_location),
                            allowed_grade: (frm.doc.custom_can_refer_from_grade_internal || []).map(item => item.grade),
                            notification_name: "Internal Job Opening Email",
                            job_opening: frm.doc.name,
                            source: "Internal Application"
                        },
                        callback: (res) => {
                            frappe.msgprint(`${res.message?.length || 0} eligible employees have been notified.`);
                        }
                    });
                },
                () => {
                    //?  NO clicked - do nothing
                    frappe.show_alert({message: 'Notification cancelled', indicator: 'orange'});
                }
            );

        });
    }
}


// ? EMPLOYEE REFERRAL
function handleEmployeeReferral(frm) {
    if (frm.doc.custom_allow_employee_referance) {
        frm.add_custom_button(__('Notify Employees for Job Referral'), () => {
            frappe.call({
                method: "prompt_hr.py.job_opening.send_job_opening_notification",
                args: {
                    company: frm.doc.company,
                    due_date: frm.doc.custom_due_date_for_applying_job_jr,
                    min_tenure_in_company: frm.doc.custom_minimum_tenure_in_company_in_months_jr,
                    min_tenure_in_current_role: frm.doc.custom_minimum_tenure_in_current_role_in_months_jr,
                    allowed_department: (frm.doc.custom_can_refer_from_department_referral).map(item => item.department),
                    allowed_location: (frm.doc.custom_can_refer_from_work_location_referral).map(item => item.work_location),
                    allowed_grade: (frm.doc.custom_can_refer_from_grade_referral).map(item => item.grade),
                    notification_name: "Employee Referral Email",
                    job_opening: frm.doc.name,
                    source: "Employee Referral"
                },
                callback: (res) => {
                    frappe.msgprint(`${res.message?.length || 0} employees were notified for referral.`);
                }
            });
        });
    }
}

// ? FUNCTION TO APPLY FILTER ON JOB REQUISITION WITH STATUS == "FINAL APPROVAL"
function applyJobRequisitionFilter(frm) {
    frm.set_query("custom_job_requisition_record", () => {
        return {
            filters: {
                workflow_state: "Final Approval",
            }
        };
    });
}

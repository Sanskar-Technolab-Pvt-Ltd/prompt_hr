frappe.ui.form.on("Job Opening", {
    refresh: (frm) => {
        handleInternalJobPosting(frm);
        handleEmployeeReferral(frm);
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
            frappe.call({
                method: "prompt_hr.py.job_opening.send_job_opening_notification",
                args: {
                    due_date: frm.doc.custom_due_date_for_applying_job,
                    min_tenure_in_company: frm.doc.custom_minimum_tenure_in_company_in_months,
                    min_tenure_in_current_role: frm.doc.custom_minimum_tenure_in_current_role_in_months,
                    allowed_department: frm.doc.custom_can_apply_from_department,
                    allowed_location: frm.doc.custom_can_apply_from_location,
                    allowed_grade: frm.doc.custom_can_apply_from_grade,
                    notification_name: "Internal Job Opening Email",
                    job_opening: frm.doc.name,
                    source: "Internal Application"
                },
                callback: (res) => {
                    frappe.msgprint(`${res.message?.length || 0} eligible employees have been notified.`);
                }
            });
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
                    due_date: frm.doc.custom_due_date_for_applying_job_jr,
                    min_tenure_in_company: frm.doc.custom_minimum_tenure_in_company_in_months_jr,
                    min_tenure_in_current_role: frm.doc.custom_minimum_tenure_in_current_role_in_months_jr,
                    allowed_department: frm.doc.custom_can_apply_from_department_jr,
                    allowed_location: frm.doc.custom_can_apply_from_location_jr,
                    allowed_grade: frm.doc.custom_can_apply_from_grade_jr,
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

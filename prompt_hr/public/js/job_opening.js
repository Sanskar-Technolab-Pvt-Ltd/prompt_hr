

frappe.ui.form.on("Job Opening", {
    refresh: (frm) => {
        
        // ? HANDLE INTERNAL JOB POSTING BUTTON
        internalJobPosting(frm);
        
        // ? CHECK AND ENABLE EMPLOYEE REFERRAL FEATURE
        employeeReferralIsAllowed(frm);
    },

    company: function (frm) {

        // ? RESET CUSTOM REFERRAL BONUS POLICY WHEN COMPANY IS CHANGED
        frm.set_value("custom_referral_bonus_policy", "");
        
        // ? IF EMPLOYEE REFERRAL IS ALLOWED AND COMPANY IS SET, FETCH REFERRAL BONUS POLICY
        if (frm.doc.custom_allow_employee_referance && frm.doc.company) {
            frappe.db.get_value("Referral Bonus Policy", { company: frm.doc.company }, "name")
                .then((r) => {
                    if (r && r.message && r.message.name) {

                        // ? SET THE REFERRAL BONUS POLICY IN THE FORM
                        frm.set_value("custom_referral_bonus_policy", r.message.name);
                    }
                })
                .catch((err) => {
                    console.error("Error fetching Referral Bonus Policy:", err);
                });
        }
    },

    custom_allow_employee_referance: function (frm) {

        // ? IF EMPLOYEE REFERRAL IS ALLOWED, FETCH THE REFERRAL BONUS POLICY
        if (frm.doc.custom_allow_employee_referance && frm.doc.company) {
            frappe.db.get_value("Referral Bonus Policy", { company: frm.doc.company }, "name")
                .then((r) => {
                    if (r && r.message && r.message.name) {

                        // ? SET THE REFERRAL BONUS POLICY IN THE FORM
                        frm.set_value("custom_referral_bonus_policy", r.message.name);
                    }
                })
                .catch((err) => {
                    console.error("Error fetching Referral Bonus Policy:", err);
                });
        } else {

            // ? CLEAR REFERRAL BONUS POLICY IF EMPLOYEE REFERRAL IS DISABLED
            frm.set_value("custom_referral_bonus_policy", "");
        }

        // ? RECHECK THE EMPLOYEE REFERRAL FEATURE
        employeeReferralIsAllowed(frm);
    }
});

// ? FUNCTION TO HANDLE INTERNAL JOB POSTING
function internalJobPosting(frm) {

    // ? CHECK IF THE JOB OPENING TYPE IS INTERNAL
    if (frm.doc.custom_job_opening_type === "Internal") {

        // ? ADD BUTTON TO RELEASE JOB POSTING FOR INTERNAL APPLICATION
        frm.add_custom_button(__('Release for Internal Application'), () => {

            // ? CALL BACKEND METHOD TO RELEASE THE INTERNAL JOB POSTING
            frappe.call({
                method: "prompt_hr.py.job_opening.release_internal_job_posting",
                args: {
                    due_date: frm.doc.custom_due_date_for_applying_job,
                    min_tenure_in_company: frm.doc.custom_minimum_tenure_in_company_in_months,
                    min_tenure_in_current_role: frm.doc.custom_minimum_tenure_in_current_role_in_months,
                    allowed_department: frm.doc.custom_can_apply_from_department,
                    allowed_location: frm.doc.custom_can_apply_from_location,
                    allowed_grade: frm.doc.custom_can_apply_from_grade,
                    notification_name: "Internal Job Opening Email" 
                },
                callback: (res) => {

                    // ? SHOW SUCCESS MESSAGE WITH THE NUMBER OF EMPLOYEES NOTIFIED
                    frappe.msgprint(
                        `${res.message.length} eligible employees have been notified.`
                    );
                }
            });
        });
    }
}

// ? FUNCTION TO HANDLE EMPLOYEE REFERRAL FEATURE
function employeeReferralIsAllowed(frm) {

    // ? IF EMPLOYEE REFERRAL IS ALLOWED, ADD NOTIFY EMPLOYEES BUTTON
    if (frm.doc.custom_allow_employee_referance) {
        frm.add_custom_button(__('Notify Employees for Job Referral'), () => {

            // ? CALL BACKEND METHOD TO SEND JOB REFERRAL EMAIL
            frappe.call({
                method: "prompt_hr.py.job_opening.notify_all_employees_for_referral",
                args: {
                    job_opening: frm.doc.name,
                    notification_name: "Employee Referral Email"
                },
                callback: (res) => {

                    // ? SHOW SUCCESS MESSAGE AFTER SENDING REFERRAL EMAIL
                    frappe.msgprint(res.message || "Referral email sent successfully!");
                }
            });
        });
    }
}

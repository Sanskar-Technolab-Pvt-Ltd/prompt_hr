frappe.ui.form.on("Job Opening", {

    refresh: (frm) => {

        // ? HANDLE INTERNAL JOB POSTING
        internalJobPosting(frm);
    }
});

// ? FUNCTION TO HANDLE INTERNAL JOB POSTING
function internalJobPosting(frm) {

    // ? CHECK IF THE JOB OPENING TYPE IS INTERNAL
    if (frm.doc.custom_job_opening_type == "Internal") {

        // ? ADD A CUSTOM BUTTON TO RELEASE JOB POSTING FOR INTERNAL APPLICATIONS
        frm.add_custom_button(__('Release for Internal Application'), () => {
            
            // ? CALL THE BACKEND FUNCTION TO HANDLE INTERNAL JOB POSTING
            frappe.call({
                method: "prompt_hr.py.job_opening.release_internal_job_posting",
                args: {
                    // ? PASS NECESSARY PARAMETERS TO THE BACKEND FUNCTION
                    due_date: frm.doc.custom_due_date_for_applying_job,
                    min_tenure_in_company: frm.doc.custom_minimum_tenure_in_company_in_months,
                    min_tenure_in_current_role: frm.doc.custom_minimum_tenure_in_current_role_in_months,
                    allowed_department: frm.doc.custom_can_apply_from_department,
                    allowed_location: frm.doc.custom_can_apply_from_location,
                    allowed_grade: frm.doc.custom_can_apply_from_grade
                },
                callback: (res) => {

                    // ? LOG THE RESPONSE MESSAGE FROM THE BACKEND
                    console.log(res.message);
                }

            })

        });
    }

}

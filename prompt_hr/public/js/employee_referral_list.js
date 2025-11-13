frappe.ui.form.on("Employee Referral", {
    refresh(frm) {
        frm.set_query("custom_job_opening", function(doc) {
            return {
                filters: {
                    designation: doc.for_designation,
                    custom_allow_employee_referance: 1
                }
            };
        });
    }
});

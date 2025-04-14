frappe.ui.form.on('Job Offer', {
    onload: function (frm) {
        // ? APPLY CANDIDATE-SPECIFIC LOGIC ONLY IF USER IS GENERIC CANDIDATE
        if (frappe.session.user === "candidate@sanskartechnolab.com") {

            const is_verified = sessionStorage.getItem("job_offer_verified") === "true";

            if (!is_verified) {
                // ? BLOCK USER IF NOT VERIFIED (SHOULD NEVER HAPPEN IF REDIRECT JS WORKED)
                frappe.msgprint("🚫 You are not authorized to view this page.");
                window.location.href = "/app"; 
                return;
            }

            // ? USER IS VERIFIED — SHOW ALL FIELDS
            frm.fields.forEach(field => {
                frm.set_df_property(field.df.fieldname, 'hidden', false);
            });
        }
    }
});

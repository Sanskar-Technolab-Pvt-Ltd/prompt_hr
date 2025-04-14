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
    },

    refresh: function (frm) {
        // ? SHOW BUTTON ONLY FOR NON-CANDIDATE USERS
        if (frappe.session.user !== "candidate@sanskartechnolab.com") {
            frm.add_custom_button("Release Offer Letter", () => {
                frappe.confirm(
                    "Are you sure you want to release the offer letter?",
                    () => {
                        frappe.call({
                            method: "prompt_hr.py.job_offer.release_offer_letter",
                            args: {
                                doctype: frm.doctype,
                                docname: frm.doc.name
                            },
                            callback: function (r) {
                                if (!r.exc) {
                                    frappe.msgprint("🎉 Offer Letter Released!");
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            })
        }
    }
});



frappe.ui.form.on('Job Offer', {
    // ? MAIN ENTRY POINT — EXECUTES ON FORM REFRESH
    refresh: function (frm) {
        const is_candidate = frappe.session.user === "candidate@sanskartechnolab.com";

        if (is_candidate) {
            handle_candidate_access(frm);
        } else if (frappe.user_roles.includes("HR Manager")) {
            add_release_offer_button(frm);
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

// ? ADD "RELEASE / RESEND OFFER LETTER" BUTTON FOR HR MANAGER
function add_release_offer_button(frm) {
    const already_sent = frm.doc.custom_offer_letter_sent === 1;
    const button_label = already_sent ? "Resend Offer Letter" : "Release Offer Letter";

    frm.add_custom_button(button_label, () => {
        frappe.confirm(
            `Are you sure you want to ${already_sent ? "resend" : "release"} the offer letter?`,
            () => release_offer_letter(frm, already_sent)
        );
    });
}

// ? CALL BACKEND TO RELEASE OR RESEND OFFER LETTER
function release_offer_letter(frm, is_resend) {
    frappe.call({
        method: "prompt_hr.py.job_offer.release_offer_letter",
        args: {
            doctype: frm.doctype,
            docname: frm.doc.name,
            is_resend: is_resend // ? PASS FLAG TO BACKEND
        },
        callback: function (r) {
            if (r.exc) {
                frappe.msgprint({
                    title: "Error",
                    message: "⚠️ Something went wrong while processing the offer.",
                    indicator: "red"
                });
                return;
            }

            // ? UPDATE FLAG IF FIRST TIME
            if (!is_resend) {
                frm.set_value("custom_offer_letter_sent", 1).then(() => {
                    frm.save_or_update();
                });


            }

            frappe.msgprint({
                title: "Success",
                message: `🎉 Offer Letter ${is_resend ? "Resent" : "Released"}!`,
                indicator: "green"
            });

        },
        error: function (err) {
            frappe.msgprint({
                title: "Server Error",
                message: "❌ Could not complete the request. Please try again.",
                indicator: "red"
            });
            console.error("Error releasing/resending offer letter:", err);
        }
    });
}

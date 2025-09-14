// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Penalty Emails", {
	 refresh: function(frm) {
        // Add a button to the form
        frm.add_custom_button(__('Send Emails'), function() {
            frappe.call({
                method: "prompt_hr.prompt_hr.doctype.penalty_emails.penalty_emails.send_penalty_emails",
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint(__('Emails sent successfully'));
                    }
                }
            });
        });
    }
});

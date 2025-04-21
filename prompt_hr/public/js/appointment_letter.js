frappe.ui.form.on("Appointment Letter", {
    refresh: function(frm) {
        if( !frm.is_new() ){
            frm.add_custom_button("Send Appointment Letter", function() {
                frappe.call({
                    method: "prompt_hr.api.main.trigger_appointment_notification",
                    args: {
                        name: frm.doc.name,
                        applicant_name: frm.doc.applicant_name,
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(r.message);
                        }
                    }
                });
            });
        }
    }
})
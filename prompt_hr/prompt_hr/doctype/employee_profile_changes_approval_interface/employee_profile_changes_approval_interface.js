// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Profile Changes Approval Interface", {
    approval_status: function (frm) {
        if (frm.doc.approval_status && frm.doc.approval_status === "Rejected") {
            frappe.prompt({
                label: 'Reason for rejection',
                fieldname: 'reason_for_rejection',
                fieldtype: 'Small Text',
                reqd: 1
            }, (values) => {
                if (values.reason_for_rejection) {
                    frm.set_value("reason_for_rejection", values.reason_for_rejection)
                    // frm.set_value("approval_status", "Rejected")
                }
            })
        }
    }
});

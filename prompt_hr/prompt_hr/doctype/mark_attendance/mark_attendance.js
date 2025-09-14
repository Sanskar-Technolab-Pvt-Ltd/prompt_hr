// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Mark Attendance", {
	attendance_date(frm) {
        frm.save()
    },
    mark_attendance: function (frm) {
        if (!frm.doc.company) {
            frappe.throw("Please Select a Company")
        }
        if (!frm.doc.attendance_date) {
            frappe.throw("Please Select a date for marking attendance")
        }

        // frappe.freeze("Marking Attendance...");

        frappe.call({
            method: "prompt_hr.py.auto_mark_attendance.mark_attendance",
            args: {
                "attendance_date": frm.doc.attendance_date,
                "company": frm.doc.company,
            },
             freeze: true,
            freeze_message:__("Marking Attendance..."),
            callback: function (r) {

                if (!r.exc) {
                    frappe.msgprint({
                        title: __("Success"),
                        message: r.message || "Attendance marked successfully!",
                        indicator: "green"
                    });
                } else {
                    frappe.msgprint({
                        title: __("Error"),
                        message: "An error occurred while marking attendance.",
                        indicator: "red"
                    });
                }
            }
        });

        
    }

});

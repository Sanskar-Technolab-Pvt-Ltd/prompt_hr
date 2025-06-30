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

        frappe.call({
            method: "prompt_hr.py.auto_mark_attendance.mark_attendance",
            args: {
                "attendance_date": frm.doc.attendance_date,
                "company": frm.doc.company,
            }
        })
        
    }

});

// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Mark Attendance", {
	attendance_date(frm) {
        frm.save()
    },
    mark_attendance: function (frm) {
        console.log("Calling Method to mark attendance for the specified date")
    }

});

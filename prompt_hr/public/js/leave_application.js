frappe.ui.form.off("Leave Application", "calculate_total_days")
frappe.ui.form.on("Leave Application", {
    calculate_total_days: function (frm) {
		if (frm.doc.from_date && frm.doc.to_date && frm.doc.employee && frm.doc.leave_type) {
			return frappe.call({
				method: "hrms.hr.doctype.leave_application.leave_application.get_number_of_leave_days",
				args: {
					employee: frm.doc.employee,
					leave_type: frm.doc.leave_type,
					from_date: frm.doc.from_date,
					to_date: frm.doc.to_date,
					half_day: frm.doc.half_day,
					half_day_date: frm.doc.half_day_date,
                    custom_half_day_time: frm.doc.custom_half_day_time
				},
				callback: function (r) {
					if (r && r.message) {
						frm.set_value("total_leave_days", r.message);
						frm.trigger("get_leave_balance");
					}
				},
			});
		}
	},
    custom_half_day_time: function(frm) {
        frm.trigger("calculate_total_days");
    }
})
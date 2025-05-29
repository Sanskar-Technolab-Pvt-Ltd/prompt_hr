frappe.ui.form.off("Leave Application", "calculate_total_days")
frappe.ui.form.on("Leave Application", {
	refresh: function(frm) {
		frappe.db.get_value("Leave Type", frm.doc.leave_type, "custom_allow_leave_extension").then(r => {
			if (r.message.custom_allow_leave_extension) {
				frm.add_custom_button(__('Extend Leave'), function() {
					let d = new frappe.ui.Dialog({
						title: 'Extend Leave',
						fields: [
							{
								label: 'From Date',
								fieldname: 'from_date',
								fieldtype: 'Date',
								read_only: 1,
								default: frm.doc.from_date
							},
							{
								label: 'To Date',
								fieldname: 'to_date',
								fieldtype: 'Date',
								read_only: 1,
								default: frm.doc.to_date
							},
							{
								label: "Total Leave Days",
								fieldname: "total_leave_days",
								fieldtype: "Data",
								read_only: 1,
								default: frm.doc.total_leave_days
							},
							{
								label: 'Extend To',
								fieldname: 'extend_to',
								fieldtype: 'Date',
								reqd: 1
							}
						],

						primary_action_label: 'Extend',
						primary_action(values) {
							frappe.call({
								method: "prompt_hr.py.leave_application.extend_leave_application",
								args: {
									leave_application: frm.doc.name,
									extend_to: values.extend_to
								},
								callback: function(r) {
									if (r) {
										frappe.msgprint(__('Leave extended successfully!'));
										frm.reload_doc();
									}
								}
							})
							d.hide()
						}
					})
					d.show()
				}).removeClass("btn-default").addClass("btn-primary");
			}
		});
	},

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
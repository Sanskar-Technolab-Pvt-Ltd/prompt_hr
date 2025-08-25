frappe.ui.form.off("Leave Application", "calculate_total_days")
frappe.ui.form.on("Leave Application", {
	refresh: function(frm) {
		if (frm.is_new()){
			frm.doc.custom_extension_status = null
		}
		if (frm.doc.employee){
			frappe.call({
                method: "prompt_hr.py.utils.check_user_is_reporting_manager",
                args: {
                    user_id: frappe.session.user,
                    requesting_employee_id: frm.doc.employee
                },
                callback: function (res) {
                    if (!res.message.error) {
                        if (res.message.is_rh) {
                            if (!has_common(frappe.user_roles, ["S - HR Director (Global Admin)", "System Manager"]))
								frm.fields.filter(field => field.has_input).forEach(field => {
									frm.set_df_property(field.df.fieldname, "read_only", 1);
								});
                        }

                    } else if (res.message.error) {
                        frappe.throw(res.message.message)
                    }
                }
            })
		}
		if (frm.doc.workflow_state !== "Pending")
        {
			let current_user = frappe.session.user;
			frappe.db.get_value("Employee", frm.doc.employee, "user_id").then(r => {
				if (r.message.user_id == current_user) {
					frappe.after_ajax(() => {
						frm.disable_form()

					})
				}
			});
        }
		if (frm.doc.custom_optional_holidays) {
			frm.trigger("leave_type");
		}
		frappe.call({
			method: "prompt_hr.py.leave_application.leave_extension_allowed",
			args: {	
				leave_type: frm.doc.leave_type || '',
				employee: frm.doc.employee || '',
			},
			callback: function (r) {
				if (r.message && (frm.doc.workflow_state == 'Approved') && (!frm.doc.custom_extension_status || frm.doc.custom_extension_status == "")) {
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
								reqd: 1,
								onchange: function() {
									if (this.value) {
										frappe.call({
											method: "prompt_hr.py.leave_application.custom_get_number_of_leave_days",
											args: {
												employee: frm.doc.employee,
												leave_type: frm.doc.leave_type,
												from_date: frappe.datetime.add_days(frm.doc.to_date, 1),
												to_date: d.get_value("extend_to"),
												half_day: 0,
											},
											callback: function(r) {
												console.log(r)
												if (r.message) {
													d.set_value("new_total_leave_days", r.message);
												}
												else{
													d.set_value("new_total_leave_days", "0");
												}
											}
										})
									}
								}
							},
							{
								label: "New Total Leave Days",
								fieldname: "new_total_leave_days",
								fieldtype: "Data",
								read_only: 1,
								default:"0",
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
										frappe.run_serially([
											() => frm.reload_doc(),
											() => frappe.msgprint(__('Leave extended successfully!')),
											() => frm.set_df_property('custom_leave_status', 'hidden', 0)
										]);
									}
								}
							})
							d.hide()
						}
					})
					d.show()
				}).removeClass("btn-default").addClass("btn-primary");
			}
			}
		})
	},
    calculate_total_days: function (frm) {
		if (frm.doc.from_date && frm.doc.to_date && frm.doc.employee && frm.doc.leave_type) {
			return frappe.call({
				method: "prompt_hr.py.leave_application.custom_get_number_of_leave_days",
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
    },

	leave_type: function(frm) {
            frappe.db.get_value("Leave Type", frm.doc.leave_type, "custom_is_optional_festival_holiday_leave")
                .then(r => {
                    if (r.message && r.message.custom_is_optional_festival_holiday_leave) {
                        frm.set_df_property('from_date', 'hidden', 1);
						frm.set_df_property('to_date', 'hidden', 1);
						frm.set_df_property('half_day', 'hidden', 1);
						frm.set_df_property('half_day_date', 'hidden', 1);
						frm.set_df_property('description', 'hidden', 1);
						frm.set_df_property('custom_attachment', 'hidden', 1);
						frm.set_df_property('custom_optional_holidays', 'hidden', 0);
						frm.set_df_property('custom_optional_holidays', 'reqd', 1);
						frappe.call({
							method: 'prompt_hr.py.leave_application.get_optional_festival_holiday_leave_list',
							args: {
								company: frm.doc.company,
								employee: frm.doc.employee || '',
								leave_type: frm.doc.leave_type
							},
							callback: function(r) {
								if (r.message) {
									// For Select field with label/value options
									frm.optional_holidays_data = r.message;
									frm.set_df_property('custom_optional_holidays', 'options', r.message);
									frm.refresh_field('custom_optional_holidays');
								} else {
									frappe.msgprint(__('No optional holidays found for this company.'));
								}
							},
						});

                    }
					else {
						frm.set_df_property('custom_optional_holidays', 'options', '');
						frm.set_df_property('custom_optional_holidays', 'reqd', 0);
						frm.set_df_property('custom_optional_holidays', 'hidden', 1);
                        frm.set_df_property('from_date', 'hidden', 0);
						frm.set_df_property('to_date', 'hidden', 0);
						frm.set_df_property('half_day', 'hidden', 0);
						frm.set_df_property('half_day_date', 'hidden', 0);
						frm.set_df_property('description', 'hidden', 0);
						frm.set_df_property('custom_attachment', 'hidden', 0);
                    }
                });
        
    },

	company: function(frm){
		frm.trigger("leave_type");
	},
	custom_optional_holidays: function(frm) {
        const selected = frm.doc.custom_optional_holidays;
		optional_holidays_data = frm.optional_holidays_data || []
        if (selected && optional_holidays_data && optional_holidays_data.length) {
            const holiday = optional_holidays_data.find(h => h.value === selected);
            if (holiday) {
                frm.set_value('from_date', holiday.holiday_date);
                frm.set_value('to_date', holiday.holiday_date);
            }
        }
    }
})
frappe.ui.form.off("Leave Allocation", "leave_policy")
frappe.ui.form.off("Leave Allocation", "add_allocate_leaves_button")
frappe.ui.form.on("Leave Allocation", {
    refresh: function(frm){
        if (!frm.doc.__islocal) {
			frappe.db.get_value("Leave Type", frm.doc.leave_type, "is_earned_leave", (r) => {
				if (!r?.is_earned_leave) return;
				frm.set_df_property("new_leaves_allocated", "read_only", 1);
				frm.trigger("add_allocate_leaves_button");
			});
		}
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee, "gender", function(r) {
                if (r && r.gender) {
                    frm.set_query("leave_type", () => {
                        return {
                            query: "prompt_hr.py.leave_allocation.get_leave_types_for_display",
                            filters: {
                                gender: r.gender,
                                company: frm.doc.company || {},
                            }
                        };
                    });
                }
            });
        } 
    },
    employee: function(frm) {
        frm.set_value("leave_type", null)
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee, "gender", function(r) {
                if (r && r.gender) {
                    frm.set_query("leave_type", () => {
                        return {
                            query: "prompt_hr.py.leave_allocation.get_leave_types_for_display",
                            filters: {
                                gender: r.gender,
                                company: frm.doc.company,
                            }
                        };
                    });
                }
            });
        } else {
            // Reset leave_type query so all leave types are visible
            frm.set_query("leave_type", function () {
                return {
                    filters: {
                        is_lwp: 0,
                    },
                };
		});
        }
    },
    leave_policy(frm) {
        if (frm.doc.leave_policy && frm.doc.leave_type && frm.doc.leave_policy_assignment) {
            frappe.db.get_value(
                "Leave Policy Detail",
                {
                    parent: frm.doc.leave_policy,
                    leave_type: frm.doc.leave_type,
                },
                "annual_allocation",
                (r) => {
                    if (r && !r.exc) {
                        frm.set_value("new_leaves_allocated", flt(r.annual_allocation));
                    }
                },
                "Leave Policy"
            );
        }
    },
    add_allocate_leaves_button: async function (frm) {
		const { message: monthly_earned_leave } = await frappe.call({
			method: "get_monthly_earned_leave",
			doc: frm.doc,
		});

		frm.add_custom_button(
			__("Allocate Leaves"),
			function () {
				const dialog = new frappe.ui.Dialog({
					title: "Manual Leave Allocation",
					fields: [
						{
							label: "New Leaves to be Allocated",
							fieldname: "new_leaves",
							fieldtype: "Float",
							reqd: 1,
						},
						{
							label: "From Date",
							fieldname: "from_date",
							fieldtype: "Date",
							default: frappe.datetime.get_today(),
						},
						{
							label: "To Date",
							fieldname: "to_date",
							fieldtype: "Date",
							read_only: 1,
							default: frm.doc.to_date,
						},
					],
					primary_action_label: "Allocate",
					primary_action({ new_leaves, from_date }) {
						frappe.call({
							method: "prompt_hr.py.leave_allocation.custom_allocate_leaves_manually",
							args: {doc:frm.doc.name, new_leaves, from_date },
							callback: function (r) {
								if (!r.exc) {
									dialog.hide();
									frm.reload_doc();
								}
							},
						});
					},
				});
				dialog.fields_dict.new_leaves.set_value(monthly_earned_leave);
				dialog.fields_dict.from_date.datepicker?.update({
					minDate: frappe.datetime.str_to_obj(frm.doc.from_date),
					maxDate: frappe.datetime.str_to_obj(frm.doc.to_date),
				});

				dialog.show();
			},
			__("Actions"),
		);
	},
});

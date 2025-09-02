frappe.ui.form.off("Leave Allocation", "leave_policy")
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
});

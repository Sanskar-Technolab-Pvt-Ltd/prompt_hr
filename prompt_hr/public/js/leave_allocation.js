frappe.ui.form.on("Leave Allocation", {
    refresh: function(frm){
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
    }
});

// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Standard Salary", {
    refresh: function(frm){
        frm.set_query("salary_structure_assignment", function () {
                return {
                    filters: {
                        employee: frm.doc.employee,
                        docstatus: 1,
                    },
                };
            });
    },
	employee(frm) {
        if (frm.doc.employee) {
            frappe.db.get_list("Salary Structure Assignment", {
                filters: {
                    employee: frm.doc.employee,
                    docstatus: 1,
                },
                order_by: "creation desc",
            }).then((res) => {
                if (res.length > 0) {
                    console.log(res);
                    frm.set_value("salary_structure_assignment", res[0].name);
                }
            });
        }
        else {
            frm.set_value("salary_structure_assignment", "");
        }
	},
});

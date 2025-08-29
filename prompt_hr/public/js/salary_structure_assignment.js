frappe.ui.form.on("Salary Structure Assignment", {
    refresh: function(frm) {
        //? ADD BUTTON FOR VIEWING EMPLOYEE STANDARD SALARY
        if (frm.doc.employee && !frm.is_new()) {
            frm.add_custom_button("View Standard Salary", function() {
                frappe.db.get_value("Employee Standard Salary", { employee: frm.doc.employee }, "name")
                    .then(r => {
                        if (r.message && r.message.name) {
                            frappe.set_route("Form", "Employee Standard Salary", r.message.name);
                        } else {
                            frappe.msgprint("No Standard Salary record found for this employee.");
                        }
                    });

            });
        }
    },
    //? TRIGGER WHEN EMPLOYEE IS SELECTED
    employee: function(frm) {
        set_income_tax_slab_from_ui(frm);
    },

    //? TRIGGER WHEN FROM DATE IS SELECTED/CHANGED
    from_date: function(frm) {
        if (frm.doc.employee)
        {
            set_income_tax_slab_from_ui(frm);
        }
    }
});

//! FUNCTION TO CALL PYTHON METHOD TO SET TAX SLAB
function set_income_tax_slab_from_ui(frm) {
    if (frm.doc.employee) {
        frappe.call({
            method: "prompt_hr.py.salary_structure_assignment.set_income_tax_slab",
            args: {
                employee: frm.doc.employee,
                posting_date: frm.doc.from_date || frappe.datetime.get_today(),
                company: frm.doc.company || null  //? COMPANY IS OPTIONAL
            },
            callback: function(res) {
                if (res.message) {
                    frm.set_value("income_tax_slab", res.message);
                    frm.refresh_field("income_tax_slab")
                }
            }
        });
    }
}

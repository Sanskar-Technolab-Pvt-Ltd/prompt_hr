frappe.ui.form.on("Salary Structure Assignment", {
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

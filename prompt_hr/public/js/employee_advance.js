frappe.ui.form.on("Employee Advance", {
    custom_advance(frm) {
        apply_salary_advance_logic(frm);
    },

    onload(frm) {
        apply_salary_advance_logic(frm);
    },

    refresh(frm) {
        apply_salary_advance_logic(frm);
    }
});

function apply_salary_advance_logic(frm) {
    if (frm.doc.custom_advance === "Salary Advance") {
        frm.set_value("repay_unclaimed_amount_from_salary", 1);
    } else {
        frm.set_value("repay_unclaimed_amount_from_salary", 0);
    }
}

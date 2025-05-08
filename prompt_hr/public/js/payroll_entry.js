// ? CHILD TABLE BUTTON HANDLER FOR "Process FnF" BUTTON IN EACH ROW
frappe.ui.form.on('Pending FnF Details', {
    process_fnf: function (frm, cdt, cdn) {
        // ? FETCH ROW DATA
        const row = locals[cdt][cdn];

        // ? SAFEGUARD: SKIP IF NO EMPLOYEE
        if (!row.employee) {
            frappe.msgprint("Employee not found in this row.");
            return;
        }

        // ? REDIRECT TO FULL AND FINAL FORM WITH EMPLOYEE IN URL
        const emp = encodeURIComponent(row.employee);
        window.location.href = `${window.location.origin}/app/full-and-final-statement/new-1?employee=${emp}`;
    }
});

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


frappe.ui.form.on("Payroll Entry", {
    refresh: (frm) => {
        // ? REMOVE AUTO BRANCH ADDITION DATA
        empty_branch_field_if_form_is_new(frm);
        
        // ? ADD CUSTOM BUTTONS FOR LEAVE ACTIONS
        frm.add_custom_button(
            __("Approve Leave"),
            function () {
                handle_leave_action(frm, "approve");
            },
            __("Leave Actions")
        );

        frm.add_custom_button(
            __("Reject Leave"),
            function () {
                handle_leave_action(frm, "reject");
            },
            __("Leave Actions")
        );

        frm.add_custom_button(
            __("Confirm Leave"),
            function () {
                handle_leave_action(frm, "confirm");
            },
            __("Leave Actions")
        );
    },
});

// ? FUNCTION TO EMPTY BRANCH FIELD IF FORM IS NEW
function empty_branch_field_if_form_is_new(frm) {
    // ? CHECK IF FORM IS NEW
    if (frm.is_new()) {
        // ? EMPTY BRANCH FIELD
        frm.set_value("branch", "");
    }
}

// ? FUNCTION TO HANDLE LEAVE ACTIONS (APPROVE, REJECT, CONFIRM)
function handle_leave_action(frm, action) {
    // * Filter selected rows from the Pending Leave Approval child table
    const selected = frm.doc.custom_pending_leave_approval.filter(row => row.__checked);

    // ! Stop if no leave entries are selected
    if (!selected.length) {
        frappe.msgprint("Please select at least one leave entry.");
        return;
    }

    // * Call server-side method to process leave action
    frappe.call({
        method: "prompt_hr.py.payroll_entry.handle_leave_action",
        args: {
            docname: frm.doc.name,
            doctype: frm.doc.doctype,
            action: action,
            leaves: selected.map(row => row.leave_application), // * Extract leave_application IDs
        },
        callback(r) {
            // * If leaves were successfully processed
            if (r.message && r.message.length > 0) {
                frm.reload_doc(); // * Refresh the form to reflect changes

                const actionPastTense = {
                    approve: "approved",
                    reject: "rejected",
                    confirm: "confirmed"
                };
                const pastTense = actionPastTense[action] || `${action}ed`;

                // ? Show success message with number of leaves processed
                setTimeout(() => {
                    frappe.msgprint(`Successfully ${pastTense} ${r.message.length} leave(s).`);
                }, 200); // delay before showing the dialog
            } else {
                // ? No leaves to process
                frappe.msgprint("There are no any leaves to " + action + ".");
            }
        }
    });
}

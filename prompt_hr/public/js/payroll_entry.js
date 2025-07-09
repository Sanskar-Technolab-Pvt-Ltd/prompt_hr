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
        frm.get_field('custom_lop_summary').grid.cannot_add_rows = true;
        frm.refresh_field('custom_lop_summary');
        // ? ADD CUSTOM BUTTONS FOR LEAVE ACTIONS
        frm.add_custom_button(
            __("Approve Leave"),
            function () {
                handle_leave_action(frm, "approve");
            },
            __("Manage Leave Requests")
        );

        frm.add_custom_button(
            __("Reject Leave"),
            function () {
                handle_leave_action(frm, "reject");
            },
            __("Manage Leave Requests")
        );

        frm.set_query('employee','custom_lop_reversal_details', function(doc, cdt, cdn) {
            // Get the list of employee names from the employees child table
            let employee_list = (frm.doc.employees || []).map(row => row.employee).filter(Boolean);
            return {
                filters: {
                    name: ["in", employee_list]
                }
            };
        });

        frm.set_query('employee','custom_adhoc_salary_details', function(doc, cdt, cdn) {
            // Get the list of employee names from the employees child table
            let employee_list = (frm.doc.employees || []).map(row => row.employee).filter(Boolean);
            return {
                filters: {
                    name: ["in", employee_list]
                }
            };
        });
        
    },
    before_save: (frm) => {
        frm.set_value('custom_pending_leave_approval', []);
    }
});

// ? FUNCTION TO EMPTY BRANCH FIELD IF FORM IS NEW
function empty_branch_field_if_form_is_new(frm) {
    // ? CHECK IF FORM IS NEW
    if (frm.is_new()) {
        // ? EMPTY BRANCH FIELD
        frm.set_value("branch", "");
    }
}

// ? FUNCTION TO HANDLE LEAVE ACTIONS (APPROVE, REJECT)
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

frappe.ui.form.on("LOP Reversal Details", {
    employee: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.employee) {
            let date_obj = frappe.datetime.str_to_obj(frm.doc.start_date);

            date_obj.setMonth(date_obj.getMonth() - 1);

            // Format to "Month-YYYY" (e.g., March-2025 if start_date is April 2025)
            let formatted_date = date_obj.toLocaleDateString('en-US', {
                month: 'long',
                year: 'numeric'
            }).replace(' ', '-');

            frappe.model.set_value(cdt, cdn, "lop_month", formatted_date);
            frappe.call({
                method: "prompt_hr.py.payroll_entry.get_actual_lop_days",
                args: {
                    employee: row.employee,
                    start_date: frm.doc.start_date
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, "actual_lop_days", r.message);
                    } else {
                        frappe.model.set_value(cdt, cdn, "actual_lop_days", 0);
                    }
                }
            });
        }
        else {
            frappe.model.set_value(cdt, cdn, "lop_month", "");
            frappe.model.set_value(cdt, cdn, "actual_lop_days", 0);
        }
    }
    }
)
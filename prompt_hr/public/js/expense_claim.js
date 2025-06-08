// ? MAIN FORM EVENTS
frappe.ui.form.on('Expense Claim', {
    refresh(frm) {
        create_payment_entry_button(frm);
        fetch_commute_data(frm);
    },
    employee: fetch_commute_data,
    company: fetch_commute_data,
    project(frm) {
        setCampaignFromProject(frm);
    }
});

// ? CHILD TABLE EVENTS
frappe.ui.form.on("Expense Claim Detail", {
    expenses_add(frm, cdt, cdn) {
        reset_commute_fields(cdt, cdn);
        const grid_row = frm.fields_dict.expenses.grid.get_row(cdn);
        if (grid_row) hide_commute_fields(grid_row);
    },
    expense_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const grid_row = frm.fields_dict.expenses.grid.get_row(cdn);
        if (grid_row) toggle_commute_fields(frm, grid_row, row);
    }
});

// ? CREATE PAYMENT ENTRY BUTTON
function create_payment_entry_button(frm) {
    if (frm.doc.docstatus !== 0 || frm.doc.workflow_state !== "Sent to Accounting Team") return;

    frm.page.actions.parent().remove();

    frm.add_custom_button(__('Create Payment Entry'), () => {
        if (frm.doc.approval_status !== "Approved") {
            frappe.throw(__('Expense Claim must be approved before creating a payment entry.'));
        }

        const proceed = () => {
            frm.set_value("workflow_state", "Expense Claim Submitted");
            frm.savesubmit().then(() => frm.events.make_payment_entry(frm));
        };

        if (!frm.doc.payable_account) {
            const d = new frappe.ui.Dialog({
                title: __('Create Payment Entry'),
                fields: [{
                    fieldtype: 'Link',
                    fieldname: 'payable_account',
                    label: __('Payable Account'),
                    options: 'Account',
                    reqd: 1,
                    get_query: () => frm.fields_dict["payable_account"].get_query()
                }],
                primary_action_label: __('Create'),
                primary_action(values) {
                    frm.set_value("payable_account", values.payable_account);
                    d.hide();
                    proceed();
                }
            });
            d.show();
        } else {
            proceed();
        }
    });
}

// ? FETCH COMMUTE DATA AND INITIALIZE EVENTS
function fetch_commute_data(frm) {
    const { employee, company } = frm.doc;
    if (!employee || !company) return;

    frappe.call({
        method: "prompt_hr.py.expense_claim.get_data_from_expense_claim_as_per_grade",
        args: { employee, company },
        callback: ({ message }) => {
            if (!message?.success) return;

            const commuteData = {
                public: message.data.allowed_local_commute_public || [],
                non_public: message.data.allowed_local_commute_non_public || []
            };
            const key = `commute_options_${employee}_${company}`;
            localStorage.setItem(key, JSON.stringify(commuteData));

            // ? ATTACH CLICK HANDLERS TO COMMUTE FIELDS
            ["custom_mode_of_vehicle", "custom_type_of_vehicle", "custom_km"].forEach(field => {
                apply_click_event_on_field(frm, "expenses", field, (row_doc) => {
                    const grid_row = frm.fields_dict.expenses.grid.get_row(row_doc.name);
                    if (grid_row) toggle_commute_fields(frm, grid_row, row_doc);
                }, true);
            });

            // ? ATTACH FORM OPEN LOGIC TO UPDATE VISIBILITY
            frm.fields_dict.expenses.grid.wrapper.on("click", ".grid-row", function () {
                const row_name = $(this).data("name");
                const grid_row = frm.fields_dict.expenses.grid.get_row(row_name);
                if (grid_row?.grid_form) {
                    grid_row.grid_form.on("form_render", () => {
                        toggle_commute_fields(frm, grid_row, grid_row.doc);
                    });
                }
            });

            // ? HANDLE ALREADY ADDED ROWS
            frm.doc.expenses?.forEach(row => {
                const grid_row = frm.fields_dict.expenses.grid.get_row(row.name);
                if (grid_row) toggle_commute_fields(frm, grid_row, row);
            });
        }
    });
}

// ? FUNCTION To SHOW/HIDE COMMUTE FIELDS BASED ON EXPENSE TYPE
function toggle_commute_fields(frm, grid_row, row) {
    if (!row || !grid_row) return;

    const is_local = row.expense_type === "Local Commute";

    if (is_local) {
        show_commute_fields(grid_row);
        update_type_of_vehicle_options(frm, row.custom_mode_of_vehicle);
    } else {
        reset_commute_fields(row.doctype, row.name);
        hide_commute_fields(grid_row);
    }
}

// ? FUNCTION To RESET FIELDS IF NOT LOCAL COMMUTE
function reset_commute_fields(cdt, cdn) {
    frappe.model.set_value(cdt, cdn, "custom_mode_of_vehicle", "");
    frappe.model.set_value(cdt, cdn, "custom_type_of_vehicle", "");
    frappe.model.set_value(cdt, cdn, "custom_km", "");
}

// ? FUNCTION To UPDATE VEHICLE OPTIONS BASED ON MODE
function update_type_of_vehicle_options(frm, mode) {
    const key = `commute_options_${frm.doc.employee}_${frm.doc.company}`;
    const stored = localStorage.getItem(key);
    if (!stored) return;

    const commuteData = JSON.parse(stored);
    const options = ["", ...(mode === "Public" ? commuteData.public : commuteData.non_public || [])];

    frm.fields_dict.expenses.grid.update_docfield_property("custom_type_of_vehicle", "options", options);
}

// ? FUNCTION To HIDE FIELDS
function hide_commute_fields(grid_row) {
    ["custom_mode_of_vehicle", "custom_type_of_vehicle", "custom_km"].forEach(fieldname => {
        grid_row.set_field_property(fieldname, "hidden", true);
        grid_row.set_field_property(fieldname, "read_only", true);
    });
}

// ? FUNCTION To SHOW FIELDS
function show_commute_fields(grid_row) {
    ["custom_mode_of_vehicle", "custom_type_of_vehicle", "custom_km"].forEach(fieldname => {
        grid_row.set_field_property(fieldname, "hidden", false);
        grid_row.set_field_property(fieldname, "read_only", false);
    });
}

// ? FUNCTION To ATTACH CLICK HANDLER TO CHILD TABLE FIELDS
function apply_click_event_on_field(frm, parent_field, target_field, callback, is_child_table = false) {
    frappe.after_ajax(() => {
        if (!is_child_table) return;

        const grid = frm.fields_dict[parent_field]?.grid;
        if (!grid?.wrapper) return;

        grid.wrapper.off(`click.${target_field}`).on(`click.${target_field}`, `[data-fieldname="${target_field}"]`, function () {
            const row_doc = $(this).closest(".grid-row").data("doc");
            if (row_doc) callback(row_doc);
        });
    });
}

// ? PLACEHOLDER FUNCTION IF YOU WANT TO LINK CAMPAIGN TO PROJECT
function setCampaignFromProject(frm) {
    // Add your logic here if needed
}

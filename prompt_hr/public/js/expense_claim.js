frappe.ui.form.on('Expense Claim', {
    refresh(frm) {
        create_payment_entry_button(frm);
        fetch_commute_data(frm);
    },
    employee(frm) {
        fetch_commute_data(frm);
    },
    company(frm) {
        fetch_commute_data(frm);
    },
    project(frm) {
        setCampaignFromProject(frm);
    }
});

frappe.ui.form.on("Expense Claim Detail", {
    custom_mode_of_vehicle(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        update_type_of_vehicle_options(frm, row.custom_mode_of_vehicle);
    },
    expenses_add(frm, cdt, cdn) {
        // Clear custom_mode_of_vehicle when new row is added
        frappe.model.set_value(cdt, cdn, "custom_mode_of_vehicle", "");
    }
});

function create_payment_entry_button(frm) {
    if (frm.doc.docstatus === 0 && frm.doc.workflow_state === "Sent to Accounting Team") {
        // Remove default submit/save buttons to avoid confusion
        frm.page.actions.parent().remove();

        frm.add_custom_button(__('Create Payment Entry'), () => {
            if (frm.doc.approval_status !== "Approved") {
                frappe.throw(__('Expense Claim must be approved before creating a payment entry.'));
                return;
            }
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
                        frm.set_value("workflow_state", "Expense Claim Submitted");
                        frm.save()
                            .then(() => frm.savesubmit())
                            .then(() => frm.events.make_payment_entry(frm));
                        d.hide();
                    }
                });
                d.show();
            } else {
                frm.set_value("workflow_state", "Expense Claim Submitted");
                frm.savesubmit().then(() => frm.events.make_payment_entry(frm));
            }
        });
    }
}

function fetch_commute_data(frm) {
    const { employee, company } = frm.doc;
    if (!employee || !company) return;

    frappe.call({
        method: "prompt_hr.py.expense_claim.get_data_from_expense_claim_as_per_grade",
        args: { employee, company },
        callback: (res) => {
            if (res.message?.success) {
                const commuteData = {
                    public: res.message.data.allowed_local_commute_public || [],
                    non_public: res.message.data.allowed_local_commute_non_public || []
                };
                const key = `commute_options_${employee}_${company}`;
                localStorage.setItem(key, JSON.stringify(commuteData));

                // Validate existing rows in child table 'expenses'
                if (frm.doc.expenses && frm.doc.expenses.length) {
                    frm.doc.expenses.forEach(row => {
                        const mode = row.custom_mode_of_vehicle || "";
                        const type = row.custom_type_of_vehicle || "";

                        // Allowed options based on mode
                        const allowedTypes = {
                            "Public": commuteData.public,
                            "Non Public": commuteData.non_public,
                            "": [""]
                        };

                        const allowedTypeOptions = allowedTypes[mode] || [];

                        // If current custom_type_of_vehicle is not allowed OR mode itself is invalid, clear both fields
                        if (!allowedTypeOptions.includes(type) || !(mode in allowedTypes)) {
                            frappe.model.set_value(row.doctype, row.name, "custom_mode_of_vehicle", "");
                            frappe.model.set_value(row.doctype, row.name, "custom_type_of_vehicle", "");
                        }
                    });
                    frm.refresh_field("expenses");
                }

                // Apply click event on child table field
                apply_click_event_on_field(frm, "expenses", "custom_type_of_vehicle", (row) => {
                    update_type_of_vehicle_options(frm, row.custom_mode_of_vehicle);
                }, true);
            }
        }
    });
}


function apply_click_event_on_field(frm, parent_field, target_field, callback, is_child_table = false) {
    frappe.after_ajax(() => {
        if (is_child_table) {
            const grid = frm.fields_dict[parent_field]?.grid;
            if (!grid?.wrapper) return;
            grid.wrapper.off("click.custom_event").on("click.custom_event", `[data-fieldname="${target_field}"]`, function () {
                const row = $(this).closest(".grid-row").data("doc");
                if (row) callback(row, target_field);
            });
        } else {
            const field = frm.fields_dict[target_field];
            if (field?.input) {
                $(field.input).off("click.custom_event").on("click.custom_event", () => callback(frm.doc[target_field], target_field));
            }
        }
    });
}

function update_type_of_vehicle_options(frm, mode) {
    const key = `commute_options_${frm.doc.employee}_${frm.doc.company}`;
    const stored = localStorage.getItem(key);
    if (!stored) return;

    const commuteData = JSON.parse(stored);
    const options_map = {
        "": [""],
        "Public": commuteData.public || [],
        "Non Public": commuteData.non_public || []
    };
    const options = ["", ... (options_map[mode] || [])];

    frm.fields_dict.expenses.grid.update_docfield_property("custom_type_of_vehicle", "options", options);
    frm.fields_dict.expenses.grid.refresh();
}

function setCampaignFromProject(frm) {
    // Placeholder for your logic when project changes
}

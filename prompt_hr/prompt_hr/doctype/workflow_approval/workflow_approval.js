// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Workflow Approval", {
    applicable_doctype: function (frm) {
        frm.events.update_field_options(frm);
    },

    refresh: function (frm) { 
        frm.events.update_field_options(frm);
    },
    update_field_options: function (frm) {
        var doc = frm.doc;
        if (!doc.applicable_doctype) return;

        frappe.model.with_doctype(doc.applicable_doctype, () => {
            const field_map = frappe
                .get_meta(doc.applicable_doctype)
                .fields
                .filter((field) => !frappe.model.no_value_type.includes(field.fieldtype))
                .map((field) => {
                    return {
                        label: field.label || field.fieldname,
                        value: field.fieldname
                    };
                });

            // Store it on frm for reuse in child logic
            frm._field_map = field_map;

            const labels = field_map.map(f => f.label);
            frm.fields_dict.workflow_approval_criteria.grid.update_docfield_property(
                "field_label",
                "options",
                [""].concat(labels)
            );
        });
    },
    
});

// frappe.ui.form.on("Workflow Approval Criteria", {
//     field_label: function (frm, cdt, cdn) {
//         let row = locals[cdt][cdn];
//         if (!frm._field_map || !row.field_label) return;

//         let match = frm._field_map.find(f => f.label === row.field_label);
//         if (match) {
//             row.field_name = match.value;
//             frm.fields_dict.workflow_approval_criteria.grid.refresh();
//         }
//     }
// });

frappe.ui.form.on("Workflow Approval Criteria", {
    field_label: function (frm, cdt, cdn) {
                let row = locals[cdt][cdn];
                if (!frm._field_map || !row.field_label) return;
        
                let match = frm._field_map.find(f => f.label === row.field_label);
                if (match) {
                    row.field_name = match.value;
                    frm.fields_dict.workflow_approval_criteria.grid.refresh();
                }
            },
    set_expected_value: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.field_label || !frm._field_map) {
            frappe.msgprint("Please select a field first.");
            return;
        }

        const fieldMeta = frm._field_map.find(f => f.label === row.field_label);
        if (!fieldMeta) return;

        frappe.model.with_doctype(frm.doc.applicable_doctype, () => {
            const meta = frappe.get_meta(frm.doc.applicable_doctype);
            const field = meta.fields.find(f => f.fieldname === fieldMeta.value);
            if (!field) return;

            // Define dialog input field config
            let dialog_field = { fieldname: "value", label: "Value", reqd: 1 };

            if (field.fieldtype === "Date") {
                dialog_field.fieldtype = "Date";
            } else if (field.fieldtype === "Datetime") {
                dialog_field.fieldtype = "Datetime";
            } else if (field.fieldtype === "Link" && field.options) {
                dialog_field.fieldtype = "Link";
                dialog_field.options = field.options;
            } else if (field.fieldtype === "Select" && field.options) {
                dialog_field.fieldtype = "Select";
                dialog_field.options = field.options;
            } else if (field.fieldtype === "Check") {
                dialog_field.fieldtype = "Select";
                dialog_field.options = ["1", "0"];
            } else {
                dialog_field.fieldtype = "Data";
            }

            // Show dialog
            const d = new frappe.ui.Dialog({
                title: `Set Expected Value for ${field.label}`,
                fields: [dialog_field],
                primary_action_label: "Set",
                primary_action(values) {
                    frappe.model.set_value(cdt, cdn, "expected_value", values.value);
                    d.hide();
                }
            });

            d.show();
        });
    }
});


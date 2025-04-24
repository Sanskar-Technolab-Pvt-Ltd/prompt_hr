frappe.ui.form.on("Workflow Approval", {
	clear_property_table: function (frm) {
		let table = "workflow_criteria";
		frm.clear_table(table);
		frm.refresh_field(table);
		frm.fields_dict[table].grid.wrapper.find(".grid-add-row").hide();
	},

	refresh: function (frm) {
		let table = "workflow_approval_criteria";
		if (!table) return;
		frm.fields_dict[table].grid.wrapper.find(".grid-add-row").hide();
		frm.events.setup_workflow_criteria_button(frm, table);
	},

	setup_workflow_criteria_button: function (frm, table) {
		frm.fields_dict[table].grid.add_custom_button(__("Add Workflow Criteria"), () => {
			if (!frm.doc.applicable_doctype) {
				frappe.msgprint(__("Please select Target DocType first."));
				return;
			}

			const allowed_fieldtypes = [
				"Data", "Select", "Link", "Date", "Datetime", "Check", "Int", "Float", "Currency"
			];

			const allowed_fields = [];
			frappe.model.with_doctype(frm.doc.applicable_doctype, () => {
				const meta = frappe.get_meta(frm.doc.applicable_doctype);
				meta.fields.forEach((d) => {
					if (
						d.fieldname &&
						d.label &&
						!["Section Break", "Column Break", "Table", "Button", "HTML"].includes(d.fieldtype) &&
						allowed_fieldtypes.includes(d.fieldtype) &&
						!d.hidden
					) {
						allowed_fields.push({
                            label:d.label,
							// label: `${d.label}`,
							value: d.fieldname,
							fieldtype: d.fieldtype,
							options: d.options
						});
					}
				});
				show_dialog(frm, table, allowed_fields);
			});
		});
	},
});

var show_dialog = function (frm, table, field_meta_list) {
    let d = new frappe.ui.Dialog({
        title: "Add Workflow Criteria",
        fields: [
            {
                fieldname: "field_label",
                label: __("Select Field"),
                fieldtype: "Autocomplete",
                options: field_meta_list.map(f => f.label), // Only show labels
            },
            { fieldname: "field_name", fieldtype: "Data", label: __("Field Name"), read_only: 1 },
            {
                fieldname: "expected_value",
                fieldtype: "Data",
                label: __("Expected Value")
            }
        ],
        primary_action_label: __("Add to Criteria"),
        primary_action: () => {
            let field_name = d.get_value("field_name");
            let expected_value = d.get_value("expected_value");

            if (field_name && expected_value !== undefined) {
                frm.add_child(table, {
                    field_label: d.get_value("field_label"),
                    field_name: field_name,
                    expected_value: expected_value
                });
                frm.refresh_field(table);
                frappe.show_alert({ message: __("Added to criteria"), indicator: "green" });

                // Clear dialog inputs
                d.set_value("field_label", "");
                d.set_value("field_name", "");
                d.set_value("expected_value", "");
                d.get_primary_btn().attr("disabled", true);
            } else {
                frappe.show_alert({ message: __("Value missing"), indicator: "red" });
            }
        },
        secondary_action_label: __("Close"),
        secondary_action: () => d.hide(),
    });

    d.fields_dict["field_label"].df.onchange = () => {
        let selected_label = d.get_value("field_label");
        if (!selected_label) return;

        let matched_field = field_meta_list.find(f => f.label === selected_label);
        if (!matched_field) return;

        d.set_value("field_name", matched_field.value);

        // Render dynamic field based on matched_field
        render_dynamic_field(d, matched_field.fieldtype || "Data", matched_field.options || "", "expected_value");
        d.get_primary_btn().attr("disabled", false);
    };

    d.get_primary_btn().attr("disabled", true);
    d.show();
};

var render_dynamic_field = function (d, fieldtype, options, fieldname) {
    var dynamic_field = frappe.ui.form.make_control({
        df: {
            fieldtype: fieldtype,
            fieldname: fieldname,
            options: options || "",
            label: __("Expected Value"),
        },
        parent: d.fields_dict[fieldname].wrapper,
        only_input: false,
    });
    dynamic_field.make_input();
    d.replace_field(fieldname, dynamic_field.df);
};




frappe.ui.form.on("Travel Budget", {
	refresh(frm) {
		// Apply custom click handler to set dynamic options
		apply_click_event_on_field(
			frm,
			"local_commute",                 // Child table fieldname
			"type_of_commute",              // Field to dynamically update
			(row) => update_type_of_commute_options(frm, row.mode_of_commute),
			true                            // Is child table
		);
	},
});

// ? FUNCTION To update options for `type_of_commute` field based on selected `mode_of_commute`
function update_type_of_commute_options(frm, mode) {
	const options_map = {
		"": [""],
		"Public": ["Auto", "Bus", "Taxi"],
		"Non Public": ["Car", "Bike"]
	};

	const options = ["", ...(options_map[mode] || [])];

	// ? UPDATE OPTIONS IN CHILD TABLE FIELD
	frm.fields_dict.local_commute.grid.update_docfield_property("type_of_commute", "options", options);
	frm.fields_dict.local_commute.grid.refresh();
}

// ? FUNCTION To attach a click event to a specific field in a child table or main form
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

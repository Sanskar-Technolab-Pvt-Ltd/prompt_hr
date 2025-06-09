frappe.ui.form.on("Travel Budget", {
	refresh(frm) {
		// ? APPLY CUSTOM CLICK HANDLER TO SET DYNAMIC OPTIONS
		prompt_hr.utils.apply_click_event_on_field(
			frm,
			"local_commute",              
			"mode_of_commute",            
			(row) => update_type_of_commute_options(frm, row.mode_of_commute),
			true                           
		);
	},
});

// ? FUNCTION TO UPDATE OPTIONS FOR `TYPE_OF_COMMUTE` FIELD BASED ON SELECTED `MODE_OF_COMMUTE`
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


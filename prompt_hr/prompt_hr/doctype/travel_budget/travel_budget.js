frappe.ui.form.on("Travel Budget", {
	refresh(frm) {
		// ? APPLY DYNAMIC OPTIONS TO CHILD TABLE
		prompt_hr.utils.apply_click_event_on_field(
			frm,
			"local_commute",
			"mode_of_commute",
			(row) => update_type_of_commute_options(frm, row.mode_of_commute),
			true
		);

		// ? ADD GRADE-WISE ROW BUTTON
		frm.add_custom_button("Add Grade-Wise Commutes", () => {
			open_dynamic_grade_dialog(frm);
		});
	}
});

// ? UPDATE COMMUTE TYPES BASED ON MODE
function update_type_of_commute_options(frm, mode) {
	const options_map = {
		"": [""],
		"Public": ["Auto", "Bus", "Taxi", "Train", "Flight"],
		"Non Public": ["Car", "Bike"]
	};
	const options = ["", ...(options_map[mode] || [])];

	frm.fields_dict.local_commute.grid.update_docfield_property("type_of_commute", "options", options);
	frm.fields_dict.local_commute.grid.refresh();
}

// ? SIMPLE GRADE DIALOG
function open_dynamic_grade_dialog(frm) {
	const child_tables = frm.meta.fields.filter(df => df.fieldtype === "Table");

	if (child_tables.length === 0) {
		frappe.msgprint("No child tables found in this form.");
		return;
	}

	const dialog = new frappe.ui.Dialog({
		title: "Add Grade-Wise Rows",
		fields: [
			{
				fieldname: "child_table",
				label: "Select Child Table",
				fieldtype: "Select",
				options: ["", ...child_tables.map(df => df.fieldname)],
				reqd: 1,
				change: () => load_child_fields(dialog, frm, child_tables)
			}
		],
		primary_action_label: "Add Rows",
		primary_action: (values) => add_grade_rows(dialog, frm, values)
	});

	dialog.show();
}

// ? LOAD CHILD TABLE FIELDS DYNAMICALLY
function load_child_fields(dialog, frm, child_tables) {
	const table_fieldname = dialog.get_value("child_table");
	if (!table_fieldname) return;

	// ? GET CHILD DOCTYPE
	const child_doctype = get_child_doctype(frm, table_fieldname);
	if (!child_doctype) {
		frappe.msgprint("Unable to find child doctype");
		return;
	}

	// ? LOAD DOCTYPE AND REBUILD DIALOG
	frappe.model.with_doctype(child_doctype, () => {
		rebuild_dialog_with_fields(dialog, child_doctype, table_fieldname);
	});
}

// ? GET CHILD DOCTYPE USING MULTIPLE METHODS
function get_child_doctype(frm, table_fieldname) {
	// ? METHOD 1: FROM FIELD META OPTIONS
	const field_meta = frm.meta.fields.find(df => df.fieldname === table_fieldname);
	if (field_meta?.options) return field_meta.options;

	// ? METHOD 2: FROM GRID
	if (frm.fields_dict[table_fieldname]?.grid?.docfield?.options) {
		return frm.fields_dict[table_fieldname].grid.docfield.options;
	}

	return null;
}

// ? REBUILD DIALOG WITH CHILD TABLE FIELDS
function rebuild_dialog_with_fields(dialog, child_doctype, table_fieldname) {
	// ? GET CHILD FIELDS (EXCLUDE SYSTEM FIELDS)
	const child_fields = frappe.meta.get_docfields(child_doctype).filter(df =>
		!["Section Break", "Column Break", "Table", "Button", "HTML"].includes(df.fieldtype) &&
		!df.fieldname.startsWith('_') &&
		!["name", "idx", "grade"].includes(df.fieldname)
	);

	// ? BUILD NEW FIELD LIST
	const new_fields = [
		{
			fieldname: "selected_table",
			label: "Selected Table",
			fieldtype: "Data",
			read_only: 1,
			default: table_fieldname
		},
		{
			fieldname: "section_1",
			fieldtype: "Section Break",
			label: "Grade Input"
		},
		{
			fieldname: "grade_input",
			label: "Grades (comma-separated)",
			fieldtype: "Small Text",
			reqd: 1,
			description: "Enter grades: A, B, C, Manager, Executive"
		}
	];

	// ? ADD CHILD FIELDS IF ANY EXIST
	if (child_fields.length > 0) {
		new_fields.push({
			fieldname: "section_2",
			fieldtype: "Section Break",
			label: "Field Values (Optional)"
		});

		child_fields.forEach(df => {
			new_fields.push({
				fieldname: df.fieldname,
				label: df.label || df.fieldname,
				fieldtype: df.fieldtype === "Text Editor" ? "Small Text" : df.fieldtype,
				options: df.options,
				default: df.default || "",
				reqd: 0
			});
		});
	}

	// ? REBUILD DIALOG
	dialog.fields = new_fields;
	dialog.fields_dict = {};
	dialog.body.innerHTML = "";
	dialog.make();
}

// ? ADD ROWS WITH GRADE DATA
function add_grade_rows(dialog, frm, values) {
	const table_fieldname = values.selected_table || values.child_table;
	if (!table_fieldname) return;

	const grades = values.grade_input?.split(",").map(g => g.trim()).filter(Boolean) || [];
	if (grades.length === 0) {
		frappe.msgprint("Please enter at least one grade.");
		return;
	}

	const child_doctype = get_child_doctype(frm, table_fieldname);
	if (!child_doctype) return;

	// ? GET CHILD FIELDS
	const child_fields = frappe.meta.get_docfields(child_doctype).filter(df =>
		!["Section Break", "Column Break", "Table", "Button", "HTML"].includes(df.fieldtype) &&
		!df.fieldname.startsWith('_') &&
		!["name", "idx"].includes(df.fieldname)
	);

	// ? ADD ROWS FOR EACH GRADE
	grades.forEach(grade => {
		const row = frm.add_child(table_fieldname);

		child_fields.forEach(df => {
			if (df.fieldname === "grade") {
				row[df.fieldname] = grade;
			} else if (values[df.fieldname] !== undefined && values[df.fieldname] !== "") {
				row[df.fieldname] = values[df.fieldname];
			}
		});
	});

	frm.save().then(() => {
    frm.refresh();
    frappe.show_alert(`Added ${grades.length} rows to ${table_fieldname}`, 5);
    dialog.hide();
});
}
frappe.provide("prompt_hr.utils");

/**
 * ? DYNAMICALLY ATTACHES A CLICK EVENT TO FIELDS IN A FORM, EITHER IN CHILD TABLES OR REGULAR FIELDS.
 *
 * @param {frappe.ui.Form} frm - The Frappe form object.
 * @param {string|null} parent_fieldname - The fieldname of the child table (if applicable). Use null for main form fields.
 * @param {string} target_fieldname - The fieldname on which the click event should be applied.
 * @param {function} callback - The callback function to execute when the field is clicked.
 * @param {boolean} is_child_table - Flag indicating if the target is part of a child table (default: false).
 */
prompt_hr.utils.apply_click_event_on_field = function (
	frm,
	parent_fieldname,
	target_fieldname,
	callback,
	is_child_table = false
) {
	frappe.after_ajax(() => {
		if (is_child_table) {
			const grid = frm.fields_dict[parent_fieldname]?.grid;
			if (!grid || !grid.wrapper) return;

			grid.wrapper.off(`click.${target_fieldname}`);
			grid.wrapper.on("click", `[data-fieldname="${target_fieldname}"]`, function () {
				const row = $(this).closest(".grid-row").data("doc");
				if (row && typeof callback === "function") {
					callback(row, target_fieldname);
				}
			});
		} else {
			const field = frm.fields_dict[target_fieldname];
			if (field?.input) {
				$(field.input).off("click").on("click", () => {
					if (typeof callback === "function") {
						callback(frm.doc[target_fieldname], target_fieldname);
					}
				});
			}
		}
	});
};

/**
 * ? SETS MULTIPLE FIELD PROPERTIES (LIKE HIDDEN, READ_ONLY, ETC.) FOR A GIVEN LIST OF FIELDS IN A GRID ROW.
 *
 * @param {frappe.ui.form.GridRow} grid_row - The grid row object where field properties need to be updated.
 * @param {string[]} fields - List of fieldnames to apply the properties on.
 * @param {Object} props - Key-value map of properties to be applied (e.g., { hidden: true, read_only: true }).
 */
prompt_hr.utils.set_field_properties_bulk = function (grid_row, fields = [], props = {}) {
	fields.forEach(fieldname => {
		Object.entries(props).forEach(([prop, value]) => {
			grid_row.set_field_property(fieldname, prop, value);
		});
	});
};

/**
 * ? SHOWS OR HIDES FIELDS IN A CHILD TABLE ROW BASED ON A TRIGGER FIELD'S VALUE.
 *
 * @param {Object} config - Configuration object for toggling fields.
 * @param {frappe.ui.form.GridRow} config.grid_row - The current grid row.
 * @param {Object} config.row - The current row data (locals).
 * @param {string} config.trigger_field - Fieldname that triggers the toggle.
 * @param {string} config.trigger_value - The value that activates the toggle condition.
 * @param {string[]} config.affected_fields - List of fields to show/hide or toggle.
 * @param {Object} config.on_true_props - Properties to apply when the condition matches (e.g., { hidden: false, read_only: false }).
 * @param {string[]} config.on_false_reset_fields - Fields to reset when condition is false.
 * @param {function} [config.reset_fn=frappe.model.set_value] - Optional function to reset fields (default is frappe.model.set_value).
 * @param {frappe.ui.Form} [config.form_context=null] - Optional form object for additional context or custom logic.
 * @param {function} [config.on_true_callback=null] - Optional callback to execute if the condition is true.
 */
prompt_hr.utils.toggle_child_row_fields = function ({
	grid_row,
	row,
	trigger_field,
	trigger_value,
	affected_fields,
	on_true_props,
	on_false_reset_fields,
	on_true_callback,
	on_false_callback,
	reset_fn,
	form_context
}) {
	const match = row[trigger_field] === trigger_value;
	console.log(match)
	if (match) {
		
		prompt_hr.utils.set_field_properties_bulk(grid_row, affected_fields, on_true_props);
		if (on_true_callback) on_true_callback();
	} else {
		on_false_reset_fields.forEach(field => {
			reset_fn(row.doctype, row.name, field, "");
			if (on_false_callback) on_false_callback(); 
		});
		prompt_hr.utils.set_field_properties_bulk(grid_row, affected_fields, { hidden: true, read_only: true });
		// 👈 make sure this exists
	}
}


/**
 * ? UPDATES THE OPTIONS OF A SELECT FIELD INSIDE A CHILD TABLE.
 *
 * @param {frappe.ui.Form} frm - The Frappe form object.
 * @param {Object} config - Configuration object.
 * @param {string} config.table_field - Fieldname of the child table.
 * @param {string} config.fieldname - Fieldname inside the child table whose options need to be updated.
 * @param {string[]} config.options - Array of options to be set (e.g., ['Option 1', 'Option 2']).
 */
prompt_hr.utils.update_select_field_options = function (frm, {
	table_field,
	fieldname,
	options = []
}) {
	if (!frm.fields_dict[table_field]) return;
	const grid = frm.fields_dict[table_field].grid;
	grid.update_docfield_property(fieldname, "options", ["", ...options]);
};


/**
 * Dynamically updates the visibility of columns in a child table grid in a Frappe form.
 *
 * If specific fields are provided, only those fields will be hidden. If no fields are provided,
 * it resets the visibility of all columns in the child table based on the metadata.
 *
 * This function also ensures the grid's visible columns and headers are recalculated and re-rendered.
 *
 * @namespace prompt_hr.utils
 * @function update_child_table_columns
 *
 * @param {frappe.ui.Form} frm - The Frappe form object.
 * @param {string} table - The fieldname of the child table in the form.
 * @param {string[]|null} [fields=null] - Optional array of fieldnames to hide. If null, all fields will be reset to their default visibility.
 *
 * @example
 * // Hide specific columns in a child table
 * prompt_hr.utils.update_child_table_columns(frm, "product_core_details", ["defect", "solution"]);
 *
 * @example
 * // Reset all columns in the child table to their default visibility
 * prompt_hr.utils.update_child_table_columns(frm, "product_core_details");
 */

prompt_hr.utils.update_child_table_columns = function (frm, table, fields = null) {
	const grid = frm.get_field(table)?.grid;
	if (!grid) return;

	const parent_doctype = frm.doctype;
	const child_doctype = frm.fields_dict[table].df.options;

	if (fields && fields.length) {
		fields.forEach((fieldname) => {
			if (grid.fields_map[fieldname]) {
				grid.fields_map[fieldname].hidden = 1;
				frm.fields_dict[table].grid.update_docfield_property(fieldname, "hidden", 1);
			}
		});
	} else {
		frappe.meta.get_docfields(child_doctype).forEach((df) => {
			const field = grid.fields_map[df.fieldname];
			if (field) {
				const original_df = frappe.meta.get_docfield(
					child_doctype,
					df.fieldname,
					parent_doctype
				);
				field.hidden = original_df?.hidden || 0;
				frm.fields_dict[table].grid.update_docfield_property(df.fieldname, "hidden", 0);
			}
		});
	}

	grid.visible_columns = undefined;
	grid.setup_visible_columns();

	if (grid.header_row) {
		grid.header_row.wrapper.remove();
		delete grid.header_row;
		grid.make_head();
	}

	grid.grid_rows.forEach((row) => {
		if (row.open_form_button) {
			row.open_form_button.parent().remove();
			delete row.open_form_button;
		}
		if (row.columns) {
			Object.keys(row.columns).forEach((col) => {
				if (row.columns[col]) {
					row.columns[col].remove();
				}
			});
			row.columns = [];
		}
		row.render_row();
	});
};
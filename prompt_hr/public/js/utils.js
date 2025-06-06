

frappe.provide("prompt_hr.utils");

/**
 * Dynamically attaches a click event to fields in a form, either in child tables or regular fields.
 *
 * @param {frappe.ui.Form} frm - The Frappe form object.
 * @param {string|null} parent_fieldname - The fieldname of the child table (if applicable). Use null for normal fields.
 * @param {string} target_fieldname - The actual field to bind the click event on.
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

			grid.wrapper.on("click", `[data-fieldname="${target_fieldname}"]`, function () {
				const row = $(this).closest(".grid-row").data("doc");
				if (row && typeof callback === "function") {
					callback(row, target_fieldname);
				}
			});
		} else {
			const field = frm.fields_dict[target_fieldname];
			if (field?.input) {
				$(field.input).on("click", () => {
					if (typeof callback === "function") {
						callback(frm.doc[target_fieldname], target_fieldname);
					}
				});
			}
		}
	});
};

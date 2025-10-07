// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Organization Documents", {
	refresh(frm) {
        frm.fields_dict["access_criteria"].grid.get_field("select_doctype").get_query = function() {
            return {
                filters: [
                    ["name", "in", ["Department", "Employee Grade", "Designation","Address","Employment Type"]]
                ]
            };
        };
	},
});

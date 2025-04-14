// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Confirmation Evaluation Form", {
	refresh: function(frm) {
        
        frm.fields_dict['table_txep'].grid.get_field('parameters').get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            console.log("get_query (refresh) - Category:", row.category);
            if (row.category) {
                return {
                    filters: [
                        ['category', '=', row.category]
                    ]
                };
            }
            return { filters: {} }; 
        };
        frm.fields_dict['table_txep'].grid.refresh();
    }
});

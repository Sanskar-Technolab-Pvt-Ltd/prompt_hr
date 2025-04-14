// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Confirmation Evaluation Form", {
// 	refresh(frm) {

// 	},
// });

// frappe.ui.form.on("table_txep", {
//     category: function(frm, cdt, cdn) {
//         set_parameter_filter(frm);
//         frm.refresh_field('table_txep');
//     },
//     table_txep_add: function(frm, cdt, cdn) {
//         set_parameter_filter(frm);
//     }
// });


// function set_parameter_filter(frm) {
//     frm.fields_dict['table_txep'].grid.get_field('parameters').get_query = function(doc, cdt, cdn) {
//         let row = locals[cdt][cdn];
//         return {
//             filters: [
//                 ['category', '=', row.category]
//             ]
//         };
//     };
// }
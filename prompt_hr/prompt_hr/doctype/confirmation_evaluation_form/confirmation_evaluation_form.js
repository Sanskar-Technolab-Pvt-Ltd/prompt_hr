// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Confirmation Evaluation Form", {
	refresh: function(frm) {
        
        // * Making the rh_rating and dh_rating fields read-only based on the logged-in user is either the reporting manager or head of department
        const user = frappe.session.user;
        const reporting_manager = frm.doc.reporting_manager;
        const head_of_department = frm.doc.hod;

        console.log("User:", user);

        frappe.call({
            "method": "frappe.client.get_value",
            "args": {
                "doctype": "Employee",
                "filters": {
                    "user_id": user
                },
                "fieldname": ["name"]
            },
            "callback": function(response) {
                if (response.message) {
                    const user_employee_name = response.message.name;
            
                    if (user_employee_name === reporting_manager) {
                        console.log("User is Reporting Manager");
                        frm.fields_dict.table_txep.grid.update_docfield_property('rh_rating', 'read_only', 0);
                        frm.fields_dict.table_txep.grid.update_docfield_property('dh_rating', 'read_only', 1);

                    } else if (user_employee_name === head_of_department) {
                        console.log("User is Head of Department");
                        frm.fields_dict.table_txep.grid.update_docfield_property('dh_rating', 'read_only', 0);
                        frm.fields_dict.table_txep.grid.update_docfield_property('rh_rating', 'read_only', 1);

                    }else {
                        console.log("User is neither Reporting Manager nor Head of Department");
                        frm.fields_dict.table_txep.grid.update_docfield_property('rh_rating', 'read_only', 1);
                        frm.fields_dict.table_txep.grid.update_docfield_property('dh_rating', 'read_only', 1);
                        frm.fields_dict.table_txep.grid.update_docfield_property('remarks_if_any', 'read_only', 1);
                    }
                }
                
            }
        })

        // * Applying filters to the 'parameters' field in the 'table_txep' child table based on the selected 'category'
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
    },

    probation_status: function (frm) { 
        // *CALCULATING THE LAST DATE OF WORK FROM THE DATE WHEN PROBATION STATUS IS SET TO TERMINATE TO BASED ON THE NOTICE PERIOD DAYS

        if (frm.doc.probation_status === "Terminate") {
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "Employee",
                    filters: { name: frm.doc.employee },
                    fieldname: ["notice_number_of_days"]
                },
                callback: function (r) {
                    if (r.message) {
                        const notice_number_of_days = r.message.notice_number_of_days;
                        let today = frappe.datetime.get_today();
                        console.log("Today:", today);
                        const last_work_date = frappe.datetime.add_days(today, notice_number_of_days);
                        console.log("last work date", last_work_date, "after", notice_number_of_days, "days");


                        frm.set_value("last_work_date", last_work_date);
                    }
                }
            });
        
        }
    
    }
});

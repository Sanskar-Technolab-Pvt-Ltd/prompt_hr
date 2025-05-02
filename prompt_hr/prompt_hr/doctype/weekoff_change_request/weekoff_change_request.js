// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("WeekOff Change Request", {
    
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Employee',
                    filters: {
                        user_id: frappe.session.user
                    },
                    fieldname: ['name'],
                },
                callback: function(r) {
                    if (r.message && r.message.name) {
                        frm.set_value('employee', r.message.name);
                    }
                }
            });
        }
    },
	refresh(frm) {

        const user = frappe.session.user
        if (frm.doc.employee) {
            frappe.call({
                "method": "prompt_hr.prompt_hr.doctype.weekoff_change_request.weekoff_change_request.check_user_is_reporting_manager",
                "args": {
                    user_id: user,
                    requesting_employee_id: frm.doc.employee
                },
                callback: function (r) {
                    if (!r.message.error) {
                        if (r.message.is_rh) {
                            frm.set_df_property("status", "hidden", 0)
                        }
                    } else if (r.message.error) {
                        frappe.throw(r.message.message)
                    }
                }
            })
        }
        

    },
    
});
frappe.ui.form.on('WeekOff Request Details', {
    existing_weekoff_date: function (frm, cdt, cdn) {

        let child = locals[cdt][cdn];
        if (child.existing_weekoff_date) {
    
            frappe.call({
                method: "prompt_hr.prompt_hr.doctype.weekoff_change_request.weekoff_change_request.check_existing_date",
                args: {
                    employee_id: frm.doc.employee,
                    existing_date: child.existing_weekoff_date
                },
                callback: function (r) {
                    
                    if (!r.message.error) {
                        if (r.message.exists) {
                            let date_obj = new Date(child.existing_weekoff_date);
                            let day_name = date_obj.toLocaleString('en-US', { weekday: 'long' });
                            // frappe.model.set_value(cdt, cdn, 'existing_weekoff', day_name);
                            child.existing_weekoff = day_name
                            frm.refresh_field("weekoff_details")
                        } else {
                            frappe.model.set_value(cdt, cdn, 'existing_weekoff', '');
                            frappe.throw(`Date ${child.existing_weekoff_date} does not exist in Holiday List`)
                        
                        }
                    } else if (r.message.error) {
                        frappe.throw(`Error While Verifying Existing Date. ${r.message.message}`)
                    }
                }
            });
        }
    },

    new_weekoff_date: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.new_weekoff_date) {
            let date_obj = new Date(row.new_weekoff_date);
            let day_name = date_obj.toLocaleString('en-US', { weekday: 'long' });
            row.new_weekoff = day_name;
            frm.refresh_field('weekoff_details'); 
        }
        
    }
});
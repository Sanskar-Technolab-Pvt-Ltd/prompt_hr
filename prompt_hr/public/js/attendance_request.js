frappe.ui.form.on('Attendance Request', {
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.employee) {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Employee',
                    filters: {
                        user_id: frappe.session.user
                    },
                    fields: ['name', 'employee_name'],
                    limit_page_length: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value('employee', r.message[0].name);
                    }
                }
            });
        }
    },

    refresh: function (frm) {
        if (frm.doc.employee) {
            frappe.call({
                method: "prompt_hr.py.utils.check_user_is_reporting_manager",
                args: {
                    user_id: frappe.session.user,
                    requesting_employee_id: frm.doc.employee
                },
                callback: function (res) {
                    if (!res.message.error) {
                        if (res.message.is_rh) {
                            frm.set_df_property("custom_status", "hidden", 0)
                        }

                    } else if (res.message.error) {
                        frappe.throw(res.message.message)
                    }
                }
            })
        }

        if (frm.doc.company) {
            set_partial_day_option(frm)
        }
    },
    employee: function (frm) {
        
            set_partial_day_option(frm)
    
    }
});


function set_partial_day_option(frm) {
    console.log("Function Ran", frm.doc.company)

    frappe.call({
        method: 'prompt_hr.py.utils.fetch_company_name',
        args: {
            "prompt": 1
        },
        callback: function (res) {

            options = {
                "default_options": ['Work From Home', 'On Duty'],
                "prompt_options": ['Work From Home', 'On Duty', 'Partial Day']
            }

            if (!res.message.error && res.message.company_id == frm.doc.company){
                
                frm.set_df_property('reason', 'options', options["prompt_options"])
                
            }
            else if (res.message.error) {
                frappe.throw(res.message.message)
            }
            else {
                
                frm.set_df_property('reason', 'options', options["default_options"])
            }
        }
    })
}
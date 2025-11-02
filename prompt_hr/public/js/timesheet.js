frappe.ui.form.on("Timesheet", {
    setup: function(frm)
    {
        frm.fields_dict["time_logs"].grid.get_field("task").get_query = function (frm, cdt, cdn) {
			var child = locals[cdt][cdn];
			return {
				filters: {
					// project: child.project,
					status: ["!=", "Cancelled"],
				},
			};
		};
    },
    refresh(frm) {
        if (frm.doc.status === "Submitted" || frm.doc.status === "Requested for Unsubmission") {
            // Disable all fields
            frm.fields_dict && Object.keys(frm.fields_dict).forEach(fieldname => {

                frm.set_df_property(fieldname, "read_only", 1);
            });

            frm.fields_dict.timesheet_details?.grid?.df?.fields?.forEach(field => {
                frm.fields_dict.timesheet_details.grid.set_column_disp(field.fieldname, false);
            });

        } else {
            frm.fields_dict && Object.keys(frm.fields_dict).forEach(fieldname => {
                if (!["naming_series", "user", "start_date", "end_date", "employee_name", "department", "total_hours", "total_billable_hours", "base_total_billable_amount", "base_total_billed_amount", "base_total_costing_amount", "total_billed_hours", "total_billable_amount", "total_billed_amount", "total_costing_amount", "per_billed", "sales_invoice", "salary_slip", "status"].includes(fieldname)) {
                        frm.set_df_property(fieldname, "read_only", 0);
                }
            });

        }

    },
    // before_workflow_action: async (frm) => {
    //     const allowed_actions = ['Submit', 'Request for Unsubmit Timesheet'];
    //     const action = frm.selected_workflow_action;

    //     if (allowed_actions.includes(action)){
    //         let promise = new Promise ((resolve, reject) => {
    //             frappe.dom.unfreeze()

    //             const timesheet_date = frm.doc.date;
    //             const weeks = frappe.get_doc('HR Settings', null)?.custom_allowed_weeks_to_unsubmit_timesheet_for_prompt || 5;
    //             const cutoff = frappe.datetime.add_days(frappe.datetime.now_date(), -(weeks * 7));
    //             console.log("asdasdsa", cutoff)
    //             const is_valid = frappe.datetime.str_to_obj(timesheet_date) >= frappe.datetime.str_to_obj(cutoff);

    //             if (!is_valid) {
                    
    //                 frappe.msgprint({
    //                     title: __('Timesheet Too Old'),
    //                     message: __('You can only {0} timesheets from the last {1} week(s). This timesheet is older than allowed.',[ action === 'submit' ? 'submit' : 'request unsubmit', weeks]), indicator: 'red'});
    //                 reject()
                    
    //             }
    //             else{
    //                 resolve()
    //             }
    //         })

    //         await promise
    //     }
    // }

    before_workflow_action: async (frm) => {
        const allowed_actions = ['Submit', 'Request for Unsubmit Timesheet'];
        const action = frm.selected_workflow_action;

        if (allowed_actions.includes(action)) {
            frappe.dom.unfreeze();

            const weeks = await frappe.db.get_single_value('HR Settings', 'custom_allowed_weeks_to_unsubmit_timesheet_for_prompt');
            const allowed_weeks = weeks || 5;

            const timesheet_date = frm.doc.custom_date;
            const cutoff = frappe.datetime.add_days(frappe.datetime.now_date(), -(allowed_weeks * 7));
            const is_valid = frappe.datetime.str_to_obj(timesheet_date) >= frappe.datetime.str_to_obj(cutoff);
            
            console.log("asdasdas", is_valid, cutoff, timesheet_date)
            if (!is_valid) {
                frappe.throw({
                    title: __('Timesheet Too Old'),
                    message: __(`You can only ${action === 'Submit' ? 'submit' : 'request unsubmit'} timesheets from the last ${allowed_weeks} week(s). This timesheet is older than allowed.`)
                });
            }
        }
    }

})

frappe.ui.form.on("Timesheet Detail", {
    form_render: function(frm, cdt, cdn){
        let row = locals[cdt][cdn]
        field_names = ["is_billable", "billing_hours", "billing_rate", "billing_amount", "costing_rate", "costing_amount", "base_billing_rate", "base_billing_amount", "base_costing_rate", "base_costing_amount"]
        

            frappe.call({
                method: "prompt_hr.py.timesheet.show_filds_for",
                args:{
                    project: row.project
                },
                callback: function(res){

                    console.log("res.message.show_fields", res.message.show_fields)
                    if (res.message.error){
                        frappe.throw(res.message.message)
                    }
                    else if (res.message && res.message.show_fields){
                        console.log("THIS IS TRUE")
                        field_names.forEach( fn =>{
                            frm.fields_dict["time_logs"].grid.toggle_display(fn, true);
                        })
                    }
                    else{
                        field_names.forEach( fn =>{
                            frm.fields_dict["time_logs"].grid.toggle_display(fn, false);
                        })  
                    }
                    frm.refresh_field("time_logs")
                }
            })
        
        
    },

    time_logs_add: function(frm, cdt,cdn){
        let row = locals[cdt][cdn]

        frappe.call({
            method: "prompt_hr.py.timesheet.set_billing_rate",
            args: {
                doc: frm.doc
            },
            callback: function(r){
                if (r.message && r.message.billing_rate){
                    row.billing_rate = r.message.billing_rate   
                }
            }
        })
        
    },

    is_billable: function(frm, cdt, cdn){

        let row = locals[cdt][cdn]
        
        if (row.is_billable){
            console.log("Called")
            frappe.call({
                method: "prompt_hr.py.timesheet.set_billing_rate",
                args: {
                    doc: frm.doc
                },
                callback: function(r){
                    console.log("res", r)
                    if (r.message && r.message.billing_rate){

                        row.billing_rate = r.message.billing_rate   
                    }

                    frm.refresh_field("time_logs")
                }
            })
        }
        
    }
})

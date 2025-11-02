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
    }
})

frappe.ui.form.on("Timesheet Detail", {
    form_render: function(frm, cdt, cdn){
        let row = locals[cdt][cdn]
        field_names = ["is_billable", "billing_hours", "billing_rate", "billing_amount", "costing_rate", "costing_amount"]
        

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
        
        
    }
})

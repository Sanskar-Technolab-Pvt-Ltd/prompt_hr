frappe.ui.form.on("HR Settings", {

    refresh: function (frm) {

        if (frm.doc.custom_deduct_leave_penalty_for_indifoss) {

            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_indifoss", "custom_leave_type_for_indifoss", 0, 1);
        }

        if (frm.doc.custom_deduct_leave_penalty_weekly_for_indifoss) {
            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_weekly_for_indifoss", "custom_leave_type_weekly_for_indifoss", 0, 1);
            
        }

        if (frm.doc.custom_deduct_leave_penalty_for_prompt) {
            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_prompt", "custom_leave_type_for_prompt", 1, 0)            
        }

        if (frm.doc.custom_deduct_leave_penalty_weekly_for_prompt) {
            apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_weekly_for_prompt", "custom_leave_type_weekly_for_prompt", 1, 0)            
        }
    },
    custom_deduct_leave_penalty_for_indifoss: function (frm) {
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_indifoss", "custom_leave_type_for_indifoss", 0, 1);
    },

    custom_deduct_leave_penalty_weekly_for_indifoss: function (frm) {
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_weekly_for_indifoss", "custom_leave_type_weekly_for_indifoss", 0, 1)
    },

    custom_deduct_leave_penalty_for_prompt: function (frm) {
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_for_prompt", "custom_leave_type_for_prompt", 1, 0)
    },

    custom_deduct_leave_penalty_weekly_for_prompt: function (frm) { 
        apply_filter_for_leave_type(frm, "custom_deduct_leave_penalty_weekly_for_prompt", "custom_leave_type_weekly_for_prompt", 1, 0)
    }

})



function apply_filter_for_leave_type(frm, fieldname, leave_type_fieldname, prompt_comp, indifoss) {

    let args = {};
    if (indifoss) args.indifoss = 1;
    if (prompt_comp) args.prompt = 1;

    frappe.call({
        method: "prompt_hr.py.utils.fetch_company_name",
        args: args,
        callback: function (res) {
            if (res.message) {
                if (!res.message.error && res.message.company_id) {
                    
                    if (frm.doc[fieldname] == "Deduct leave without pay")
                        {
                            frm.set_query(leave_type_fieldname, function () {
                                return {
                                    filters: {
                                        "custom_company": res.message.company_id,
                                        "is_lwp": 1
                                    }
                                }
                            })
                        }
                
                    if (frm.doc[fieldname] == "Deduct earned leave") {
                            frm.set_query(leave_type_fieldname, function () {
                                return {
                                    query: 'prompt_hr.py.utils.fetch_leave_type_for_indifoss',
                                    filters: {
                                        company_id: res.message.company_id
                                    }
                                };
                            });
                        }
                } else {
                    frappe.throw(res.message.message)
                }
            }
        }
    })
}
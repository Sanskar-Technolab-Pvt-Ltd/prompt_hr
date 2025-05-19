frappe.ui.form.on("HR Settings", {
    custom_deduct_leave_penalty_for_indifoss: function (frm) {

        frappe.call({
            method: "prompt_hr.py.utils.fetch_company_name",
            args: {
                indifoss: 1
            },
            callback: function (res) {

                if (res.message) {
                    if (!res.message.error && res.message.company_id) {
                        
                        if (frm.doc.custom_deduct_leave_penalty_for_indifoss == "Deduct leave without pay")
                            {
                                frm.set_query("custom_leave_type_for_indifoss", function () {
                                    return {
                                        filters: {
                                            "custom_company": res.message.company_id,
                                            "is_lwp": 1
                                        }
                                    }
                                })
                            }
                    
                            if (frm.doc.custom_deduct_leave_penalty_for_indifoss == "Deduct earned leave") {
                                frm.set_query("custom_leave_type_for_indifoss", function () {
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

        
        
    },

    custom_deduct_leave_penalty_weekly_for_indifoss: function (frm) {

        frappe.call({
            method: "prompt_hr.py.utils.fetch_company_name",
            args: {
                indifoss: 1
            },
            callback: function (res) {

                if (res.message) {
                    if (!res.message.error && res.message.company_id) {
                        
                        if (frm.doc.custom_deduct_leave_penalty_weekly_for_indifoss == "Deduct leave without pay")
                            {
                                frm.set_query("custom_leave_type_weekly_for_indifoss", function () {
                                    return {
                                        filters: {
                                            "custom_company": res.message.company_id,
                                            "is_lwp": 1
                                        }
                                    }
                                })
                            }
                        
                        if (frm.doc.custom_deduct_leave_penalty_weekly_for_indifoss == "Deduct earned leave") {
                                frm.set_query("custom_leave_type_weekly_for_indifoss", function () {
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
})

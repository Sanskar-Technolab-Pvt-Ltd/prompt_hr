frappe.ui.form.on("Compensatory Leave Request", {
    refresh(frm) {
        if (frm.doc.employee){
			frappe.call({
                method: "prompt_hr.py.utils.check_user_is_reporting_manager",
                args: {
                    user_id: frappe.session.user,
                    requesting_employee_id: frm.doc.employee
                },
                callback: function (res) {
                    if (!res.message.error) {
                        if (res.message.is_rh) {
                            if (!has_common(frappe.user_roles, ["S - HR Director (Global Admin)", "System Manager"]))
								frm.fields.filter(field => field.has_input).forEach(field => {
                                    frm.set_df_property(field.df.fieldname, "read_only", 1);
                                });
                        }

                    } else if (res.message.error) {
                        frappe.throw(res.message.message)
                    }
                }
            })
		}
    }
})

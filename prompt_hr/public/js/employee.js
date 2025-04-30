frappe.ui.form.on("Employee", {
    refresh: function(frm) {
        if (!frm.doc.department) {
            frm.set_query("custom_subdepartment", () => {
                return {
                    filters: {
                        name: ["is", "not set"]
                    }
                };
            });
        }
        frm.add_custom_button(__("Release Service Level Agreement"), function () {
            frappe.dom.freeze(__('Releasing Letter...'));
            frappe.call({
                method: "prompt_hr.py.employee.send_service_agreement",
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                    }
                },
                always: function () {
                    frappe.dom.unfreeze();
                }
            });
        }, __("Release Letters"));

        frm.add_custom_button(__("Release Confirmation Letter"), function () {
            frappe.dom.freeze(__('Releasing Letter...'));
            frappe.call({
                method: "prompt_hr.py.employee.send_confirmation_letter",
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                    }
                },
                always: function () {
                    frappe.dom.unfreeze();
                }
            });
        }, __("Release Letters"));
        frm.add_custom_button(__("Release Probation Extension Letter"), function () {
            frappe.dom.freeze(__('Releasing Letter...'));
            frappe.call({
                method: "prompt_hr.py.employee.send_probation_extension_letter",
                args: { name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint(r.message);
                    }
                },
                always: function () {
                    frappe.dom.unfreeze();
                }
            });
        }, __("Release Letters"));

        if (frm.doc.custom_state) {
            frm.set_query("custom_festival_holiday_list", () => {
                return {
                    filters: {
                        state: frm.doc.custom_state
                    }
                };
            });
        }
    },
    department: function(frm) {
        console.log("Employee Form Refreshed");
        if (frm.doc.department){
            frappe.db.get_value("Department", frm.doc.department || "", "is_group")
                .then((r) => {
                    if (r && r.message && r.message.is_group) {
                        frm.set_query("custom_subdepartment", () => {
                            return {
                                filters: {
                                    parent_department: frm.doc.department,
                                    company: frm.doc.company,
                                }
                            };
                        });
                    }
                    else{
                        frm.set_query("custom_subdepartment", () => {
                            return {
                                filters: {
                                    name: ["is", "not set"]
                                }
                            };
                        });
                    }
                })
                .catch((err) => {
                    console.error("Error fetching Department Type:", err);
                });
        }
        else{
            frm.set_query("custom_subdepartment", () => {
                return {
                    filters: {
                        name: ["is", "not set"]
                    }
                };
            });
        }
    },
    custom_current_address_is_permanent_address: function (frm) {
        if (frm.doc.custom_current_address_is_permanent_address) {
            console.log(frm.doc.custom_current_address_is_permanent_address)
            frm.set_value("custom_permanent_address_line_1", frm.doc.custom_current_address_line_1);
            frm.set_value("custom_permanent_address_line_2", frm.doc.custom_current_address_line_2);
            frm.set_value("custom_permanent_address_line_3", frm.doc.custom_current_address_line_3);
            frm.set_value("custom_permanent_city", frm.doc.custom_current_city);
            frm.set_value("custom_permanent_state", frm.doc.custom_current_state);
            frm.set_value("custom_permanent_zip_code",frm.doc.custom_current_zip_code)
        }
        else{
            frm.set_value("custom_permanent_address_line_1", "");
            frm.set_value("custom_permanent_address_line_2", "");
            frm.set_value("custom_permanent_address_line_3", "");
            frm.set_value("custom_permanent_city", "");
            frm.set_value("custom_permanent_state", "");
            frm.set_value("custom_permanent_zip_code", "")
        }
    },

    
    // refresh: function (frm){
    //     prompt_probation_period = frappe.db.get_single_value("HR Settings","custom_probation_period_for_prompt")
    //     indifoss_probation_period = frappe.db.get_single_value("HR Settings","custom_probation_period_for_indifoss")
    //     if (frm.doc.company == "Prompt Equipments Pvt Ltd"){
            
    //     }
    // }

});

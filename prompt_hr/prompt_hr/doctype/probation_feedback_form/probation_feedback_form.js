// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Probation Feedback Form", {
    refresh(frm) {
        
        // * APPLYING FILTER TO QUESTION LINK FIELD BASED ON PROBATION FEEDBACK FOR IN probation_feedback_prompt CHILD TABLE
        if (frm.doc.probation_feedback_for) {
            frm.fields_dict['probation_feedback_prompt'].grid.get_field('question').get_query = function () {
                return {
                    filters: [
                        ['probation_feedback_for', '=', frm.doc.probation_feedback_for] // pass list
                    ]
                };
            };
        }

        const user = frappe.session.user;
        const reporting_manager = frm.doc.reporting_manager;

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
            "callback": function (response) {
                
                if (response.message) {
                    console.log("asdsadsad")
                    fields = ["department", "company", "reporting_manager", "evaluation_date", "hod", "probation_feedback_for"]
                    
                    const hr_manager_roles = ["S - HR L1", "S - HR Director (Global Admin)"];

                    const user_employee_name = response.message.name;
                    
                    if (user_employee_name === reporting_manager) {

                        console.log("User is Reporting Manager");
                        frm.fields_dict.probation_feedback_prompt.grid.update_docfield_property('rating', 'read_only', 0);
                        frm.set_df_property("any_major_areas_of_improvement", "reqd", 1)
                        frm.set_df_property("recommend_trainings_if_any", "reqd", 1)
                        
                        fields.forEach(field => {
                            frm.set_df_property(field, "read_only", 1)
                        })
                        
                    } else if (hr_manager_roles.some(role => frappe.user.has_role(role))) {
                        console.log("hr manager")
                        frm.fields_dict.probation_feedback_prompt.grid.update_docfield_property('rating', 'read_only', 0);
                        frm.page.clear_primary_action();
                        fields.forEach(field => {
                            frm.set_df_property(field, "read_only", 0)
                        })

                    }else {
                        console.log("User is neither Reporting Manager nor Head of Department");
                        frm.fields_dict.probation_feedback_prompt.grid.update_docfield_property('rating', 'read_only', 1);
                        frm.page.clear_primary_action();
                        

                        fields.forEach(field => {
                            frm.set_df_property(field, "read_only", 1)
                        })
                        
                    }
                }
            }
        })
        frm.fields_dict['probation_feedback_prompt'].grid.refresh();

    },
    
    probation_feedback_for: function (frm) {

        // * APPLYING FILTER TO QUESTION LINK FIELD BASED ON PROBATION FEEDBACK FOR IN probation_feedback_prompt CHILD TABLE
        if (frm.doc.probation_feedback_for) {
            frm.fields_dict['probation_feedback_prompt'].grid.get_field('question').get_query = function () {
                return {
                    filters: [
                        ['probation_feedback_for', '=', frm.doc.probation_feedback_for] // pass list
                    ]
                };
            };
        }

        frm.doc.probation_feedback_prompt.forEach(function (row) {
            row.frequency = frm.doc.probation_feedback_for;
        });

        frm.refresh_field('probation_feedback_prompt');
    }
});


frappe.ui.form.on("Probation Feedback Prompt", {
    rating: function (frm, cdt, cdn) { 
        let row = locals[cdt][cdn];

        if (row.rating < 1 || row.rating > 5) {
            frappe.throw("Rating must be between 1 and 5.");
        }
    }
})
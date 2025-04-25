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

        if (frm.doc.company === "IndiFOSS Analytical Pvt Ltd" && frm.doc.employee) {
                
            // * APPLYING FILTER TO FACTOR CATEGORY LINK FIELD BASED ON SUB CATEGORY AND CATEGORY IN probation_feedback_indifoss
            frm.fields_dict['probation_feedback_indifoss'].grid.get_field('factor_category').get_query = function (doc, cdt, cdn) {
                let row = locals[cdt][cdn];
                
                if (row.category && row.category == "General") {
                    return {
                        filters: [
                            ['parent_category', '=', row.sub_category]
                        ]
                    };
                }

                else if (row.category && row.category == "KPI Expectations") {
                    return {
                        filters: [
                            ['parent_category', '=', row.category]
                        
                        ]
                    };
                };
                frm.fields_dict['probation_feedback_indifoss'].grid.refresh();
            };

            // * MAKING 45_DAYS, 90_DAYS AND 180_DAYS READ ONLY BASED ON EMPLOYEE JOINING DATE AND HR SETTINGS FIRST AND SECOND PROBATION FEEDBACK AND RELEASE CONFIRMATION FOR INDIFOSS FIELDS
            frappe.db.get_value("Employee", frm.doc.employee, "date_of_joining")
                .then(r => {
                    if (r.message && r.message.date_of_joining) {
                        const joining_date = r.message.date_of_joining;
                        const today = frappe.datetime.get_today();
                        const days_diff = frappe.datetime.get_diff(today, joining_date);


                        if (days_diff > 45) {
                            let grid = frm.fields_dict["probation_feedback_indifoss"].grid;

                            if (grid && grid.get_docfield) {
                                let docfield = grid.get_docfield("90_days");

                                if (docfield) {
                                    docfield.read_only = 1;
                                    grid.refresh();

                                    frm.fields_dict["probation_feedback_indifoss"].grid.grid_rows.forEach(row => {
                                        if (row.docfields) {
                                            row.docfields.forEach(df => {
                                                if (df.fieldname === "90_days") {
                                                    df.read_only = 1;
                                                }
                                            });
                                        }
                                    });
                                    frm.refresh_field("probation_feedback_indifoss");
                                }
                            }
                        }
                    }
                });
        }
        
        const user = frappe.session.user;
        frappe.call({
            "method": "frappe.client.get_value",
            "args": {
                "doctype": "Employee",
                "filters": {
                    "name": frm.doc.employee
                },
                "fieldname": ["custom_dotted_line_manager"]
            },
            callback: function (r) { 
                if (r.message.custom_dotted_line_manager) {
                    frappe.call({
                        "method": "frappe.client.get_value",
                        "args": {
                            "doctype": "Employee",
                            "filters": {
                                "name": r.message.custom_dotted_line_manager
                            },
                            "fieldname": ["user_id"]
                        },
                        callback: function (response) {
                            if (response.message.user_id) {
                                if (response.message.user_id == user) {
                                    if (!frm.doc.added_dotted_manager_feedback) { 
                                        frm.add_custom_button("Confirm Rating", function () {
                                            
                                            frappe.call({
                                                method: "prompt_hr.prompt_hr.doctype.probation_feedback_form.probation_feedback_form.send_mail_to_hr",
                                                args: {
                                                    docname: frm.doc.name
                                                },
                                                callback: function (r) {
                                                    if (r.message.error) {
                                                        frappe.throw(r.message.message);
                                                    }
                                                    else {
                                                        frm.set_value('added_dotted_manager_feedback', 1)
                                                        frm.save();            
                                                    }
                                                }
                                            })
                                            
                                        }).addClass("btn-primary");

                                    }
                                    
                                }
                                
                            }
                        }
                    });
                    
                }
            }
        })

        if (frappe.user.has_role("HR Manager") || frappe.user.has_role("HR User")) {
            frappe.call({
                "method": "frappe.client.get_value",
                "args": {
                    "doctype": "Performance Improvement Plan",
                    "filters": {
                        "employee": frm.doc.employee
                    },
                    "fieldname": ["name"]
                },
                callback: function (r) { 
                    if (r.message.name) {
                        frm.add_custom_button(__('Go to PIP'), function() {
                            frappe.set_route("Form", "Performance Improvement Plan", r.message.name);
                        }).addClass("btn-primary");
                    }
                    else {
                        frm.add_custom_button(__('Create PIP'), function() {
                            frappe.route_options = {
                                "employee": frm.doc.employee
                                // "custom_job_requisition_record": frm.doc.name,
                                // "designation": frm.doc.designation,
                                // "department": frm.doc.department,
                                // "employment_type": frm.doc.custom_employment_type,
                                // "custom_no_of_position": frm.doc.no_of_positions,
                                // "custom_priority": frm.doc.custom_priority,
                                // "description": frm.doc.description,
                                // "location": frm.doc.custom_work_location,
                                // "custom_business_unit": frm.doc.custom_business_unit,
                                // "custom_required_experience": frm.doc.custom_experience
                            }
                            frappe.set_route("Form", "Performance Improvement Plan", "new-performance-improvement-plan");
                        }).addClass("btn-primary");
                        
                    }
                    
                }
            })           
            
        }   


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

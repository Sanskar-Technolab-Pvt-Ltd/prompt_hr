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
                                    console.log("Current User is A Dotted Manager")
                                    frm.add_custom_button("Confirm Rating", function () { 
                                        
                                    })
                                }
                                
                            }
                        }
                    });
                    
                }
            }
        })
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

frappe.ui.form.on('Interview Feedback', {
    refresh: function(frm) {
        frappe.after_ajax(() => {
            frm.get_field('skill_assessment').grid.cannot_add_rows = true;
            frm.fields_dict.skill_assessment.$wrapper
                .find('.grid-add-row')
                .hide();
                if (frappe.user.has_role("Interviewer") && 
                !frappe.user.has_role("System Manager") && 
                !frappe.user.has_role("S - HR Director (Global Admin)") && 
                frappe.session.user !== "Administrator") {
    
                // Make main form fields read-only
                const readonly_fields = ["interview", "job_applicant", "custom_company", 
                                        "interview_round", "interviewer", "custom_obtained_average_score"];
                readonly_fields.forEach(field => {
                    frm.set_df_property(field, "read_only", 1);
                });
    
                frm.fields_dict.skill_assessment.grid.update_docfield_property(
                    'custom_skill_type', 'read_only', 1
                );
                frm.fields_dict.skill_assessment.grid.update_docfield_property(
                    'custom_rating_scale', 'read_only', 1
                );
            }
        });
        
    },
    validate: function(frm) {
        // Check all rows in the skill assessment table
        let hasError = false;
        
        frm.doc.skill_assessment.forEach(function(row) {
            if (row.custom_rating_given > row.custom_rating_scale) {
                hasError = true;
                frappe.throw(`Skill ${row.skill}: Rating given (${row.custom_rating_given}) cannot be greater than rating scale (${row.custom_rating_scale})`);
                return false; // Break out of the loop
            }
        });
        
        return !hasError;
    },
    custom_company: function(frm) {
        if (frm.doc.custom_company) {
            frm.set_query("interview_round", function() {
                return {
                    filters: {
                        'custom_company': frm.doc.custom_company
                    }
                };
            });
        }
    },
});
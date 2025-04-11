// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

// your_app/public/js/user_welcome_status.js
frappe.ui.form.on('Welcome Page', {
    refresh: function(frm) {
        // Hide standard buttons if not completed
        if (!frm.doc.is_completed) {
            // Hide back button
            $('.page-head .page-head-content .back-link').hide();
            
            // Add custom submit button
            frm.add_custom_button(__('Complete Profile'), function() {
                // Validate required fields
                let required_fields = ['eps_consent'];
                let missing_fields = [];
                
                required_fields.forEach(field => {
                    if (!frm.doc[field]) {
                        missing_fields.push(frm.fields_dict[field].df.label);
                    }
                });
                
                if (missing_fields.length > 0) {
                    frappe.msgprint({
                        title: __('Missing Required Fields'),
                        indicator: 'red',
                        message: __('Please fill in the following required fields: {0}', 
                            [missing_fields.join(', ')])
                    });
                    return;
                }
                
                // Set as completed and save
                frm.set_value('is_completed', 1);
                frm.save().then(() => {
                    frappe.show_alert({
                        message: __('Profile completed successfully'),
                        indicator: 'green'
                    });
                    
                    // Redirect to home
                    setTimeout(() => {
                        window.location.href = '/desk';
                    }, 1000);
                });
            }).addClass('btn-primary');
        }
    },
    
    onload: function(frm) {
        // If already completed and not System Manager, redirect away
        if (frm.doc.is_completed && !frappe.user.has_role('System Manager')) {
            window.location.href = '/desk';
        }
    }
});
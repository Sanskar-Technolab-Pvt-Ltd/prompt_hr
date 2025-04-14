//  Copyright (c) 2025, Jignasha Chavda and contributors
//  For license information, please see license.txt

frappe.ui.form.on('Welcome Page', {
    validate: function(frm) {
        const required_fields = [
            "do_you_have_a_pran_no", "nps_consent", "meal_wallet", "meal_amount",
            "fuel_wallet", "fuel_amount", "attire_wallet", "attire_amount",
            "consent_for_background_verification"
        ];

        required_fields.forEach(fieldname => {
            const field = frm.fields_dict[fieldname];

            // ? SKIP IF FIELD NOT FOUND OR IS HIDDEN
            if (!field || field.df.hidden || field.$wrapper.is(":hidden")) {
                return; 
            }

            const value = frm.doc[fieldname];

            if (value === "" || value == null) {
                frappe.throw(__("Field '{0}' cannot be left empty.", [field.df.label || fieldname]));
            }
        });
    },
    
    onload: function(frm) {

        // ? IF ALREADY COMPLETED AND NOT SYSTEM MANAGER, REDIRECT AWAY
        if (frm.doc.is_completed && !frappe.user.has_role('System Manager')) {
            window.location.href = '/desk';
        }
    }
});

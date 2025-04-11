//  Copyright (c) 2025, Jignasha Chavda and contributors
//  For license information, please see license.txt

frappe.ui.form.on('Welcome Page', {
    refresh: function(frm) {

    
    },
    
    onload: function(frm) {

        // ? IF ALREADY COMPLETED AND NOT SYSTEM MANAGER, REDIRECT AWAY
        if (frm.doc.is_completed && !frappe.user.has_role('System Manager')) {
            window.location.href = '/desk';
        }
    }
});
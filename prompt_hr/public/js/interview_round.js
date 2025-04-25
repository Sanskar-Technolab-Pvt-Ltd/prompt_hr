frappe.ui.form.on("Interview Round", {
    refresh: function(frm) {
        if (frm.doc.custom_company) {
            frm.set_query("skill", "expected_skill_set", function() {
                return {
                    filters: {
                        'custom_company': frm.doc.custom_company
                    }
                };
            });
        }
    },
    custom_company: function(frm) {
        if (frm.doc.custom_company) {
            frm.set_query("skill", "expected_skill_set", function() {
                return {
                    filters: {
                        'custom_company': frm.doc.custom_company
                    }
                };
            });
        }
    }
});

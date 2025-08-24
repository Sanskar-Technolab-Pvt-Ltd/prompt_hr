frappe.ui.form.on("Employee Checkin", {
    onload: function(frm) {
        // ? ONLY RUN FOR NEW CHECK-INS AND WHEN NO EMPLOYEE IS PRE-FILLED
        if (frm.is_new() && !frm.doc.employee) {

            // ? CHECK IF USER DOES NOT HAVE PRIVILEGED ROLES
            const privileged_roles = ["S - HR Director (Global Admin)", "System Manager", "Administrator"];
            const is_privileged = privileged_roles.some(role => frappe.user_roles.includes(role));

            if (!is_privileged) {
                // ? GET EMPLOYEE LINKED TO CURRENT USER AND AUTO-SET
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Employee',
                        filters: {
                            user_id: frappe.session.user
                        },
                        fields: ['name', 'employee_name'],
                        limit_page_length: 1
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            frm.set_value('employee', r.message[0].name);
                            frm.set_df_property("employee", "read_only", 1);
                        }
                    }
                });
            }
        }
    },
});
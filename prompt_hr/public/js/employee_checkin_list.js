frappe.listview_settings['Employee Checkin'] = {
    refresh: function (listview) {
        frappe.call({
            method: "prompt_hr.py.employee.check_if_employee_create_checkin_is_validate_via_web",
            args: {
                user_id: frappe.session.user
            },
            callback: function (r) {
                if (r.message === 0) {
                    // Disable / hide New button
                    listview.page.clear_primary_action();
                }
            }
        });
    }
};

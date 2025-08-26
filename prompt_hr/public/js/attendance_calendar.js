frappe.views.calendar["Attendance"] = {
    field_map: {
        start: "attendance_date",
        end: "attendance_date",
        id: "name",
        title: "status",
        allDay: 1,
    },
    get_events_method: "prompt_hr.py.utils.get_colored_events",

    filters: [
        {
            fieldname: "employee",
            fieldtype: "Link",
            label: "Employee",
            options: "Employee",
            default: "",
        }
    ],
};

frappe.views.calendar["Meeting Request"] = {
    field_map: {
        start: "from_time",
        end: "to_time",
        id: "name",
        title: "meeting_title",
        allDay: 0,
        progress: 50,
        color: "color",
    },
    gantt: true,
    color: "color",
    filters: [
        {
            label: __("Meeting Title"),
            fieldname: "meeting_title",
            fieldtype: "Link",
            options: "Employee",
        },
    ],
    get_events_method: "frappe.desk.calendar.get_events",
};
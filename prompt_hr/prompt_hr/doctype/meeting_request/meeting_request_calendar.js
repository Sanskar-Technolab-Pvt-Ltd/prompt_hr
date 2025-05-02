frappe.views.calendar["Meeting Request"] = {
    field_map: {
        start: "from_time",
        end: "to_time",
        id: "id",
        title: "organizor_name",
        allDay: 0,
        progress: 50,
        color: "color",
    },
    gantt: {
        field_map: {
            start: "from_time",
            end: "to_time",
            id: "name",
            title: "organizor_name",
            allDay: 0,
            progress: 50,
            color: "color",
        },
	},
    color: "color",
    filters: [
        {
            label: __("Organizor Name"),
            fieldname: "organizor_name",
            fieldtype: "Link",
            options: "Employee",
        },
    ],
    get_events_method: "frappe.desk.calendar.get_events",
};
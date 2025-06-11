frappe.listview_settings["Attendance"] = {
    get_indicator: function (doc) {
        if(["Half Day", "Mispunch"].includes(doc.status)) {
			return [__(doc.status), "orange", "status,=," + doc.status];
        } else if (doc.status == "WeekOff") {
			return [__(doc.status), "blue", "status,=," + doc.status];
		}
	},
} 
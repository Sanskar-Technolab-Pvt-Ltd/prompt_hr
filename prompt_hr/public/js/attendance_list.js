frappe.listview_settings["Attendance"] = {
	get_indicator: function (doc) {
		if (["Present", "Work From Home"].includes(doc.status)) {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (["Absent", "On Leave"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		} else if (doc.status == "Half Day") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		}
        else if(["Half Day", "Mispunch"].includes(doc.status)) {
			return [__(doc.status), "orange", "status,=," + doc.status];
        } else if (doc.status == "WeekOff") {
			return [__(doc.status), "blue", "status,=," + doc.status];
		}
	},
} 
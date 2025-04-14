frappe.ui.form.on("Job Opening", {
    company: function (frm) {
        frappe.ui.form.off("Job Opening", "company");
	},
});
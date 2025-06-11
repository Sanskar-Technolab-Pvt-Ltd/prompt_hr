frappe.ui.form.on("Meeting Request", {
    onload(frm) {
        updateRelatedToOptions(frm);
    }
});

function updateRelatedToOptions(frm) {
    frm.set_query("related_to", function () {
        return {
            filters: [["name", "in", ["Customer", "Lead", "Opportunity"]]]
        };
    });
    frm.refresh_field("related_to");
}

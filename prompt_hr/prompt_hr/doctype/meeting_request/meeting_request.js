frappe.ui.form.on("Meeting Request", {
    onload(frm) {
        updateRelatedToOptions(frm);
        frappe.call({
            method:"prompt_marketing.prompt_marketing.doctype.tour_visit.tour_visit.get_employee_for_user",
            callback:function(r){
                if(r.message){
                    frm.set_value("organizor_name",r.message.name)
                    frm.set_value("organizer_name",r.message.employee_name)
                }
            }
        });
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

cur_frm.fields_dict["table_qygi"].grid.get_field("related_to").get_query = function() {
    return {
        filters: {
            name: ["in", ["User", "Contact", "Customer"]]
        }
    };
};
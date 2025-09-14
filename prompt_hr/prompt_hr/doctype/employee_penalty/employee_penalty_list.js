frappe.listview_settings["Employee Penalty"] = {
    refresh(list_view) {
        list_view.page.add_inner_button(__("Cancel Penalties"), function () {
            let checked_items = list_view.get_checked_items();

            if (!checked_items.length) {
                frappe.msgprint(__("Please select at least one record to cancel"));
                return;
            }

            let ids = checked_items.map(item => item.name);

            // ? Create dialog for reason input
            let dialog = new frappe.ui.Dialog({
                title: __("Cancel Employee Penalties"),
                fields: [
                    {
                        label: __("Reason for Cancellation"),
                        fieldname: "reason",
                        fieldtype: "Small Text",
                    }
                ],
                primary_action_label: __("Submit"),
                primary_action(values) {
                    frappe.call({
                        method: "prompt_hr.prompt_hr.doctype.employee_penalty.employee_penalty.cancel_penalties",
                        args: {
                            ids,
                            reason: values.reason
                        },
                        freeze: true,
                        freeze_message: __("Cancelling penalties, please wait..."),
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(__("Penalties cancelled successfully"));
                                list_view.refresh();
                                dialog.hide();
                            }
                        }
                    });
                }
            });

            dialog.show();
        }).removeClass("btn-default").addClass("btn-primary");
    }
};

frappe.listview_settings["Attendance Regularization"] = {
    onload: function (listview) {
        const actions_menu_items = [];

        // Bulk Delete Action
        const bulk_delete = {
            label: __("Delete", null, "Button in list view actions menu"),
            action: () => {
                const docnames = listview.get_checked_items(true).map(docname => docname.toString());
                if (docnames.length === 0) return;

                let message = __("Delete {0} item permanently?", [docnames.length]);
                if (docnames.length > 1) {
                    message = __("Delete {0} items permanently?", [docnames.length]);
                }

                frappe.confirm(message, () => {
                    listview.disable_list_update = true;
                    frappe.call({
                        method: "frappe.desk.reportview.delete_items",
                        freeze: true,
                        freeze_message: (docnames.length <= 10) ? __("Deleting {0} records...", [docnames.length]) : null,
                        args: {
                            items: docnames,
                            doctype: listview.doctype,
                        },
                    }).then(r => {
                        const failed = r.message || [];
                        if (failed.length && !r._server_messages) {
                            frappe.throw(
                                __("Cannot delete {0}", [failed.map(f => f.bold()).join(", ")])
                            );
                        }
                        if (failed.length < docnames.length) {
                            frappe.utils.play_sound("delete");
                            listview.clear_checked_items();
                            listview.refresh();
                        }
                        listview.disable_list_update = false;
                    });
                });
            },
            standard: true,
        };

        const bulk_cancel = {
            label: __("Cancel"),
            action: () => {
                const docnames = listview.get_checked_items(true);
                if (!docnames.length) return;

                const task_id = Math.random().toString(36).slice(-5);
                frappe.realtime.task_subscribe(task_id);

                frappe.confirm(__("Cancel {0} documents?", [docnames.length]), () => {
                    listview.disable_list_update = true;

                    frappe.xcall("frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs", {
                        doctype: listview.doctype,
                        action: "cancel",
                        docnames: docnames,
                        task_id: task_id
                    }).then((failed_docnames) => {
                        if (failed_docnames?.length) {
                            // ✅ Single combined message
                            const failed_list = frappe.utils.comma_and(failed_docnames);
                            frappe.msgprint({
                                title: __("Bulk Cancel Failed"),
                                message: __("Cannot cancel: {0}", [failed_list]),
                                indicator: "red"
                            });
                        } else {
                            frappe.utils.play_sound("cancel");
                            frappe.show_alert({message: __("Documents cancelled successfully"), indicator: "green"});
                        }
                    }).finally(() => {
                        frappe.realtime.task_unsubscribe(task_id);
                    });
                    listview.disable_list_update = false;
                    listview.clear_checked_items();
                    listview.refresh();
                });
            },
            standard: true,
        };


        // Add Cancel button if user can cancel Doctype
        if (frappe.model.can_cancel(listview.doctype)) {
            actions_menu_items.push(bulk_cancel);
        }

        // Add Delete button if user can delete Doctype
        if (frappe.model.can_delete(listview.doctype)) {
            actions_menu_items.push(bulk_delete);
        }

        // Add actions to the List View Actions Menu
        actions_menu_items.forEach(item => {
            const $item = listview.page.add_actions_menu_item(item.label, item.action, item.standard);
            if (item.class) {
                $item.addClass(item.class);
            }
            if (item.is_workflow_action && $item) {
                this.workflow_action_items[item.name] = $item;
            }
        });
    },
}
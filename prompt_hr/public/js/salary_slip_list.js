frappe.listview_settings['Salary Slip'] = {  
    onload(listview) {  
        // ? Remove standard Cancel action  
        listview.page.actions.find(`[data-label="Cancel"]`).parent().parent().remove();

        // ? Add custom Cancel action with reason prompt  
        listview.page.add_actions_menu_item('Cancel', () => {  
            const docnames = listview.get_checked_items(true);  
            if (docnames.length > 0) {

                const task_id = Math.random().toString(36).slice(-5);
                frappe.realtime.task_subscribe(task_id);
                frappe.confirm(  
                    __("Cancel {0} documents?", [docnames.length]),  
                    () => {  
                        frappe.prompt(  
                            [  
                                {  
                                    label: 'Cancellation Reason',  
                                    fieldname: 'cancel_reason',  
                                    fieldtype: 'Data',  
                                    reqd: 1,  
                                }  
                            ],  
                            async (values) => {  
                                try {  
                                    // 1 Fetch the docstatus for all selected docs
                                    const docs = await frappe.xcall('frappe.client.get_list', {
                                        doctype: 'Salary Slip',
                                        filters: { name: ['in', docnames] },
                                        fields: ['name', 'docstatus']
                                    });

                                    // 2 Filter only submitted documents (docstatus = 1)
                                    const submitted_docs = docs.filter(d => d.docstatus === 1);

                                    // 3 Update cancellation reason only for submitted docs
                                    await Promise.all(submitted_docs.map(d => 
                                        frappe.xcall('frappe.client.set_value', {
                                            doctype: 'Salary Slip',
                                            name: d.name,
                                            fieldname: 'custom_reason_for_cancellation',
                                            value: values.cancel_reason
                                        })
                                    ));
  
                                    // Use frappe.xcall directly to call the backend method  
                                    await frappe.xcall("frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs", {
                                        doctype: listview.doctype,
                                        action: "cancel",
                                        docnames: docnames,
                                        task_id: task_id
                                    }).then((failed_docnames) => {
                                        if (failed_docnames?.length) {
                                            const failed_list = frappe.utils.comma_and(failed_docnames);
                                            frappe.msgprint({
                                                title: __("Cancel Failed"),
                                                message: __("Cannot cancel: {0}", [failed_list]),
                                                indicator: "red"
                                            });
                                        }
                                    }).finally(() => {
                                        frappe.realtime.task_unsubscribe(task_id);
                                    });
                                    listview.disable_list_update = false;
                                    listview.clear_checked_items();
                                    listview.refresh();
                                } catch (error) {  
                                    frappe.msgprint(`Failed to cancel documents: ${error.message}`);  
                                }  
                            },  
                            'Cancel Selected',  
                            'Cancel'  
                        );  
                    }  
                );  
            } else {  
                frappe.msgprint(__('Please select at least one record to cancel.'));  
            }  
        });  
    }  
};

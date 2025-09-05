frappe.ui.form.on("Shift Request", {

    custom_reason_for_rejection: function (frm) {
        console.log(frm.doc.custom_reason_for_rejection.length)
    },
    before_workflow_action: async (frm) => {		
		if (frm.selected_workflow_action === "Reject" && frm.doc.custom_reason_for_rejection.length < 1){
            let promise = new Promise((resolve, reject) => {
				frappe.dom.unfreeze()
				
				frappe.prompt({
					label: 'Reason for rejection',
					fieldname: 'reason_for_rejection',
					fieldtype: 'Small Text',
					reqd: 1
				}, (values) => {
					if (values.reason_for_rejection) {
						frm.set_value("custom_reason_for_rejection", values.reason_for_rejection)
						frm.save().then(() => {
							resolve();
						}).catch(reject);						
					}
					else {
						reject()
					}
				})
            });
            await promise.catch(() => frappe.throw());
        }
    }
})
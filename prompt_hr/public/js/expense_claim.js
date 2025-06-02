frappe.ui.form.on('Expense Claim', {
    refresh(frm) {
        // ? CREATE PAYMENT ENTRY BUTTON BASED ON CERTAIN CONDITIONS
        create_payment_entry_button(frm);
    },
    project(frm) {

        // ? SET CAMPAIGN FROM PROJECT 
        setCampaignFromProject(frm);
    }
});

// ? FUNCTION TO CREATE PAYMENT ENTRY BUTTON BASED ON CERTAIN CONDITIONS
function create_payment_entry_button(frm) {
    // ? SHOW BUTTON ONLY IF DOC IS IN DRAFT AND SENT TO ACCOUNTING
    if (frm.doc.docstatus === 0 && frm.doc.workflow_state === "Sent to Accounting Team") {
        
        // ? HIDE SUBMIT BUTTON UNDER ACTIONS BUTTON
        frm.page.actions.parent().remove();
        frm.add_custom_button(__('Create Payment Entry'), () => {

            if (frm.doc.approval_status != "Approved") {
            frappe.throw(__('Expense Claim must be approved before creating a payment entry.'));
            return;
        }

            // ? IF PAYABLE ACCOUNT NOT SET, PROMPT USER TO SELECT ONE
            if (!frm.doc.payable_account) {
                const d = new frappe.ui.Dialog({
                    title: __('Create Payment Entry'),
                    fields: [
                        {
                            fieldtype: 'Link',
                            fieldname: 'payable_account',
                            label: __('Payable Account'),
                            options: 'Account',
                            reqd: 1,
                            get_query: () => {
                                // ? COPY FILTERS FROM FORM'S PAYABLE ACCOUNT FIELD
                                return cur_frm.fields_dict["payable_account"].get_query();
                            }
                        }
                    ],
                    primary_action_label: __('Create'),
                    primary_action(values) {
                        frm.set_value("payable_account", values.payable_account);
                        frm.set_value("workflow_state","Expense Claim Submitted");
                        frm.save().then(() => {
                            frm.savesubmit().then(() => {
                                frm.events.make_payment_entry(frm);
                            });
                        });
                        d.hide();
                    }
                });
                d.show();
            } else {
                frm.set_value("workflow_state","Expense Claim Submitted");
                // ? PAYABLE ACCOUNT ALREADY SET, SUBMIT AND CREATE ENTRY
                frm.savesubmit().then(() => {
                    frm.events.make_payment_entry(frm);
                });
            }
        });
    }
}

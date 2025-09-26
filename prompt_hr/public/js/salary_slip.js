frappe.ui.form.on('Salary Slip', {

    refresh: function (frm) {
        //* TO SHOW A BUTTON TO INFORM THE ACCOUNT USERS ABOUT THE SALARY SLIP
        inform_account_users(frm)
        set_default_value_for_amended_doc(frm)

        // if (!frm.is_new()) {
        //     update_primary_button(frm)
        // }
                
    },

    before_cancel: function (frm) {
        // ? Stop the automatic cancel flow
        frappe.validated = false;

        frappe.prompt([
            {
                fieldname: 'cancel_reason',
                fieldtype: 'Small Text',
                label: 'Cancellation Reason',
                reqd: 1
            }
        ], function (values) {

            // ? Save the reason
            frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: frm.doc.doctype,
                    name: frm.doc.name,
                    fieldname: 'custom_reason_for_cancellation',
                    value: values.cancel_reason
                },
                callback: function () {
                    // ? CANCEL THE DOCUMENT
                    frappe.call({
                        method: 'frappe.client.cancel',
                        args: {
                            doctype: frm.doc.doctype,
                            name: frm.doc.name
                        },
                        callback: function () {
                            frappe.show_alert(__('Document Cancelled'));
                            frm.reload_doc();
                        }
                    });
                }
            });

        }, 'Cancellation Reason Required', 'Submit');
    }

    // custom_account_user_informed(frm) {
    //     update_primary_button(frm);
    // },

    // after_save(frm) {
    //     update_primary_button(frm);
    // },
    // on_submit(frm) {
    //     console.log("Before Submit")
    // },
    // before_submit(frm) {
    //     console.log("After Submit")        
    // }

})

function set_default_value_for_amended_doc(frm) {
    // ? TO SET DEFAULT VALUE TO ZERO FOR SALARY SLIP RELEASED AND A
    if (frm.doc.amended_from && frm.is_new()) {
        frm.set_value("custom_account_user_informed", 0)
        frm.set_value("custom_is_salary_slip_released", 0)
    }
}

// function update_primary_button(frm) {
//     console.log("Function Called")
//     // if (frm.doc.docstatus === 0) {
//     //     console.log("IF CONDITION TRUE")
//     //     frm.page.clear_primary_action();

//     //     if (frm.doc.custom_account_user_informed && !frm.doc.__unsaved) {
//     //         // Show Submit button
//     //         console.log("SHOW SUBMIT BUTTON")
//     //         frm.page.set_primary_action(__('Submit'), async () => {
//     //             try {
//     //                 // await frm.save();
//     //                 await frm.save('Submit');
//     //                 frm.reload_doc()

//     //             } catch (e) {
//     //                 frappe.throw(__('Failed to submit: ') + e.message);
//     //             }
//     //         });
//     //     } else {
//     //         // Show Save button
//     //         if (frm.doc.__unsaved) {
//     //             frm.page.set_primary_action(__('Save'), () => {
//     //                 frm.save();
//     //             });
//     //         }
//     //     }
//     // }
    
//     if (frm.doc.docstatus === 0) {
//         console.log("dasdsad")
//         // This hides or shows the primary "Submit" button without replacing it
//         if (!frm.doc.custom_checkbox && !frm.doc.__unsaved) {
//             // Just hide the button (if it's Submit)

//             console.log("True", frm.page.btn_primary.text())
//             if (frm.page.btn_primary && frm.page.btn_primary.text() === 'Submit') {
//                 frm.page.btn_primary.style.display = 'none';
//             }
//         } else {
//             // Re-show if hidden
//             console.log("False")
//             if (frm.page.btn_primary && frm.page.btn_primary.innerText === 'Submit') {
//                 frm.page.btn_primary.style.display = '';
//             }
//         }
//     }
// }

// * FUNCTION TO INFORM ACCOUNT USERS

function inform_account_users(frm) {
    if (!frm.doc.custom_account_user_informed) {
        frm.add_custom_button(__('Inform Account Department'), function () {
            
            frappe.call({
                method: "prompt_hr.py.salary_slip.send_salary_slip",
                args: {
                    salary_slip_id: frm.doc.name,
                    from_date: frm.doc.start_date,
                    to_date: frm.doc.end_date,
                    company: frm.doc.company
                },
                callback: function (res) {
                    frm.reload_doc()
                }
            })
        });
    }
}
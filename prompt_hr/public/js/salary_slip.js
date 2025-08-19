frappe.ui.form.on('Salary Slip', {

    refresh: function (frm) {
        //* TO SHOW A BUTTON TO INFORM THE ACCOUNT USERS ABOUT THE SALARY SLIP
        inform_account_users(frm)

        // if (!frm.is_new()) {
        //     update_primary_button(frm)
        // }
                
    },

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
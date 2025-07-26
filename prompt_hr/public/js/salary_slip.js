frappe.ui.form.on('Salary Slip', {

    refresh: function (frm) {
        //* TO SHOW A BUTTON TO INFORM THE ACCOUNT USERS ABOUT THE SALARY SLIP
        inform_account_users(frm)

        if (!frm.doc.custom_account_user_informed && frm.doc.docstatus== 0) {
            $(`[data-label="Submit"]`).hide()            
        }
        else if(frm.doc.docstatus== 0) {
            console.log("CHECKBOX CHECKED")
            $(`[data-label="Submit"]`).show()
            $(`[data-label="Submit"]`).text("Send for Approval");
        }
    },
    
})


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
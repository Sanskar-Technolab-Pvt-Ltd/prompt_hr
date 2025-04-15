frappe.ui.form.on('Job Applicant', {
    refresh: function (frm) {
        frm.add_custom_button('Invite for Screen Test', () => {
            if (!frm.doc.job_title) {
                frappe.msgprint(__('No Job Opening linked.'));
                return;
            }

            frappe.call({
                method: "prompt_hr.py.job_applicant.check_test_and_invite",
                args: {
                    job_applicant: frm.doc.name
                },
                callback: function (r) {

                    if (!r.message['error']) {
                        if (r.message['message'] === "redirect") {

                            frappe.set_route("Form", "Job Opening", frm.doc.job_title);
                            
                            frappe.msgprint("Please create a Screening Test for the job opening before inviting the applicant.");
                            frappe.after_ajax(() => {
                            
                                setTimeout(() => {
                                    let fieldname = 'custom_applicable_screening_test';
                                    console.log("Fieldname: ", fieldname);
                                    if (cur_frm && cur_frm.doc.doctype === 'Job Opening') {
                                        // Highlight the field's wrapper with a border
                                        let $field = cur_frm.fields_dict[fieldname]?.$wrapper;
                                        if ($field) { 
                                            frappe.utils.scroll_to($field);
                                        }
                                    }
                                }, 600);
                            });
                        } else if (r.message['message'] === "invited")
                        {
                            frappe.msgprint("Screening Test invitation sent successfully.");
                        }
                    }
                    else if (r.message['error'])  {
                        frappe.throw(r.message['message'])
                    }
                    
                }
            });
        });
    }
});

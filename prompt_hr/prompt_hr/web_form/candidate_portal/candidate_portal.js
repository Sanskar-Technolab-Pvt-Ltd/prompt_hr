frappe.ready(function () {
    // Force disable the default web form functionality
    setTimeout(function() {
        // Remove the standard submit button entirely
        $('.web-form-actions .btn-primary').remove();
        
        // Disable the form submission
        $('.web-form-container form').attr('onsubmit', 'return false;');
        $('.web-form-container form').off('submit');
        
        // Add our custom update button immediately
        if (!$('#custom-update-btn').length) {
            const customBtn = $(`
                <button id="custom-update-btn" class="btn btn-primary btn-sm" style="display:none">
                    Update Information
                </button>
            `);
            $('.web-form-actions').append(customBtn);
        }
    }, 100);
    
    // ? CREATE AND SHOW DIALOG BOX ONLOAD
    const dialog = new frappe.ui.Dialog({
        title: 'Verify Your Identity',
        fields: [
            {
                label: 'Phone Number',
                fieldname: 'phone_number',
                fieldtype: 'Data',
                reqd: 1
            },
            {
                label: 'Password',
                fieldname: 'password',
                fieldtype: 'Password',
                reqd: 1
            }
        ],
        primary_action_label: 'Verify',
        primary_action(values) {
            let filters = {
                phone_number: values.phone_number,
            }

            // ? MAKE FRAPPE CALL TO SERVER FOR VERIFICATION
            frappe.call({
                method: 'prompt_hr.prompt_hr.web_form.candidate_portal.candidate_portal.validate_candidate_portal_hash',
                args: {
                    hash: values.password,
                    doctype: "Candidate Portal",
                    filters: filters,
                    fields: ["phone_number",
                        "offer_acceptance",
                        "expected_date_of_joining",
                        "condition_for_offer_acceptance",
                        "applicant_email",
                        "applicant_name",
                        "job_offer",
                        "applied_for_designation",
                        "offer_date",
                        "offer_letter",
                        "name"
                    ]
                },
                callback: function (r) {
                    if (Array.isArray(r.message) && r.message.length > 0) {
                        const data = r.message[0];
                        const docName = data.name;
                        
                        // Store the docName in a global variable
                        window.verifiedDocName = docName;

                        frappe.msgprint('Verification successful!');
                        dialog.hide();

                        // ? SET VALUES FROM RETURNED DATA
                        Object.entries(data).forEach(([key, value]) => {
                            if (frappe.web_form.fields_dict[key]) {
                                frappe.web_form.set_value(key, value);
                            }
                        });
                        
                        // Show our custom update button
                        $('#custom-update-btn').show().off('click').on('click', function() {
                            // Get current form values
                            const formData = frappe.web_form.get_values();
                            
                            // Include the record name
                            formData.name = window.verifiedDocName;
                            
                            // Make server call to update record
                            frappe.call({
                                method: 'prompt_hr.prompt_hr.web_form.candidate_portal.candidate_portal.update_candidate_portal',
                                args: {
                                    doc: formData
                                },
                                freeze: true,
                                freeze_message: 'Updating your information...',
                                callback: function(response) {
                                    if (response.message && response.message.success) {
                                        // Hide the form and show thank you message
                                        $('.web-form-container').html(`
                                            <div class="text-center py-5">
                                                <i class="fa fa-check-circle text-success" style="font-size: 48px;"></i>
                                                <h3 class="mt-3">Thank You!</h3>
                                                <p class="lead">Your information has been successfully updated.</p>
                                                <p>You may close this window now.</p>
                                            </div>
                                        `);
                                    } else {
                                        frappe.show_alert({
                                            message: 'Error updating information: ' + 
                                              (response.message ? response.message.message : 'Unknown error'),
                                            indicator: 'red'
                                        }, 5);
                                    }
                                }
                            });
                        });
                    } else {
                        frappe.msgprint('Invalid credentials. Please try again.');
                    }
                }
            });
        }
    });

    // ? SHOW DIALOG ON WEB FORM LOAD
    dialog.show();
});
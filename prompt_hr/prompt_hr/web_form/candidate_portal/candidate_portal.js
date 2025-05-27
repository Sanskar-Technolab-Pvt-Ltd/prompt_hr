frappe.ready(function () {

    // ? FORCE DISABLE THE DEFAULT WEB FORM FUNCTIONALITY
    setTimeout(function () {
        // ? REMOVE THE STANDARD SUBMIT BUTTON ENTIRELY
        $('.web-form-actions .btn-primary').remove();

        // ? DISABLE THE FORM SUBMISSION
        $('.web-form-container form').attr('onsubmit', 'return false;');
        $('.web-form-container form').off('submit');

        // ? DISABLE ADDING OR DELETING ROWS IN THE DOCUMENTS TABLE
        frappe.web_form.set_df_property("documents", "cannot_add_rows", 1);
        frappe.web_form.set_df_property("documents", "cannot_delete_rows", 1);
        $(".row-check").hide();

        // ? ADD OUR CUSTOM UPDATE BUTTON IMMEDIATELY
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
                    child_doctypes_config: [
                        { "child_doctype": "Document Collection", "child_table_fieldname": "documents" },
                        { "child_doctype": "Document Collection", "child_table_fieldname": "new_joinee_documents" }
                    ]
                    ,
                    filters: filters,
                    fields: [
                        "phone_number",
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
                callback: async function (r) {
                    const form_data = r.message.form_data;
                    const child_tables_data = r.message.child_tables_data;
                    console.log("Form Data: ", r);

                    if (Array.isArray(form_data) && form_data.length > 0) {
                        const data = form_data[0];
                        const docName = data.name;

                        // ? STORE THE DOCNAME IN A GLOBAL VARIABLE
                        window.verifiedDocName = docName;

                        frappe.msgprint('Verification successful!');
                        dialog.hide();

                        // ? SET VALUES FROM RETURNED DATA
                        Object.entries(data).forEach(([key, value]) => {
                            if (frappe.web_form.fields_dict[key]) {
                                frappe.web_form.set_value(key, value);
                            }
                        });

                        // ? CONDITIONAL FIELD HIDING BASED ON job_offer
                        if (!data.job_offer || child_tables_data[1].child_table_data.length > 0) {
                            const fieldsToHide = [
                                "offer_date",
                                "offer_letter",
                                "job_offer",
                                "offer_acceptance",
                                "expected_date_of_joining"
                            ];
                            child_tables_data.forEach(child_table_data => {
                                if (child_table_data.child_table_data.length<1) 
                                fieldsToHide.push(child_table_data.child_table_fieldname); 
                            });
                               
                            
                            fieldsToHide.forEach(field => {
                                if (frappe.web_form.fields_dict[field]) {
                                    frappe.web_form.set_df_property(field, "hidden", 1);
                                }
                            });
                        }
                        
                        let idx = 0;
                        // ? SET THE CHILD TABLE DATA
                        child_tables_data.forEach( async child_table_data => {
                            console.log("Child Table Data: ", child_table_data);
                            child_table_fieldname = child_table_data.child_table_fieldname;
                            idx = frappe.web_form.fields_dict[child_table_fieldname].df.idx;
                            frappe.web_form.fields[idx].data = child_table_data.child_table_data;
                            // ? SET THE DOCUMENTS TABLE DATA
                            const grid = frappe.web_form.fields_dict[child_table_fieldname].grid;

                            // ? HIDE THE "name" FIELD FROM CHILD TABLE LIST VIEW
                            grid.df.fields = grid.df.fields.filter(f => f.fieldname !== "name");

                            await grid.refresh();

                            $(".row-check").hide();
                        });

                        

                        // ? SHOW OUR CUSTOM UPDATE BUTTON
                        $('#custom-update-btn').show().off('click').on('click', function () {
                            // ? GET CURRENT FORM VALUES
                            const formData = frappe.web_form.get_values();

                            // ? INCLUDE THE RECORD NAME
                            formData.name = window.verifiedDocName;

                            console.log(formData)

                            // ? MAKE SERVER CALL TO UPDATE RECORD
                            frappe.call({
                                method: 'prompt_hr.prompt_hr.web_form.candidate_portal.candidate_portal.update_candidate_portal',
                                args: {
                                    doc: formData
                                },
                                freeze: true,
                                freeze_message: 'Updating your information...',
                                callback: function (response) {
                                    if (response.message && response.message.success) {
                                        // ? HIDE THE FORM AND SHOW THANK YOU MESSAGE
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

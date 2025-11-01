frappe.ready(function () {
    if (!frappe.session.user || frappe.session.user === "Guest") {
        return;
    }
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
                        "name",
                        "department",
                        "employment_type",
                        "business_unit",
                        "employee_name",
                        "phone_no",
                        "monthly_base_salary"
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
                        })

                        // ? CONDITIONAL FIELD HIDING BASED ON job_offer
                        if (!data.job_offer || child_tables_data[1].child_table_data.length > 0) {
                            const fieldsToHide = [
                                "offer_date",
                                "offer_letter",
                                "job_offer",
                                "offer_acceptance",
                                "expected_date_of_joining",
                                "department",
                                "employment_type",
                                "business_unit",
                                "employee_name",
                                "phone_no",
                                "monthly_base_salary"
                            ];
                            console.log("Fields to Hide: ", fieldsToHide);
                            console.log("Child Tables Data: ", child_tables_data);
                            child_tables_data.forEach(child_table_data => {
                                if (child_table_data.child_table_data.length<1) {
                                fieldsToHide.push(child_table_data.child_table_fieldname); 
                                console.log("Child Table Field Name: ", child_table_data.child_table_fieldname);
                                }
                            });

                            if (child_tables_data[1].child_table_data.length > 0)
                                fieldsToHide.push("documents");

                            
                            fieldsToHide.forEach(field => {
                                if (frappe.web_form.fields_dict[field]) {
                                    frappe.web_form.set_df_property(field, "hidden", 1);
                                }
                            });
                        }

                        else if (data.job_offer) {
                            
                            const fieldsToHide = []
                            child_tables_data.forEach(child_table_data => {
                                if (child_table_data.child_table_data.length < 1) {
                                    fieldsToHide.push(child_table_data.child_table_fieldname);
                                }
                            });
                            fieldsToHide.forEach(field => {
                                if (frappe.web_form.fields_dict[field]) {
                                    frappe.web_form.set_df_property(field, "hidden", 1);
                                }
                            });
                        }
                        // Customize the display of the offer letter field if value exists
                        const offerLetterValue = data.offer_letter;    
                        if (offerLetterValue) {    
                            const $fieldWrapper = $(`[data-fieldname="offer_letter"]`).closest('.frappe-control');    
                            
                            // Hide ALL visible parts of the Attach field  
                            $fieldWrapper.find('.control-input').hide();      // Hide the attach button  
                            $fieldWrapper.find('.attached-file').hide();      // Hide the file display area  
                            $fieldWrapper.find('.control-value').hide();      // Hide any value display  
                            
                            // Create the download URL    
                            const downloadUrl = `/api/method/prompt_hr.prompt_hr.web_form.candidate_portal.candidate_portal.get_candidate_portal_file_public?doc_name=${window.verifiedDocName}&file_field=offer_letter`;    
                            
                            // Add button with click handler    
                            $fieldWrapper.find('.control-input-wrapper').append(`    
                                <div class="offer-letter-link" style="margin-top: 10px;">    
                                    <button class="btn btn-default btn-sm" id="view-offer-letter-btn">    
                                        <i class="fa fa-file-pdf-o"></i> View Offer Letter    
                                    </button>    
                                </div>    
                            `);    
                            
                            // Attach click handler to open file in new tab    
                            $('#view-offer-letter-btn').on('click', function() {    
                                window.open(downloadUrl, '_blank');    
                            });
                        }
                        let idx = 0;
                        // ? SET THE CHILD TABLE DATA
                        child_tables_data.forEach( async child_table_data => {
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

                        // ? BEAUTIFUL TOP "DAYS TO GO" HIGHLIGHT CARD
                        if (data.expected_date_of_joining) {

                            // Convert dates
                            const currentDate = frappe.datetime.str_to_obj(frappe.datetime.get_today());
                            const joinDate = frappe.datetime.str_to_obj(data.expected_date_of_joining);

                            if (currentDate && joinDate) {
                                const diffMs = joinDate - currentDate;
                                const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

                                // Remove if already added
                                $(".days-to-go-banner").remove();

                                // Determine banner style based on days
                                let bgColor = "#e8f0fe";     // Default blue theme
                                let textColor = "#1a73e8";
                                let emoji = "⏳";

                                if (diffDays <= 3) {
                                    bgColor = "#fdecea";     // Light red
                                    textColor = "#d93025";   // Dark red
                                    emoji = "⌛";
                                } else if (diffDays <= 10) {
                                    bgColor = "#fff8e1";     // Light yellow
                                    textColor = "#f9a825";   // Gold
                                    emoji = "⌛";
                                } else {
                                    bgColor = "#e8f5e9";
                                    textColor = "#1b5e20";
                                    emoji = "⌛"
                                }

                                // ✅ Insert beautiful banner at the top of the page
                                $(".web-form-container").prepend(`
                                    <div class="days-to-go-banner"
                                        style="
                                            background: ${bgColor};
                                            border-left: 6px solid ${textColor};
                                            padding: 15px 20px;
                                            border-radius: 6px;
                                            margin-bottom: 20px;
                                            font-size: 18px;
                                            font-weight: 600;
                                            display: flex;
                                            align-items: center;
                                            gap: 10px;
                                        ">
                                        <span style="font-size: 22px;">${emoji}</span>
                                        <div>
                                            Joining in <span style="color:${textColor}; font-weight:800;">
                                                ${diffDays} day(s)
                                            </span>
                                        </div>
                                    </div>
                                `);
                            }
                        }

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

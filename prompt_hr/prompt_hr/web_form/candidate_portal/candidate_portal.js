frappe.ready(async function () {
    
    if (!frappe.session.user || frappe.session.user === "Guest") {
        //? AUTO LOGIN USER TO ACCESS CANDIDATE PORTAL
        await frappe.call({
            method: "login",
            type: "POST",
            args: {
                usr: "candidate@promptdairytech.com",
                pwd: "Candidate@123"
            },
            callback: function (r) {
                if (r.message) {
                    console.log("Login Successful!"); 
                    window.location.reload();   
                }
            },
            error: function(err) {
                console.log("Login Failed:", err);
            }
        });
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

                    if (Array.isArray(form_data) && form_data.length > 0) {
                        const data = form_data[0];
                        const docName = data.name;

                        // ? STORE THE DOCNAME IN A GLOBAL VARIABLE
                        window.verifiedDocName = docName;

                        // frappe.msgprint('Verification successful!');
                        dialog.hide();

                        localStorage.setItem("portal_phone", values.phone_number);
                        localStorage.setItem("portal_hash", values.password);

                        // ? SET VALUES FROM RETURNED DATA
                        Object.entries(data).forEach(([key, value]) => {
                            if (frappe.web_form.fields_dict[key]) {
                                frappe.web_form.set_value(key, value);
                            }
                        })
                        let workflow_state = ""
                        if (data.job_offer) {
                                try {
                                    const result = await frappe.call({
                                        method: "prompt_hr.prompt_hr.web_form.candidate_portal.candidate_portal.get_job_offer_workflow_state",
                                        args: { job_offer_name: data.job_offer },
                                        freeze: true,
                                    });

                                    workflow_state = result.message?.workflow_state || null;
                                } catch (error) {
                                    console.error("Error fetching workflow_state:", error);
                                    workflow_state = null;
                                }
                        }

                        // ? CONDITIONAL FIELD HIDING BASED ON job_offer
                        if (!data.job_offer || child_tables_data[1].child_table_data.length > 0 || workflow_state !== "Approved") {
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

                            child_tables_data.forEach(child_table_data => {
                                if (child_table_data.child_table_data.length<1) {
                                fieldsToHide.push(child_table_data.child_table_fieldname); 
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

                        if (workflow_state === "Approved" && data.job_offer) {
                            const breakup = data.salary_break_up;                            
                            if (breakup) {
                                // ✅ Remove existing button and wrapper
                                $(".salary-breakup-btn-wrapper").remove();
                                $(".salary-breakup-btn").remove();

                                // ✅ Add button inside form container with proper styling
                                const buttonHtml = `
                                    <div class="salary-breakup-btn-wrapper" style="margin: 0 0 24px 0; padding: 0;">
                                        <button class="btn btn-primary btn-sm salary-breakup-btn" 
                                                style="display: inline-flex; align-items: center; gap: 8px; font-weight: 500;">
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                                <line x1="3" y1="9" x2="21" y2="9"></line>
                                                <line x1="9" y1="21" x2="9" y2="9"></line>
                                            </svg>
                                            View Salary Breakup
                                        </button>
                                    </div>
                                `;

                                // ✅ Insert at the beginning of form fields (inside container)
                                const $target = $(".web-form-container .form-section:first, .web-form-container form:first").first();
                                if ($target.length) {
                                    $target.prepend(buttonHtml);
                                } else {
                                    // Fallback: try direct container
                                    $(".web-form-container").prepend(buttonHtml);
                                }

                                // ✅ On click → open dialog (use event delegation to avoid duplicate handlers)
                                $(document).off("click", ".salary-breakup-btn").on("click", ".salary-breakup-btn", function (e) {
                                    e.preventDefault();
                                    show_salary_breakup_dialog(breakup);
                                });
                            }
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
                        if (
                            data.expected_date_of_joining &&
                            (data.offer_acceptance == "Accepted" ||
                            data.offer_acceptance == "Accepted with Condition")
                        ) {
                            const currentDate = frappe.datetime.str_to_obj(frappe.datetime.get_today());
                            const joinDate = frappe.datetime.str_to_obj(data.expected_date_of_joining);

                            if (currentDate && joinDate) {
                                const diffMs = joinDate - currentDate;
                                const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

                                // Remove existing banner
                                $(".days-to-go-banner").remove();

                                // ✅ If joining date is already passed
                                if (diffDays < 0) {
                                    $(".web-form-container").prepend(`
                                        <div class="days-to-go-banner"
                                            style="
                                                background: #ffecec;
                                                border-left: 6px solid #d93025;
                                                padding: 15px 20px;
                                                border-radius: 6px;
                                                margin-bottom: 20px;
                                                font-size: 18px;
                                                font-weight: 600;
                                                display: flex;
                                                align-items: center;
                                                gap: 10px;
                                            ">
                                            <span style="font-size: 22px;">⚠️</span>
                                            <div>
                                                Expected joining date has <span style="color:#d93025; font-weight:800;">
                                                    already passed
                                                </span>.
                                            </div>
                                        </div>
                                    `);
                                    return; // ✅ Stop further processing
                                }

                                // ✅ Default banner styles
                                let bgColor = "#e8f0fe";
                                let textColor = "#1a73e8";
                                let emoji = "⏳";

                                if (diffDays <= 3) {
                                    bgColor = "#fdecea";
                                    textColor = "#d93025";
                                    emoji = "⌛";
                                } else if (diffDays <= 10) {
                                    bgColor = "#fff8e1";
                                    textColor = "#f9a825";
                                    emoji = "⌛";
                                } else {
                                    bgColor = "#e8f5e9";
                                    textColor = "#1b5e20";
                                    emoji = "⌛";
                                }

                                // ✅ Normal future date banner
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
    const savedPhone = localStorage.getItem("portal_phone");
    const savedHash = localStorage.getItem("portal_hash");

    if (savedPhone && savedHash) {
        dialog.set_values({
            phone_number: savedPhone,
            password: savedHash
        });

        dialog.primary_action({
            phone_number: savedPhone,
            password: savedHash
        });
    } else {
        dialog.show();
    }
});


async function show_salary_breakup_dialog(salary_breakup) {
    if (!salary_breakup || (!salary_breakup.earnings?.length && !salary_breakup.deductions?.length)) {
        frappe.msgprint("Salary breakup is not available.");
        return;
    }

    // ✅ Calculate totals
    let total_earnings = salary_breakup.earnings.reduce((t, r) => t + (r.amount || 0), 0);
    let total_deductions = salary_breakup.deductions.reduce((t, r) => t + (r.amount || 0), 0);
    let net_pay = total_earnings - total_deductions;

    // ✅ Build enhanced earnings table
    let earnings_html = `
        <div style="margin-bottom: 32px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                <div style="width: 4px; height: 24px; background: #10b981; border-radius: 2px;"></div>
                <h4 style="margin: 0; font-weight: 600; color: #1f2937;">Earnings</h4>
            </div>
            <table class="table table-bordered" style="margin: 0; border-radius: 8px; overflow: hidden;">
                <thead style="background: #f9fafb;">
                    <tr>
                        <th style="padding: 12px 16px; font-weight: 600; color: #6b7280; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;">Component</th>
                        <th style="padding: 12px 16px; text-align: right; font-weight: 600; color: #6b7280; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;">Amount</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    salary_breakup.earnings.forEach((row, index) => {
        const bgColor = index % 2 === 0 ? '#ffffff' : '#f9fafb';
        earnings_html += `
            <tr style="background: ${bgColor};">
                <td style="padding: 12px 16px; color: #374151;">${row.salary_component}</td>
                <td style="padding: 12px 16px; text-align: right; font-weight: 500; color: #10b981;">${format_currency(row.amount)}</td>
            </tr>
        `;
    });
    
    earnings_html += `
                <tr style="background: #ecfdf5; border-top: 2px solid #10b981;">
                    <td style="padding: 12px 16px; font-weight: 600; color: #065f46;">Total Earnings</td>
                    <td style="padding: 12px 16px; text-align: right; font-weight: 700; color: #10b981; font-size: 15px;">${format_currency(total_earnings)}</td>
                </tr>
            </tbody>
        </table>
        </div>
    `;

    // ✅ Build enhanced deductions table
    let deductions_html = `
        <div style="margin-bottom: 32px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                <div style="width: 4px; height: 24px; background: #ef4444; border-radius: 2px;"></div>
                <h4 style="margin: 0; font-weight: 600; color: #1f2937;">Deductions</h4>
            </div>
            <table class="table table-bordered" style="margin: 0; border-radius: 8px; overflow: hidden;">
                <thead style="background: #f9fafb;">
                    <tr>
                        <th style="padding: 12px 16px; font-weight: 600; color: #6b7280; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;">Component</th>
                        <th style="padding: 12px 16px; text-align: right; font-weight: 600; color: #6b7280; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;">Amount</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    salary_breakup.deductions.forEach((row, index) => {
        const bgColor = index % 2 === 0 ? '#ffffff' : '#f9fafb';
        deductions_html += `
            <tr style="background: ${bgColor};">
                <td style="padding: 12px 16px; color: #374151;">${row.salary_component}</td>
                <td style="padding: 12px 16px; text-align: right; font-weight: 500; color: #ef4444;">${format_currency(row.amount)}</td>
            </tr>
        `;
    });
    
    deductions_html += `
                <tr style="background: #fef2f2; border-top: 2px solid #ef4444;">
                    <td style="padding: 12px 16px; font-weight: 600; color: #991b1b;">Total Deductions</td>
                    <td style="padding: 12px 16px; text-align: right; font-weight: 700; color: #ef4444; font-size: 15px;">${format_currency(total_deductions)}</td>
                </tr>
            </tbody>
        </table>
        </div>
    `;

    // ✅ Enhanced summary section
    let summary_html = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 24px; border-radius: 12px; color: white;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                <div>
                    <div style="font-size: 13px; opacity: 0.9; margin-bottom: 4px; font-weight: 500;">Total Earnings</div>
                    <div style="font-size: 20px; font-weight: 700;">${format_currency(total_earnings)}</div>
                </div>
                <div>
                    <div style="font-size: 13px; opacity: 0.9; margin-bottom: 4px; font-weight: 500;">Total Deductions</div>
                    <div style="font-size: 20px; font-weight: 700;">${format_currency(total_deductions)}</div>
                </div>
                <div style="background: rgba(255, 255, 255, 0.2); 
                           padding: 16px; border-radius: 8px; 
                           backdrop-filter: blur(10px);">
                    <div style="font-size: 13px; opacity: 0.9; margin-bottom: 4px; font-weight: 500;">Net Pay</div>
                    <div style="font-size: 24px; font-weight: 700;">${format_currency(net_pay)}</div>
                </div>
            </div>
        </div>
    `;

    // ✅ Create dialog with enhanced styling
    let d = new frappe.ui.Dialog({
        title: "💰 Salary Breakup Details",
        size: "large",
        fields: [
            { fieldname: "earnings_html", fieldtype: "HTML" },
            { fieldname: "deductions_html", fieldtype: "HTML" },
            { fieldname: "summary_html", fieldtype: "HTML" },
        ]
    });

    d.fields_dict.earnings_html.$wrapper.html(earnings_html);
    d.fields_dict.deductions_html.$wrapper.html(deductions_html);
    d.fields_dict.summary_html.$wrapper.html(summary_html);

    // ✅ Add custom styling to dialog
    d.$wrapper.find('.modal-content').css({
        'border-radius': '12px',
        'box-shadow': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
    });

    d.show();
}

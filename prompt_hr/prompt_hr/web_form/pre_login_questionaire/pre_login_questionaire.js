frappe.ready(function () {
    // HIDE DEFAULT BUTTONS
    $(".web-form-actions").hide();

    // SELECT ALL AUTOCOMPLETE INPUTS
    let autocompleteFields = document.querySelectorAll('input[data-fieldtype="Autocomplete"]');

    autocompleteFields.forEach(field => {
        field.addEventListener('input', function(e) {
            let value = e.target.value;
            let fieldname = e.target.getAttribute('data-fieldname');

            // GET THE FRAPPE FIELD CONTROL
            let control = frappe.web_form?.fields_dict[fieldname];

            if (control) {
                // CALL YOUR FUNCTION
                frappe.call({
                    method: "prompt_hr.prompt_hr.web_form.pre_login_questionaire.pre_login_questionaire.make_autocomplete_options",
                    args: {
                        fieldname: fieldname,
                        searchtxt: value
                    },
                    callback: function(r) {
                        if (!r.exc && r.message) {
                            // ? UPDATE CONTROL OPTIONS
                            if (control.set_data) {  
                                // ? FOR AUTOCOMPLETE CONTROLS  
                                control.set_data(r.message);  
                            } else if (control.awesomplete) {  
                                // ? FOR LINK CONTROLS OR DIRECT AWESOMPLETE ACCESS  
                                control.awesomplete.list = r.message;  
                            }  

                        }
                    }
                    
                });
            }
        });
    });


    // ADD CUSTOM SUBMIT BUTTON
    let customBtn = $(`<button class="btn btn-primary mt-3">Submit Questionnaire</button>`);
    $(".web-form-footer").append(customBtn);

    customBtn.on("click", function (e) {
        e.preventDefault();

        let responses = [];

        (frappe.web_form?.web_form_fields || []).forEach(field => {
            // GET THE CONTROL OBJECT
            let control = frappe.web_form.fields_dict?.[field.fieldname];

            if (control && control.get_value) {
                responses.push({
                    fieldname: field.fieldname,   // INTERNAL FIELDNAME
                    label: field.label || "",     // FIELD LABEL
                    value: control.get_value()    // USER INPUT VALUE
                });
            }
        });


        // ? CALL BACKEND METHOD FOR SUBMISSION OF DATA
        frappe.call({
            method: "prompt_hr.py.employee.employee_questionnaire_submit",
            args: {
                responses: responses,
            },
            freeze: true,
            freeze_message: "Submitting your responses...",
            callback: function (r) {
                if (!r.exc) {
                    frappe.msgprint("Questionnaire submitted successfully!");
                    showThankYouPage()
                } else {
                    frappe.msgprint("Error while submitting questionnaire.");
                }
            }
        });
    });
});


// ? SHOW THANK YOU PAGE AFTER ALL RESPONSES ARE APPROVED
function showThankYouPage(frm) {
    $('.web-form-container').html(`
            <div class="text-center py-5">
                <i class="fa fa-hourglass-half text-warning" style="font-size: 48px;"></i>
                <h3 class="mt-3">Waiting for Approval</h3>
                <p class="lead">Your responses are still pending approval.</p>
                <p>Please check back later.</p>
            </div>
        `);
    
}

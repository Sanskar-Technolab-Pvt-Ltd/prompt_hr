$(document).ready(function () {
    console.log("Display Fix Solution loaded");
	let employeeField = getEmployeeField();
        if (employeeField.length > 0) {
            employeeField.prop('readonly', true);
            console.log("Employee field enabled for HR/Admin.");
        }
    // Call the backend method to check user role and employee
    frappe.call({
        method: "prompt_hr.prompt_hr.web_form.exit_questionnaire.exit_questionnaire.check_user_role_and_employee",  // Update this with your actual method path
        callback: function(response) {
            const isHrOrAdmin = response.message.is_hr_or_admin;
            const sessionEmployee = response.message.employee;

            if (isHrOrAdmin) {
                // Allow HR or Admin to fill the employee field
                enableEmployeeField();
            } else {
                // Set the employee field to session's employee
                setEmployeeField(sessionEmployee);
            }
        },
        error: function (err) {
            console.error("Error fetching user role and employee:", err);
        }
    });

    // Function to enable the employee field (allow HR or Admin to select)
    function enableEmployeeField() {
        let employeeField = getEmployeeField();
        if (employeeField.length > 0) {
            employeeField.prop('readonly', false);
            console.log("Employee field enabled for HR/Admin.");
        }
    }

    // Function to set the employee field value for non-HR/Admin (set from session)
 	function setEmployeeField(employee) {
        let employeeField = getEmployeeField();
        if (employeeField.length > 0) {
            employeeField.val(employee)
			// frappe.web_form.set_df_property('employee', 'read_only', 1);
            console.log("Employee field set to session employee:", employee);
        }
    }

    // Function to get the employee field
    function getEmployeeField() {
        let field = $('select[name="employee"], input[name="employee"]');
        if (field.length === 0) {
            field = $('[data-fieldname="employee"]').find('input');
        }
        if (field.length === 0) {
            field = $('select.employee-field, input.employee-field');
        }
        return field;
    }

    // Hide the default Save button but keep the discard button visible
    $('.right-area .submit-btn').hide();
    $('.web-form-actions .discard-btn').show();
    
    // Prevent default form submission
    $('form.web-form').on('submit', function(e) {
        e.preventDefault();
        console.log("Default form submission prevented");
        return false;
    });

    // Function to periodically check for changes in employee field value
    function setupValueChangeDetection() {
        let lastVal = '';
        let employeeField = getEmployeeField();

        if (employeeField.length > 0) {
            console.log("Setting up value change detection");
            lastVal = employeeField.val();

            // Polling for value changes
            setInterval(function () {
                const currentVal = employeeField.val();
                if (currentVal !== lastVal && currentVal) {
                    console.log("Value changed from", lastVal, "to", currentVal);
                    lastVal = currentVal;
                    fetchQuestions(currentVal);
                }
            }, 500);

            // Manual event handlers
            employeeField.on('change input blur', function () {
                const val = $(this).val();
                console.log("Direct event detected, value:", val);
                if (val) {
                    fetchQuestions(val);
                }
            });

            // Initial value trigger
            const initialVal = employeeField.val();
            if (initialVal) {
                console.log("Initial value found:", initialVal);
                fetchQuestions(initialVal);
            }

            // Make employee field readonly after interaction
            employeeField.on('blur', function () {
                $(this).prop('readonly', true);
                console.log("Employee field set to read-only");
            });
        } else {
            setTimeout(setupValueChangeDetection, 1000); // Retry if not found
        }
    }

    // Begin monitoring employee field
    setupValueChangeDetection();

    // Fetch interview questions from backend
    function fetchQuestions(employee) {
        console.log("Fetching questions for employee:", employee);

        if ($('#question-container').length === 0) {
            $('form.web-form').append('<div id="question-container" class="mt-4"></div>');
        }

        $('#question-container').html('<p>Loading questions...</p>');

        frappe.call({
            method: "prompt_hr.prompt_hr.web_form.exit_questionnaire.exit_questionnaire.fetch_interview_questions",
            args: { employee: employee },
            callback: function (response) {
                if (response.message && response.message.length > 0) {
                    console.log("Questions fetched:", response.message);
                    displayQuestions(response.message);
                } else {
                    $('#question-container').html('<p>No questions available for this employee.</p>');
                }
            },
            error: function (err) {
                console.error("API error:", err);
                $('#question-container').html('<p>Error loading questions: ' + (err.message || 'Unknown error') + '</p>');
            }
        });
    }

    // Render the questions into the DOM
    function displayQuestions(questions) {
        const questionContainer = $('#question-container');
        questionContainer.empty();
    
        questionContainer.append('<h3 class="mb-4">Exit Interview Questions</h3>');
    
        questions.forEach((question, index) => {
            const questionHtml = `
                <div class="question-item mb-2 p-2 border rounded bg-light" style="font-size: 14px;">
                    <p>${question.question_detail || 'No question details available'}</p>
                    <textarea class="form-control" rows="2" name="answer-${question.question}" style="font-size: 14px;"></textarea>
                </div>
            `;
            questionContainer.append(questionHtml);
            console.log("Rendered question:", index + 1, question.question_detail);
        });
    
        questionContainer.append('<p class="text-muted">Please answer all questions above.</p>');
        addButtons();
    }

    // Add Save Response button (only once)
    function addButtons() {
        if ($('#save-response').length === 0) {
            const buttonsHtml = `
                <div class="mt-3">
                    <button type="button" id="save-response" class="btn btn-primary">Save Response</button>
                </div>
            `;
            $('form.web-form').append(buttonsHtml);

            $('#save-response').on('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                
                frappe.confirm(
                    'Are you sure you want to save your responses?',
                    function () {
                        saveResponse();
                    },
                    function () {
                        console.log("Save action cancelled.");
                    }
                );
                
                return false;
            });
        }
    }

    // Collect and save responses via API
    function saveResponse() {
        const responses = [];
        const employeeField = getEmployeeField();
        const employee = employeeField.val();
    
        // Loop through each textarea and map answers to question.name
        $('#question-container textarea').each(function () {
            const questionName = $(this).attr('name').replace('answer-', '');
            const answer = $(this).val();
            responses.push({
                question: questionName,
                answer: answer
            });
        });
        console.log("Employee value:", employee);
        console.log("Collected responses:", responses);
    
        frappe.call({
            method: "prompt_hr.prompt_hr.web_form.exit_questionnaire.exit_questionnaire.save_response",
            args: { 
                employee: employee,
                response: responses
            },
            callback: function (response) {
                console.log("Responses saved successfully:", response);
                showThankYouPage();
            },
            error: function (err) {
                console.error("Error saving responses:", err);
                alert("There was an error saving your responses: " + (err.message || 'Unknown error'));
            }
        });
    }
    
    // Disable only the default save button but keep discard button
    setTimeout(function() {
        // Target only the submit/save button in web-form-actions, not all buttons
        $('.web-form-actions .btn-primary, .right-area .submit-btn').off('click').prop('disabled', true);
        console.log("Disabled default save button, kept discard button functional");
    }, 1000);
});

// Show Thank You page after successful response save
function showThankYouPage() {
    $('.web-form-container').html(`
        <div class="text-center py-5">
            <i class="fa fa-check-circle text-success" style="font-size: 48px;"></i>
            <h3 class="mt-3">Thank You!</h3>
            <p class="lead">Your information has been successfully updated.</p>
            <p>You may close this window now.</p>
        </div>
    `);
}

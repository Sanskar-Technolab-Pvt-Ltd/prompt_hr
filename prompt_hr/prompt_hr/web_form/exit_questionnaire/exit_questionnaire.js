$(document).ready(function () {

    // ? CALL THE BACKEND METHOD TO CHECK USER ROLE AND EMPLOYEE
    frappe.call({
        method: "prompt_hr.prompt_hr.web_form.exit_questionnaire.exit_questionnaire.check_user_role_and_employee",  
        callback: function(response) {
            const isHrOrAdmin = response.message.is_hr_or_admin;
            const sessionEmployee = response.message.employee;

            if (isHrOrAdmin) {
                // ? ALLOW HR OR ADMIN TO FILL THE EMPLOYEE FIELD
                enableEmployeeField();
            } else {
                // ? SET THE EMPLOYEE FIELD TO SESSION'S EMPLOYEE
                setEmployeeField(sessionEmployee);
            }
        },
        error: function (err) {
            console.error("Error fetching user role and employee:", err);
        }
    });

    // ? FUNCTION TO ENABLE THE EMPLOYEE FIELD (ALLOW HR OR ADMIN TO SELECT)
    function enableEmployeeField() {
        let employeeField = getEmployeeField();
        if (employeeField.length > 0) {
            employeeField.prop('readonly', false);
        }
    }

    // ? FUNCTION TO SET THE EMPLOYEE FIELD VALUE FOR NON-HR/ADMIN (SET FROM SESSION)
 	function setEmployeeField(employee) {
        let employeeField = getEmployeeField();
        if (employeeField.length > 0) {
            employeeField.val(employee).prop('readonly', true);
        }
    }

    // ? FUNCTION TO GET THE EMPLOYEE FIELD
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

    // ? HIDE THE DEFAULT SAVE BUTTON BUT KEEP THE DISCARD BUTTON VISIBLE
    $('.right-area .submit-btn').hide();
    $('.web-form-actions .discard-btn').show();
    
    // ? PREVENT DEFAULT FORM SUBMISSION
    $('form.web-form').on('submit', function(e) {
        e.preventDefault();
        console.log("Default form submission prevented");
        return false;
    });

    // ? FUNCTION TO PERIODICALLY CHECK FOR CHANGES IN EMPLOYEE FIELD VALUE
    function setupValueChangeDetection() {
        let lastVal = '';
        let employeeField = getEmployeeField();

        if (employeeField.length > 0) {
            console.log("Setting up value change detection");
            lastVal = employeeField.val();

            // ? POLLING FOR VALUE CHANGES
            setInterval(function () {
                const currentVal = employeeField.val();
                if (currentVal !== lastVal && currentVal) {
                    console.log("Value changed from", lastVal, "to", currentVal);
                    lastVal = currentVal;
                    fetchQuestions(currentVal);
                }
            }, 500);

            // ? MANUAL EVENT HANDLERS
            employeeField.on('change input blur', function () {
                const val = $(this).val();
                console.log("Direct event detected, value:", val);
                if (val) {
                    fetchQuestions(val);
                }
            });

            // ? INITIAL VALUE TRIGGER
            const initialVal = employeeField.val();
            if (initialVal) {
                console.log("Initial value found:", initialVal);
                fetchQuestions(initialVal);
            }

            // ? MAKE EMPLOYEE FIELD READONLY AFTER INTERACTION
            employeeField.on('blur', function () {
                $(this).prop('readonly', true);
                console.log("Employee field set to read-only");
            });
        } else {
            setTimeout(setupValueChangeDetection, 1000); 
        }
    }

    // ? BEGIN MONITORING EMPLOYEE FIELD
    setupValueChangeDetection();

    // ? FETCH INTERVIEW QUESTIONS FROM BACKEND
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

    // ? RENDER THE QUESTIONS INTO THE DOM
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

    // ? ADD SAVE RESPONSE BUTTON (ONLY ONCE)
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

    // ? COLLECT AND SAVE RESPONSES VIA API
    function saveResponse() {
        const responses = [];
        const employeeField = getEmployeeField();
        const employee = employeeField.val();
    
        // ? LOOP THROUGH EACH TEXTAREA AND MAP ANSWERS TO QUESTION.NAME
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
    
    // ? DISABLE ONLY THE DEFAULT SAVE BUTTON BUT KEEP DISCARD BUTTON
    setTimeout(function() {
        // ? TARGET ONLY THE SUBMIT/SAVE BUTTON IN WEB-FORM-ACTIONS, NOT ALL BUTTONS
        $('.web-form-actions .btn-primary, .right-area .submit-btn').off('click').prop('disabled', true);
        console.log("Disabled default save button, kept discard button functional");
    }, 1000);
});

// ? SHOW THANK YOU PAGE AFTER SUCCESSFUL RESPONSE SAVE
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

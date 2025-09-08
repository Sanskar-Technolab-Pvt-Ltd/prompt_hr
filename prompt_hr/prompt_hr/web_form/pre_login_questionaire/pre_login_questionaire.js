frappe.ready(function () {
    // RUN AFTER WEB FORM LOAD
    let responses = frappe.web_form_doc.questionnaire_responses	|| [];
    console.log('Pre-login questionnaire responses:', responses);

    // IF YOU WANT TO MANIPULATE THE TABLE FROM CONTEXT
    if (typeof questionnaire_responses !== "undefined") {
        questionnaire_responses.forEach(row => {
            console.log("Question:", row.field_label, "Status:", row.status);
        });
    }

    // EXAMPLE: AUTO-MARK STATUS WHEN USER CLICKS A BUTTON
    $(document).on("click", ".mark-complete", function () {
        let field = $(this).data("field");
        frappe.call({
            method: "frappe.client.set_value",
            args: {
                doctype: "Employee Questionnaire Response",
                name: field,
                fieldname: "status",
                value: "Completed"
            },
            callback: function () {
                frappe.show_alert("Status Updated ✅");
            }
        });
    });
});

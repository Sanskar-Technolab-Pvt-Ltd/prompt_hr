

frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
        // ? Call the function to add the button
        add_redirect_button(frm);
    },
});

// ? FUNCTION TO ADD REDIRECTION BUTTON
function add_redirect_button(frm) {
    frm.add_custom_button('Process FnF', function() {

        // ? Redirect to Full and Final Statement page using the base URL
        window.location.href = `${window.location.origin}/app/full-and-final-statement/new-1`;
    });
}
$(document).ready(function () {
    // ? CHECK ON INITIAL PAGE LOAD
    redirect_to_web_form_if_needed();

    // ? CHECK AGAIN WHENEVER THE ROUTE CHANGES (E.G., BACK BUTTON)
    if (frappe.router && frappe.router.on) {
        frappe.router.on('change', () => {
            redirect_to_web_form_if_needed();
        });
    }
});

// ? FUNCTION TO REDIRECT USER TO WELCOME FORM IF VALIDATION PASSES
function redirect_to_web_form_if_needed() {
    if (frappe.session.user === 'Guest') return;
    console.log(frappe.session.user)
    // ? SKIP REDIRECT IF ALREADY ON WELCOME FORM
    if (window.location.pathname.includes('/pre-login-questionaire/new')) return;

    frappe.call({
        method: "prompt_hr.py.employee.check_web_form_validation",
        args: {
            user_id: frappe.session.user,
        },
        callback: function (r) {
            console.log(r)
            if (r.message && r.message.success !== 1) {
                const { is_completed } = r.message.data;
                if (!is_completed) {
                    const route = `/pre-login-questionaire/new`;
                    console.log("Redirecting to Welcome Page:", route);
                    window.location.href = route;
                }
            }
        }
    });
}

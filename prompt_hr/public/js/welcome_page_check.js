// ? public/js/welcome_page_redirect.js
$(document).ready(function () {
    // ? CHECK ON INITIAL PAGE LOAD
    redirect_to_welcome_if_needed();

    // ? CHECK AGAIN WHENEVER THE ROUTE CHANGES (E.G., BACK BUTTON)
    if (frappe.router && frappe.router.on) {
        frappe.router.on('change', () => {
            redirect_to_welcome_if_needed();
        });
    }
});

// ? FUNCTION To redirect user to Welcome Page if validation passes
function redirect_to_welcome_if_needed() {
    if (frappe.session.user === 'Guest') return;

    // ? SKIP REDIRECT IF ALREADY ON WELCOME PAGE
    if (window.location.pathname.includes('/app/welcome-page/')) return;

    frappe.call({
        method: "prompt_hr.prompt_hr.doctype.welcome_page.welcome_page.check_welcome_page_validation",
        args: {
            user_id: frappe.session.user,
        },
        callback: function (r) {
            console.log(r)
            if (r.message && r.message.success === 1 && r.message.data) {
                const { name, is_completed } = r.message.data;
                if (!is_completed) {
                    const route = `/app/welcome-page/${encodeURIComponent(name)}`;
                    console.log("Redirecting to Welcome Page:", route);
                    window.location.href = route;
                }
            } 
        }
    });
}

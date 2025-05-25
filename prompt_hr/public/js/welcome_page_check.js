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

function redirect_to_welcome_if_needed() {
    if (frappe.session.user === 'Guest') return;

    // ? SKIP IF ALREADY ON WELCOME PAGE
    if (window.location.pathname.includes('/app/welcome-page/')) return;

    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Welcome Page",
            filters: { user: frappe.session.user },
            fieldname: ["name", "is_completed"]
        },
        callback: function (r) {
            if (r.message && r.message.name && !r.message.is_completed) {
                const name = encodeURIComponent(r.message.name);
                const route = `/app/welcome-page/${name}`;
                console.log("Redirecting to Welcome Page:", route);
                window.location.href = route;
            }
        }
    });
}

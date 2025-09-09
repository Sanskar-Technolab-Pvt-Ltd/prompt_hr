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
    // ? SKIP FOR GUEST OR ADMIN
    if (frappe.session.user === "Guest" || frappe.session.user === "Administrator") return;

    // ? SKIP IF ALREADY ON WELCOME FORM
    if (window.location.pathname.includes("/pre-login-questionaire/new")) return;

    // ? CHECK IF USER IS HR MANAGER OR SYSTEM MANAGER
    if (frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager") || frappe.user.has_role("S - HR Director (Global Admin)")) {
        return;
    }

    // ? CHECK IF EMPLOYEE EXISTS FOR THIS USER
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Employee",
            filters: { user_id: frappe.session.user },
            fieldname: "name"
        },
        callback: function (res) {
            let employee = res.message ? res.message.name : null;

            if (!employee) {
                return;
            }

            // ? CALL YOUR CUSTOM VALIDATION METHOD
            frappe.call({
                method: "prompt_hr.py.employee.check_web_form_validation",
                args: {
                    user_id: frappe.session.user,
                },
                callback: function (r) {
                    if (r.message && r.message.success !== 1) {
                        const { is_completed } = r.message.data;
                        if (!is_completed) {
                            const route = `/pre-login-questionaire/new`;
                            window.location.href = route;
                        }
                    }
                }
            });
        }
    });
}

$(document).ready(function () {
    // ? CHECK ON INITIAL PAGE LOAD
    redirect_to_proper_page();

    // ? CHECK AGAIN WHENEVER ROUTE CHANGES (E.G., BACK BUTTON)
    if (frappe.router && frappe.router.on) {
        frappe.router.on('change', () => {
            redirect_to_proper_page();
        });
    }
});

// ? COMBINED REDIRECTION HANDLER FOR EMPLOYEE & CANDIDATE
function redirect_to_proper_page() {
    // ? SKIP FOR GUEST USERS
    if (frappe.session.user === 'Guest') return;

    // ? CHECK IF GENERIC CANDIDATE USER
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        handle_candidate_job_offer_redirect();
        return;
    }

    // ? ONLY FOR USERS WITH 'Employee' ROLE
    if (!frappe.session.user_roles.includes("Employee")) return;

    // ? SKIP IF ALREADY ON WELCOME PAGE
    if (window.location.pathname.includes('/app/welcome-page/')) return;

    // ? FETCH WELCOME PAGE STATUS FOR CURRENT USER
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

                // ? REDIRECT TO WELCOME PAGE IF NOT COMPLETED
                console.log("Redirecting to Welcome Page:", route);
                window.location.href = route;
            }
        }
    });
}

// ? CANDIDATE REDIRECTION LOGIC BASED ON PHONE VERIFICATION
function handle_candidate_job_offer_redirect() {
    // ? SKIP IF ALREADY ON JOB OFFER PAGE
    if (window.location.pathname.includes('/app/job-offer/')) return;

    // ? CHECK IF CACHED JOB OFFER ID EXISTS
    const cached_offer_id = sessionStorage.getItem("job_offer_id");
    if (cached_offer_id) {
        const route = `/app/job-offer/${cached_offer_id}`;
        console.log("🔁 Redirecting to cached Job Offer:", route);
        window.location.href = route;
        return;
    }

    // ? SHOW PHONE VERIFICATION DIALOG
    const dialog = new frappe.ui.Dialog({
        title: '🔒 Verify Your Identity',
        fields: [
            {
                label: '📞 Enter your phone number',
                fieldname: 'phone',
                fieldtype: 'Data',
                reqd: true
            }
        ],
        primary_action_label: 'Verify',
        primary_action(values) {
            const entered_phone = values.phone.trim();

            // ? FIND JOB APPLICANT USING PHONE NUMBER
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Job Applicant",
                    filters: {
                        phone_number: entered_phone
                    },
                    fields: ["name"]
                },
                callback: function (res) {
                    if (!res.message || res.message.length === 0) {
                        frappe.msgprint("❌ Phone number not found.");
                        return;
                    }

                    const job_applicant = res.message[0].name;

                    // ? GET JOB OFFER LINKED TO JOB APPLICANT
                    frappe.call({
                        method: "frappe.client.get_list",
                        args: {
                            doctype: "Job Offer",
                            filters: {
                                job_applicant: job_applicant
                            },
                            fields: ["name"]
                        },
                        callback: function (r) {
                            if (!r.message || r.message.length === 0) {
                                frappe.msgprint("❌ Job Offer not found.");
                                return;
                            }

                            const job_offer_id = r.message[0].name;

                            // ? STORE JOB OFFER ID IN SESSION STORAGE
                            sessionStorage.setItem("job_offer_id", job_offer_id);
                            sessionStorage.setItem("job_offer_verified", "true");

                            // ? REDIRECT TO JOB OFFER FORM
                            const redirect_url = `/app/job-offer/${job_offer_id}`;
                            console.log("✅ Redirecting to Job Offer:", redirect_url);

                            dialog.hide();
                            window.location.href = redirect_url;
                        }
                    });
                }
            });
        }
    });

    dialog.show();
}

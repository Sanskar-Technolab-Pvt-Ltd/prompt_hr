

$(document).ready(function () {
    // ? CHECK ON INITIAL PAGE LOAD
    redirect_to_proper_page();

    // ? CHECK AGAIN WHENEVER ROUTE CHANGES (E.G., BACK BUTTON OR MANUAL URL EDIT)
    if (frappe.router && frappe.router.on) {
        frappe.router.on('change', () => {
            redirect_to_proper_page();
        });
    }

    // ? CLEAR CACHED INFO ON LOGOUT
    frappe.realtime.on("session_logged_out", () => {
        sessionStorage.removeItem("candidate_profile_id");
        sessionStorage.removeItem("candidate_profile_verified");
    });

    // ? DETECT SESSION STORAGE CHANGES
    add_session_storage_monitoring();
});

// ? MONITOR CHANGES TO SESSION STORAGE
function add_session_storage_monitoring() {
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        // ? Store the original values
        const original_candidate_profile_id = sessionStorage.getItem("candidate_profile_id");
        const original_verified = sessionStorage.getItem("candidate_profile_verified");
        
        // ? RECORD THE INITIAL STATE
        if (original_candidate_profile_id) {
            // ? CREATE A SPECIAL FLAG WITH RANDOM VALUE TO DETECT TAMPERING
            const integrity_key = generate_integrity_key();
            sessionStorage.setItem("candidate_profile_integrity", integrity_key);
            
            // ? STORE THE ENCRYPTED VERSION OF THE ORIGINAL Candidate Portal ID
            const secured_id = btoa(original_candidate_profile_id + ":" + integrity_key);
            sessionStorage.setItem("candidate_profile_secure", secured_id);
        }
        
        // ? CHECK PERIODICALLY FOR CHANGES
        setInterval(() => {
            check_session_storage_integrity();
        }, 1000); // ? CHECK EVERY SECOND
    }
}

// ? GENERATE RANDOM INTEGRITY KEY
function generate_integrity_key() {
    return Math.random().toString(36).substring(2, 15);
}

// ? CHECK IF SESSION STORAGE HAS BEEN TAMPERED WITH
function check_session_storage_integrity() {
    const current_candidate_profile_id = sessionStorage.getItem("candidate_profile_id");
    const integrity_key = sessionStorage.getItem("candidate_profile_integrity");
    const secured_id = sessionStorage.getItem("candidate_profile_secure");
    
    // ? IF WE HAVE BOTH AN ID AND A SECURED VERSION
    if (current_candidate_profile_id && integrity_key && secured_id) {
        try {
            // ? DECODE THE SECURED ID
            const decoded = atob(secured_id);
            const [original_id, original_key] = decoded.split(":");
            
            // ? CHECK IF THE CURRENT ID MATCHES THE ORIGINAL OR IF THE INTEGRITY KEY HAS BEEN CHANGED
            if (current_candidate_profile_id !== original_id || integrity_key !== original_key) {
                console.log("🚨 Session storage tampering detected!");
                
                // ? CLEAR ALL STORAGE
                sessionStorage.removeItem("candidate_profile_id");
                sessionStorage.removeItem("candidate_profile_verified");
                sessionStorage.removeItem("candidate_profile_integrity");
                sessionStorage.removeItem("candidate_profile_secure");
                
                // ? FORCE REVERIFICATION
                show_verification_dialog();
            }
        } catch (e) {
            // ? IF THERE'S ANY ERROR IN DECODING (TAMPERING), ALSO FORCE REVERIFICATION
            console.log("🚨 Session storage format error detected!");
            sessionStorage.clear();
            show_verification_dialog();
        }
    } else if (current_candidate_profile_id && (!integrity_key || !secured_id)) {
        // ? IF WE HAVE AN ID BUT MISSING SECURITY TOKENS, THAT'S SUSPICIOUS
        console.log("🚨 Missing security tokens!");
        sessionStorage.clear();
        show_verification_dialog();
    }
}

// ? COMBINED REDIRECTION HANDLER FOR EMPLOYEE & CANDIDATE
function redirect_to_proper_page() {
    // ? SKIP FOR GUEST USERS
    if (frappe.session.user === 'Guest') return;

    // ? CHECK IF GENERIC CANDIDATE USER
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        handle_candidate_profile_redirect();
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
function handle_candidate_profile_redirect() {
    const cached_profile_id = sessionStorage.getItem("candidate_profile_id");
    const current_path = window.location.pathname;
    
    // ? IF NOT ON Candidate Portal PAGE AND ON A PAGE THAT REQUIRES DOCTYPE ACCESS, REDIRECT TO DASHBOARD
    if (!current_path.includes('/app/candidate-portal/') && 
        (current_path.includes('/app/doctype/') || 
         current_path.includes('/app/list/') || 
         current_path.includes('/app/form/'))) {
        
        // ? REDIRECT TO A SAFE LANDING PAGE
        if (cached_profile_id) {
            window.location.href = `/app/candidate-portal/${cached_profile_id}`;
        } else {
            // ? IF NO VERIFIED PROFILE YET, SHOW VERIFICATION DIALOG ON DASHBOARD
            window.location.href = "/app/dashboard";
            // ? We'll redirect after verification in the show_verification_dialog function
            setTimeout(() => show_verification_dialog(), 1000);
            return;
        }
    }
    
    // ? EXTRACT THE Candidate Portal ID FROM THE URL IF ON candidate-portal PAGE
    let url_candidate_profile_id = null;
    const candidate_profile_match = current_path.match(/\/app\/candidate-portal\/([\w-]+)/);
    if (candidate_profile_match && candidate_profile_match[1]) {
        url_candidate_profile_id = candidate_profile_match[1];
    }

    // ? IF CACHED PROFILE EXISTS, VERIFY IT'S STILL VALID
    if (cached_profile_id) {
        // ? Always verify the cached ID is still valid, in case session storage was manipulated
        verify_candidate_access_to_profile(cached_profile_id, url_candidate_profile_id || cached_profile_id);
        return;
    }

    // ? IF NOT VERIFIED, PROMPT PHONE VERIFICATION
    show_verification_dialog();
}

// ? VERIFY CANDIDATE HAS ACCESS TO THE Candidate Portal
function verify_candidate_access_to_profile(cached_profile_id, requested_profile_id) {
    // ? Use server method that bypasses permission checks to get profile info
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Candidate Portal",
            filters: { name: cached_profile_id },
            fieldname: ["applicant_email", "phone_number", "job_offer"]
        },
        callback: function(profile_result) {
            if (!profile_result.message || !profile_result.message.phone_number) {
                // ? CACHED PROFILE DOESN'T EXIST OR MISSING PHONE, REVALIDATE
                console.log("🔄 Cached Candidate Portal invalid. Re-verifying...");
                sessionStorage.removeItem("candidate_profile_id");
                sessionStorage.removeItem("candidate_profile_verified");
                show_verification_dialog();
                return;
            }
            
            const verified_email = profile_result.message.applicant_email;
            const verified_phone = profile_result.message.phone_number;
            
            // ? IF THEY'RE TRYING TO ACCESS A DIFFERENT PROFILE THAN CACHED
            if (requested_profile_id !== cached_profile_id) {
                validate_candidate_profile_access(requested_profile_id, cached_profile_id, verified_email, verified_phone);
                return;
            }
            
            // ? OTHERWISE, CONTINUE WITH VERIFIED PROFILE
            const correct_path = `/app/candidate-portal/${cached_profile_id}`;
            if (!window.location.pathname.includes(correct_path)) {
                console.log("🚫 Invalid Candidate Portal access. Redirecting to:", correct_path);
                window.location.href = correct_path;
            }
        }
    });
}

// ? VALIDATE IF USER CAN ACCESS A SPECIFIC Candidate Portal
function validate_candidate_profile_access(requested_profile_id, default_profile_id, verified_email, verified_phone) {
    // ? Use server method that bypasses permission checks
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Candidate Portal",
            filters: { name: requested_profile_id },
            fieldname: ["applicant_email", "phone_number"]
        },
        callback: function(r) {
            if (!r.message) {
                // ? Candidate Portal DOESN'T EXIST, REDIRECT TO DEFAULT
                console.log("🚫 Candidate Portal not found. Redirecting to authorized profile.");
                window.location.href = `/app/candidate-portal/${default_profile_id}`;
                return;
            }
            
            const requested_email = r.message.applicant_email;
            const requested_phone = r.message.phone_number;
            
            // ? COMPARE EMAIL AND PHONE TO ENSURE THEY'RE FOR THE SAME PERSON
            if (requested_email !== verified_email || requested_phone !== verified_phone) {
                // ? NOT AUTHORIZED TO ACCESS THIS Candidate Portal
                console.log("🚫 Unauthorized Candidate Portal access attempt. Redirecting to authorized profile.");
                window.location.href = `/app/candidate-portal/${default_profile_id}`;
            }
            // ? IF THEY MATCH, ALLOW ACCESS TO THE REQUESTED Candidate Portal
            else {
                // ? UPDATE CACHED Candidate Portal TO THE NEW VALID ONE
                console.log("✅ Authorized access to different Candidate Portal. Updating cache.");
                // ? UPDATE BOTH THE Candidate Portal ID AND ITS SECURE COPY
                sessionStorage.setItem("candidate_profile_id", requested_profile_id);
                
                // ? UPDATE THE INTEGRITY KEY AND SECURE STORAGE
                const integrity_key = generate_integrity_key();
                sessionStorage.setItem("candidate_profile_integrity", integrity_key);
                const secured_id = btoa(requested_profile_id + ":" + integrity_key);
                sessionStorage.setItem("candidate_profile_secure", secured_id);
            }
        }
    });
}

// ? SHOW PHONE VERIFICATION DIALOG TO CANDIDATE
function show_verification_dialog() {
    // ? CHECK IF DIALOG IS ALREADY OPEN TO PREVENT MULTIPLE DIALOGS
    if (window.verification_dialog_active) return;
    
    window.verification_dialog_active = true;
    
    const dialog = new frappe.ui.Dialog({
        title: '🔒 Verify Your Identity',
        fields: [
            {
                label: '📞 Enter your phone number',
                fieldtype: 'Data',
                fieldname: 'phone',
                reqd: true
            }
        ],
        primary_action_label: 'Verify',
        primary_action(values) {
            const entered_phone = values.phone.trim();

            // ? Use a server method that bypasses permission checks
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Candidate Portal",
                    filters: {
                        phone_number: entered_phone
                    },
                    fields: ["name", "applicant_email", "job_offer"]
                },
                callback: function (res) {
                    if (!res.message || res.message.length === 0) {
                        frappe.msgprint({
                            title: 'Verification Failed',
                            indicator: 'red',
                            message: '❌ Phone number not found. Please check and try again.'
                        });
                        return;
                    }

                    const candidate_profile_id = res.message[0].name;

                    // ? STORE Candidate Portal ID IN SESSION STORAGE WITH SECURITY
                    sessionStorage.setItem("candidate_profile_id", candidate_profile_id);
                    sessionStorage.setItem("candidate_profile_verified", "true");
                    
                    // ? SET UP INTEGRITY CHECK
                    const integrity_key = generate_integrity_key();
                    sessionStorage.setItem("candidate_profile_integrity", integrity_key);
                    const secured_id = btoa(candidate_profile_id + ":" + integrity_key);
                    sessionStorage.setItem("candidate_profile_secure", secured_id);

                    // ? REDIRECT TO Candidate Portal FORM
                    const redirect_url = `/app/candidate-portal/${candidate_profile_id}`;
                    console.log("✅ Redirecting to Candidate Portal:", redirect_url);

                    dialog.hide();
                    window.verification_dialog_active = false;
                    
                    // ? Show success message before redirecting
                    frappe.show_alert({
                        message: '✅ Verification successful! Redirecting...',
                        indicator: 'green'
                    }, 2);
                    
                    setTimeout(() => {
                        window.location.href = redirect_url;
                    }, 1000);
                }
            });
        },
        onhide: function() {
            window.verification_dialog_active = false;
        }
    });

    dialog.show();
}

// ? CUSTOM SERVER CALL TO CHECK PROFILE ACCESS
// ? THIS FUNCTION WILL BE USED IN CASE WE NEED A CUSTOM API ENDPOINT
function check_profile_access(profile_id, callback) {
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Candidate Portal",
            filters: { name: profile_id },
            fieldname: ["applicant_email", "phone_number", "job_offer"]
        },
        callback: function(r) {
            if (callback && typeof callback === 'function') {
                callback(r);
            }
        }
    });
}

// ? MONKEY-PATCH SESSIONSTORAGE TO DETECT CHANGES
// ? THIS WORKS EVEN WITH DIRECT CONSOLE ACCESS
(function() {
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        const originalSetItem = sessionStorage.setItem;
        
        sessionStorage.setItem = function(key, value) {
            // ? CALL THE ORIGINAL FUNCTION
            originalSetItem.apply(this, arguments);
            
            // ? IF THE KEY IS CANDIDATE_PROFILE_ID AND WE ALREADY HAVE SESSION STORAGE MONITORING
            if (key === "candidate_profile_id" && sessionStorage.getItem("candidate_profile_integrity")) {
                // ? CHECK IF THIS IS A LEGITIMATE CHANGE FROM OUR CODE
                const integrity_key = sessionStorage.getItem("candidate_profile_integrity");
                const secured_id = sessionStorage.getItem("candidate_profile_secure");
                
                if (secured_id) {
                    try {
                        const decoded = atob(secured_id);
                        const [original_id, original_key] = decoded.split(":");
                        
                        // ? IF THIS IS NOT A LEGITIMATE CHANGE (NOT FROM OUR CODE)
                        if (value !== original_id && original_key === integrity_key) {
                            console.log("🚨 Direct sessionStorage.setItem detected!");
                            
                            // ? NEED TO USE SETTIMEOUT TO AVOID INFINITE LOOP
                            setTimeout(() => {
                                // ? CLEAR ALL STORAGE
                                sessionStorage.removeItem("candidate_profile_id");
                                sessionStorage.removeItem("candidate_profile_verified");
                                sessionStorage.removeItem("candidate_profile_integrity");
                                sessionStorage.removeItem("candidate_profile_secure");
                                
                                // ? FORCE REVERIFICATION
                                show_verification_dialog();
                            }, 0);
                        }
                    } catch (e) {
                        // ? IF THERE'S ANY ERROR, ALSO FORCE REVERIFICATION
                        setTimeout(() => {
                            sessionStorage.clear();
                            show_verification_dialog();
                        }, 0);
                    }
                }
            }
        };
    }
})();

// ? ADD CUSTOM NAVIGATION RESTRICTION TO PREVENT ACCESS TO RESTRICTED DOCTYPES
(function() {
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        // ? INTERCEPT ALL CLICKS 
        $(document).on('click', 'a[href^="/app/"]', function(e) {
            const href = $(this).attr('href');
            
            // ? BLOCK ACCESS TO DOCTYPE, LIST, AND OTHER RESTRICTED PAGES
            if (href.includes('/app/doctype/') || 
                href.includes('/app/list/') || 
                href.includes('/app/report/') ||
                href.includes('/app/form/') ||
                href.includes('/app/user/') ||
                href.includes('/app/setup/')) {
                
                e.preventDefault();
                e.stopPropagation();
                
                // ? CHECK IF WE HAVE A VERIFIED PROFILE
                const cached_profile_id = sessionStorage.getItem("candidate_profile_id");
                if (cached_profile_id) {
                    // ? REDIRECT TO Candidate Portal
                    window.location.href = `/app/candidate-portal/${cached_profile_id}`;
                } else {
                    // ? SHOW VERIFICATION DIALOG
                    show_verification_dialog();
                }
                
                return false;
            }
            
            // ? ALLOW LINKS TO Candidate Portal
            if (href.includes('/app/candidate-portal/')) {
                const profile_id = href.split('/app/candidate-portal/')[1];
                const cached_profile_id = sessionStorage.getItem("candidate_profile_id");
                
                // ? IF WE HAVE A CACHED PROFILE, VALIDATE THIS REQUEST
                if (cached_profile_id && profile_id !== cached_profile_id) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // ? VERIFY ACCESS TO THE REQUESTED PROFILE
                    verify_candidate_access_to_profile(cached_profile_id, profile_id);
                    return false;
                }
            }
        });
    }
})();
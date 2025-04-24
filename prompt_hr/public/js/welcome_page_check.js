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
        clear_portal_session_data();
    });
    
    // ? DETECT SESSION STORAGE CHANGES
    add_session_storage_monitoring();
    
    // ? CHECK IF WE NEED TO SHOW VERIFICATION DIALOG AFTER REDIRECT
    if (sessionStorage.getItem("show_verification_pending") === "true" && 
        window.location.pathname === "/app") {
        // Small timeout to ensure everything is loaded
        setTimeout(() => {
            // Remove the flag first to prevent potential loops
            sessionStorage.removeItem("show_verification_pending");
            // Show the dialog
            show_verification_dialog();
        }, 500);
    }
});

// ? CLEAR ALL PORTAL-RELATED SESSION DATA
function clear_portal_session_data() {
    // Clear Candidate Portal data
    sessionStorage.removeItem("candidate_profile_id");
    sessionStorage.removeItem("candidate_profile_verified");
    sessionStorage.removeItem("candidate_profile_integrity");
    sessionStorage.removeItem("candidate_profile_secure");
    
    // Clear LMS Portal data
    sessionStorage.removeItem("lms_portal_id");
    sessionStorage.removeItem("lms_portal_verified");
    sessionStorage.removeItem("lms_portal_integrity");
    sessionStorage.removeItem("lms_portal_secure");
    
    // Clear portal type
    sessionStorage.removeItem("portal_type");
}

// ? MONITOR CHANGES TO SESSION STORAGE
function add_session_storage_monitoring() {
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        // ? Store the original values for both portals
        const portal_type = sessionStorage.getItem("portal_type") || "candidate-portal";
        const storage_key = portal_type.replace('-', '_') + "_id";
        const original_profile_id = sessionStorage.getItem(storage_key);
        
        // ? RECORD THE INITIAL STATE
        if (original_profile_id) {
            // ? CREATE A SPECIAL FLAG WITH RANDOM VALUE TO DETECT TAMPERING
            const integrity_key = generate_integrity_key();
            sessionStorage.setItem(`${portal_type.replace('-', '_')}_integrity`, integrity_key);
            
            // ? STORE THE ENCRYPTED VERSION OF THE ORIGINAL Portal ID
            const secured_id = btoa(original_profile_id + ":" + integrity_key);
            sessionStorage.setItem(`${portal_type.replace('-', '_')}_secure`, secured_id);
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
    const portal_type = sessionStorage.getItem("portal_type") || "candidate-portal";
    const key_prefix = portal_type.replace('-', '_');
    
    const current_profile_id = sessionStorage.getItem(`${key_prefix}_id`);
    const integrity_key = sessionStorage.getItem(`${key_prefix}_integrity`);
    const secured_id = sessionStorage.getItem(`${key_prefix}_secure`);
    
    // ? IF WE HAVE BOTH AN ID AND A SECURED VERSION
    if (current_profile_id && integrity_key && secured_id) {
        try {
            // ? DECODE THE SECURED ID
            const decoded = atob(secured_id);
            const [original_id, original_key] = decoded.split(":");
            
            // ? CHECK IF THE CURRENT ID MATCHES THE ORIGINAL OR IF THE INTEGRITY KEY HAS BEEN CHANGED
            if (current_profile_id !== original_id || integrity_key !== original_key) {
                console.log("🚨 Session storage tampering detected!");
                
                // ? CLEAR ALL STORAGE
                clear_portal_session_data();
                
                // ? REDIRECT TO /app WHEN SESSION STORAGE IS INVALID
                window.location.href = "/app";
                return;
            }
        } catch (e) {
            // ? IF THERE'S ANY ERROR IN DECODING (TAMPERING), REDIRECT TO /app
            console.log("🚨 Session storage format error detected!");
            sessionStorage.clear();
            window.location.href = "/app";
            return;
        }
    } else if (current_profile_id && (!integrity_key || !secured_id)) {
        // ? IF WE HAVE AN ID BUT MISSING SECURITY TOKENS, THAT'S SUSPICIOUS
        console.log("🚨 Missing security tokens!");
        sessionStorage.clear();
        window.location.href = "/app";
        return;
    }
}

// ? COMBINED REDIRECTION HANDLER FOR EMPLOYEE & CANDIDATE
function redirect_to_proper_page() {
    // ? SKIP FOR GUEST USERS
    if (frappe.session.user === 'Guest') return;
    
    // ? CHECK IF GENERIC CANDIDATE USER
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        handle_portal_redirect();
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

// ? PORTAL REDIRECTION LOGIC BASED ON PHONE VERIFICATION
function handle_portal_redirect() {
    const current_path = window.location.pathname;
    const portal_type = sessionStorage.getItem("portal_type") || "candidate-portal";
    const storage_key = portal_type.replace('-', '_') + "_id";
    const cached_profile_id = sessionStorage.getItem(storage_key);
    
    // Check for invalid session storage state
    if (cached_profile_id) {
        const integrity_key = sessionStorage.getItem(`${portal_type.replace('-', '_')}_integrity`);
        const secured_id = sessionStorage.getItem(`${portal_type.replace('-', '_')}_secure`);
        
        if (!integrity_key || !secured_id) {
            console.log("🚨 Incomplete session storage detected during redirection!");
            clear_portal_session_data();
            window.location.href = "/app";
            return;
        }
        
        try {
            const decoded = atob(secured_id);
            const [original_id, original_key] = decoded.split(":");
            
            if (cached_profile_id !== original_id || integrity_key !== original_key) {
                console.log("🚨 Session storage inconsistency detected during redirection!");
                clear_portal_session_data();
                window.location.href = "/app";
                return;
            }
        } catch (e) {
            console.log("🚨 Session storage decode error during redirection!");
            clear_portal_session_data();
            window.location.href = "/app";
            return;
        }
    }
    
    // ? IF NOT ON PORTAL PAGE AND ON A PAGE THAT REQUIRES DOCTYPE ACCESS, REDIRECT TO DASHBOARD
    if (!current_path.includes(`/app/${portal_type}/`) && 
        (current_path.includes('/app/doctype/') || 
         current_path.includes('/app/list/') || 
         current_path.includes('/app/form/'))) {
        
        // ? REDIRECT TO A SAFE LANDING PAGE
        if (cached_profile_id) {
            window.location.href = `/app/${portal_type}/${cached_profile_id}`;
        } else {
            // ? IF NO VERIFIED PROFILE YET, SHOW VERIFICATION DIALOG ON DASHBOARD
            window.location.href = "/app/dashboard";
            // ? We'll redirect after verification in the show_verification_dialog function
            setTimeout(() => show_verification_dialog(), 1000);
            return;
        }
    }
    
    // ? EXTRACT THE PORTAL ID FROM THE URL IF ON PORTAL PAGE
    let url_profile_id = null;
    let url_portal_type = null;
    
    // Check if we're on a portal page
    if (current_path.includes('/app/candidate-portal/')) {
        const match = current_path.match(/\/app\/candidate-portal\/([\w-]+)/);
        if (match && match[1]) {
            url_profile_id = match[1];
            url_portal_type = "candidate-portal";
        }
    } else if (current_path.includes('/app/lms-portal/')) {
        const match = current_path.match(/\/app\/lms-portal\/([\w-]+)/);
        if (match && match[1]) {
            url_profile_id = match[1];
            url_portal_type = "lms-portal";
        }
    }
    
    // ? If we're on a portal page but it's different from the cached one
    if (url_portal_type && url_portal_type !== portal_type) {
        // User is trying to access a different portal type, show verification dialog
        if (!cached_profile_id) {
            show_verification_dialog();
            return;
        }
        
        // If they're accessing a different portal type but we have a cached profile,
        // let's check if they have access to this portal type
        sessionStorage.setItem("portal_type", url_portal_type);
        // We'll handle verification in the verify_portal_access function
    }
    
    // ? IF CACHED PROFILE EXISTS, VERIFY IT'S STILL VALID
    if (cached_profile_id) {
        // ? Always verify the cached ID is still valid, in case session storage was manipulated
        verify_portal_access(cached_profile_id, url_profile_id || cached_profile_id);
        return;
    }
    
    // ? IF NOT VERIFIED, PROMPT PHONE VERIFICATION
    show_verification_dialog();
}

// ? VERIFY USER HAS ACCESS TO THE PORTAL
function verify_portal_access(cached_profile_id, requested_profile_id) {
    const portal_type = sessionStorage.getItem("portal_type") || "candidate-portal";
    const doctype = portal_type === "candidate-portal" ? "Candidate Portal" : "LMS Portal";
    
    // ? Use server method that bypasses permission checks to get profile info
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: doctype,
            filters: { name: cached_profile_id },
            fieldname: ["applicant_email", "phone_number", "job_offer"]
        },
        callback: function(profile_result) {
            if (!profile_result.message || !profile_result.message.phone_number) {
                // ? CACHED PROFILE DOESN'T EXIST OR MISSING PHONE, REVALIDATE
                console.log(`🔄 Cached ${doctype} invalid. Re-verifying...`);
                clear_portal_session_data();
                window.location.href = "/app"; // Redirect to /app on invalid session
                return;
            }
            
            const verified_email = profile_result.message.applicant_email;
            const verified_phone = profile_result.message.phone_number;
            
            // ? IF THEY'RE TRYING TO ACCESS A DIFFERENT PROFILE THAN CACHED
            if (requested_profile_id !== cached_profile_id) {
                validate_profile_access(requested_profile_id, cached_profile_id, verified_email, verified_phone);
                return;
            }
            
            // ? OTHERWISE, CONTINUE WITH VERIFIED PROFILE
            const correct_path = `/app/${portal_type}/${cached_profile_id}`;
            if (!window.location.pathname.includes(correct_path)) {
                console.log(`🚫 Invalid ${doctype} access. Redirecting to:`, correct_path);
                window.location.href = correct_path;
            }
        }
    });
}

// ? VALIDATE IF USER CAN ACCESS A SPECIFIC PROFILE
function validate_profile_access(requested_profile_id, default_profile_id, verified_email, verified_phone) {
    const portal_type = sessionStorage.getItem("portal_type") || "candidate-portal";
    const doctype = portal_type === "candidate-portal" ? "Candidate Portal" : "LMS Portal";
    
    // ? Use server method that bypasses permission checks
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: doctype,
            filters: { name: requested_profile_id },
            fieldname: ["applicant_email", "phone_number"]
        },
        callback: function(r) {
            if (!r.message) {
                // ? PROFILE DOESN'T EXIST, REDIRECT TO DEFAULT
                console.log(`🚫 ${doctype} not found. Redirecting to authorized profile.`);
                window.location.href = `/app/${portal_type}/${default_profile_id}`;
                return;
            }
            
            const requested_email = r.message.applicant_email;
            const requested_phone = r.message.phone_number;
            
            // ? COMPARE EMAIL AND PHONE TO ENSURE THEY'RE FOR THE SAME PERSON
            if (requested_email !== verified_email || requested_phone !== verified_phone) {
                // ? NOT AUTHORIZED TO ACCESS THIS PROFILE
                console.log(`🚫 Unauthorized ${doctype} access attempt. Redirecting to authorized profile.`);
                window.location.href = `/app/${portal_type}/${default_profile_id}`;
            }
            // ? IF THEY MATCH, ALLOW ACCESS TO THE REQUESTED PROFILE
            else {
                // ? UPDATE CACHED PROFILE TO THE NEW VALID ONE
                console.log(`✅ Authorized access to different ${doctype}. Updating cache.`);
                const key_prefix = portal_type.replace('-', '_');
                
                // ? UPDATE BOTH THE PROFILE ID AND ITS SECURE COPY
                sessionStorage.setItem(`${key_prefix}_id`, requested_profile_id);
                
                // ? UPDATE THE INTEGRITY KEY AND SECURE STORAGE
                const integrity_key = generate_integrity_key();
                sessionStorage.setItem(`${key_prefix}_integrity`, integrity_key);
                const secured_id = btoa(requested_profile_id + ":" + integrity_key);
                sessionStorage.setItem(`${key_prefix}_secure`, secured_id);
            }
        }
    });
}

// ? SHOW PHONE VERIFICATION DIALOG WITH PORTAL SELECTION
function show_verification_dialog() {
    // ? CHECK IF DIALOG IS ALREADY OPEN TO PREVENT MULTIPLE DIALOGS
    if (window.verification_dialog_active) return;
    
    window.verification_dialog_active = true;
    
    // Only redirect if we're not already on /app
    if (!window.location.pathname.startsWith('/app') || window.location.pathname !== '/app') {
        window.location.href = "/app";
        
        // Set a flag in sessionStorage to indicate we need to show the dialog
        // after the redirect completes
        sessionStorage.setItem("show_verification_pending", "true");
        return; // Exit the function - dialog will be shown after redirect
    }
    
    const dialog = new frappe.ui.Dialog({
        title: '🔒 Verify Your Identity',
        fields: [
            {
                label: '🔄 Select Portal',
                fieldtype: 'Select',
                fieldname: 'portal_type',
                options: 'Candidate Portal\nLMS Portal',
                default: 'Candidate Portal',
                reqd: true
            },
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
            const selected_portal = values.portal_type;
            
            // Determine which doctype to query based on selection
            const doctype = selected_portal === 'Candidate Portal' ? 'Candidate Portal' : 'LMS Portal';
            const portal_route = selected_portal === 'Candidate Portal' ? 'candidate-portal' : 'lms-portal';
            
            // ? Use a server method that bypasses permission checks
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: doctype,
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
                            message: `❌ Phone number not found in ${selected_portal}. Please check and try again.`
                        });
                        return;
                    }
                    
                    const profile_id = res.message[0].name;
                    const key_prefix = portal_route.replace('-', '_');
                    
                    // ? STORE PROFILE ID IN SESSION STORAGE WITH SECURITY
                    sessionStorage.setItem(`${key_prefix}_id`, profile_id);
                    sessionStorage.setItem(`${key_prefix}_verified`, "true");
                    sessionStorage.setItem("portal_type", portal_route);
                    
                    // ? SET UP INTEGRITY CHECK
                    const integrity_key = generate_integrity_key();
                    sessionStorage.setItem(`${key_prefix}_integrity`, integrity_key);
                    const secured_id = btoa(profile_id + ":" + integrity_key);
                    sessionStorage.setItem(`${key_prefix}_secure`, secured_id);
                    
                    // Remove the pending verification flag
                    sessionStorage.removeItem("show_verification_pending");
                    
                    // ? REDIRECT TO APPROPRIATE PORTAL FORM
                    const redirect_url = `/app/${portal_route}/${profile_id}`;
                    console.log(`✅ Redirecting to ${selected_portal}:`, redirect_url);
                    
                    dialog.hide();
                    window.verification_dialog_active = false;
                    
                    // ? Show success message before redirecting
                    frappe.show_alert({
                        message: `✅ Verification successful! Redirecting to ${selected_portal}...`,
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
    const portal_type = sessionStorage.getItem("portal_type") || "candidate-portal";
    const doctype = portal_type === "candidate-portal" ? "Candidate Portal" : "LMS Portal";
    
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: doctype,
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
            
            // Check if this is a profile ID key for either portal
            if ((key === "candidate_profile_id" || key === "lms_portal_id")) {
                const portal_type = key === "candidate_profile_id" ? "candidate-portal" : "lms-portal";
                const key_prefix = portal_type.replace('-', '_');
                
                // ? CHECK IF THIS IS A LEGITIMATE CHANGE FROM OUR CODE
                const integrity_key = sessionStorage.getItem(`${key_prefix}_integrity`);
                const secured_id = sessionStorage.getItem(`${key_prefix}_secure`);
                
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
                                clear_portal_session_data();
                                
                                // ? REDIRECT TO /app ON INVALID SESSION
                                window.location.href = "/app";
                            }, 0);
                        }
                    } catch (e) {
                        // ? IF THERE'S ANY ERROR, ALSO FORCE REDIRECTION TO /app
                        setTimeout(() => {
                            sessionStorage.clear();
                            window.location.href = "/app";
                        }, 0);
                    }
                }
            }
        };
        
        // Also intercept and check removal of items
        const originalRemoveItem = sessionStorage.removeItem;
        
        sessionStorage.removeItem = function(key) {
            // Check if this is a security-related key
            if (key.includes('_integrity') || key.includes('_secure')) {
                const key_parts = key.split('_');
                const portal_prefix = key_parts[0] + '_' + key_parts[1];
                const profile_id = sessionStorage.getItem(`${portal_prefix}_id`);
                
                // If we have a profile ID but someone is trying to remove security keys
                if (profile_id) {
                    console.log("🚨 Attempt to remove security key detected!");
                    
                    setTimeout(() => {
                        // Clear all and redirect to /app
                        sessionStorage.clear();
                        window.location.href = "/app";
                    }, 0);
                    
                    // Don't actually remove the item yet
                    return;
                }
            }
            
            // ? CALL THE ORIGINAL FUNCTION FOR LEGITIMATE REMOVALS
            originalRemoveItem.apply(this, arguments);
        };
    }
})();

// ? ADD CUSTOM NAVIGATION RESTRICTION TO PREVENT ACCESS TO RESTRICTED DOCTYPES
(function() {
    if (frappe.session.user === "candidate@sanskartechnolab.com") {
        // ? INTERCEPT ALL CLICKS 
        $(document).on('click', 'a[href^="/app/"]', function(e) {
            const href = $(this).attr('href');
            const portal_type = sessionStorage.getItem("portal_type") || "candidate-portal";
            const key_prefix = portal_type.replace('-', '_');
            const cached_profile_id = sessionStorage.getItem(`${key_prefix}_id`);
            
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
                if (cached_profile_id) {
                    // ? VERIFY INTEGRITY BEFORE REDIRECTING
                    const integrity_key = sessionStorage.getItem(`${key_prefix}_integrity`);
                    const secured_id = sessionStorage.getItem(`${key_prefix}_secure`);
                    
                    if (!integrity_key || !secured_id) {
                        // ? MISSING SECURITY TOKENS, REDIRECT TO /APP
                        sessionStorage.clear();
                        window.location.href = "/app";
                        return false;
                    }
                    
                    try {
                        const decoded = atob(secured_id);
                        const [original_id, original_key] = decoded.split(":");
                        
                        if (cached_profile_id !== original_id || integrity_key !== original_key) {
                            // ? SESSION TAMPERED WITH, REDIRECT TO /APP
                            sessionStorage.clear();
                            window.location.href = "/app";
                            return false;
                        }
                        
                        // ? REDIRECT TO APPROPRIATE PORTAL
                        window.location.href = `/app/${portal_type}/${cached_profile_id}`;
                    } catch (e) {
                        // ? ERROR IN DECODING, REDIRECT TO /APP
                        sessionStorage.clear();
                        window.location.href = "/app";
                        return false;
                    }
                } else {
                    // ? SHOW VERIFICATION DIALOG
                    show_verification_dialog();
                }
                
                return false;
            }
            
            // ? CHECK ACCESS TO EITHER PORTAL TYPE
            if (href.includes('/app/candidate-portal/') || href.includes('/app/lms-portal/')) {
                const clicked_portal_type = href.includes('/app/candidate-portal/') ? 
                    "candidate-portal" : "lms-portal";
                
                // ? EXTRACT THE PROFILE ID FROM THE URL
                const pattern = new RegExp(`/app/${clicked_portal_type}/([\\w-]+)`);
                const match = href.match(pattern);
                
                if (match && match[1]) {
                    const profile_id = match[1];
                    
                    // ? IF TRYING TO ACCESS A DIFFERENT PORTAL TYPE THAN CACHED
                    if (clicked_portal_type !== portal_type) {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        // ? NEED TO VERIFY WITH THE APPROPRIATE PORTAL TYPE
                        sessionStorage.setItem("portal_type", clicked_portal_type);
                        
                        // ? IF WE HAVE A CACHED PROFILE FOR THE CURRENT TYPE, CHECK IF SAME USER
                        if (cached_profile_id) {
                            verify_portal_access(cached_profile_id, profile_id);
                        } else {
                            // ? OTHERWISE SHOW VERIFICATION DIALOG
                            show_verification_dialog();
                        }
                        return false;
                    }
                    
                    // ? IF TRYING TO ACCESS SAME PORTAL TYPE BUT DIFFERENT PROFILE
                    if (cached_profile_id && profile_id !== cached_profile_id) {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        // ? VERIFY ACCESS TO THE REQUESTED PROFILE
                        verify_portal_access(cached_profile_id, profile_id);
                        return false;
                    }
                }
            }
        });
    }
})();
// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reporting Manager Checklist", {
    refresh(frm) {
        // ? APPLY ROLE-BASED FIELD VISIBILITY
        set_field_config_based_on_user_role(frm);

        // ? MAKE GENERAL FIELDS READ-ONLY IF USER HAS SPECIFIC ROLES
        make_general_fields_read_only(frm);
    },
});

// ? FUNCTION TO SET GENERAL FIELDS AS READ-ONLY IF USER HAS ANY SPECIFIC ROLE
function make_general_fields_read_only(frm) {
    const roles_to_check = ["Reporting Manager", "IT User", "Admin User"];
    const general_fields = [
        "applicant_name",
        "employment_type",
        "designation",
        "work_location",
        "department",
        "company"
    ];

    const has_specific_role = roles_to_check.some(role => frappe.user.has_role(role));

    if (has_specific_role) {
        general_fields.forEach(field => {
            if (frm.fields_dict[field]) {
                frm.set_df_property(field, "read_only", 1);
            }
        });
        console.log("Set general fields as read-only for role-based user");
    }
}

// ? MAIN FUNCTION TO APPLY FIELD RULES BASED ON USER ROLE
function set_field_config_based_on_user_role(frm) {
    if (frappe.user.has_role("Reporting Manager")) {
        set_reporting_manager_field_config(frm);
    } 
    else if (frappe.user.has_role("IT User")) {
        set_it_user_field_config(frm);
    }
    else if (frappe.user.has_role("Admin User")) {
        set_admin_user_field_config(frm);
    }
    else {
        console.log("User does not have any of the specified roles");
    }
}

// ? FUNCTION TO APPLY FIELD CONFIG FOR REPORTING MANAGER
function set_reporting_manager_field_config(frm) {
    const fields_to_hide = ["cug", "visiting_cards", "special_requirements"];
    const fields_to_read_only = [
        // "system_allocation", "create_company_email_id", "system_configuration", "company_email", 
        // "chat_software_access", "sitting_arrangements", "bts_project_name", "buddy_name","company_mobile_no"
    ];

    // Hide specific fields
    fields_to_hide.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 1);
        }
    });

    // Make remaining fields read-only
    fields_to_read_only.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 0);
            frm.set_df_property(field, "read_only", 1);
        }
    });

    console.log("Applied Reporting Manager field configuration");
}

// ? FUNCTION TO APPLY FIELD CONFIG FOR IT USER
function set_it_user_field_config(frm) {
    const fields_to_hide = [
        "crm_access_required", "stock_requirement",
        "cug", "special_requirements", "visiting_cards"
    ];

    const read_only_fields = [
        "git_project_access_required", "engineer_dongle", "git_project_name", 
        "assign_erp_role", "erp_module_access", "crm_division", "crm_project","crm_module", "stock_requirement", "crm_access_required"
    ];

    fields_to_hide.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 1);
        }
    });

    read_only_fields.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 0);
            frm.set_df_property(field, "read_only", 1);
        }
    });

    if (frm.fields_dict["company_mobile_no"]) {
        frm.set_df_property("company_mobile_no", "hidden", 0);
        frm.set_df_property("company_mobile_no", "read_only", 0);
    }

    console.log("Applied IT User field configuration");
}

// ? FUNCTION TO APPLY FIELD CONFIG FOR ADMIN USER
function set_admin_user_field_config(frm) {
    const fields_to_hide = [
        "crm_access_required","crm_division","crm_project","crm_module", "stock_requirement", "company_mobile_no", "git_project_access_required", 
        "engineer_dongle", "assign_erp_role", "erp_module_access", "system_allocation", 
        "create_company_email_id", "system_configuration", "company_email", "chat_software_access", 
        "sitting_arrangements", "bts_project_name", "buddy_name"
    ];

    fields_to_hide.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 1);
        }
    });

    console.log("Applied Admin User field configuration");
}

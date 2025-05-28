// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reporting Manager Checklist", {
    refresh(frm) {
        set_field_config_based_on_user_role(frm);
    },
});

// Main function to determine user role and apply appropriate field configuration
function set_field_config_based_on_user_role(frm) {
    // Get current user
    const current_user = frappe.session.user;

    
    
    // Check user roles and apply appropriate field configuration
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
        // Default behavior - you can choose to show all fields or apply a default configuration
        console.log("User does not have any of the specified roles");
        // Optionally apply a default configuration or show all fields
    }
}

function set_reporting_manager_field_config(frm) {
    const FIELDS_TO_HIDE = [
        "system_allocation", "create_company_email_id", "system_configuration", "company_email", 
        "chat_software_access", "sitting_arrangements", "bts_project_name", "buddy_name", 
        "cug", "special_requirements", "visiting_cards"
    ];

    FIELDS_TO_HIDE.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 1);
        }
    });
    
    console.log("Applied Reporting Manager field configuration");
}

function set_it_user_field_config(frm) {
    const FIELDS_TO_HIDE = [
        "crm_access_required", "stock_requirement", "company_mobile_no", "git_project_access_required", 
        "engineer_dongle", "assign_erp_role", "erp_module_access", "cug", "special_requirements", 
        "visiting_cards"
    ];

    FIELDS_TO_HIDE.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 1);
        }
    });
    
    console.log("Applied IT User field configuration");
}

function set_admin_user_field_config(frm) {
    const FIELDS_TO_HIDE = [
        "crm_access_required", "stock_requirement", "company_mobile_no", "git_project_access_required", 
        "engineer_dongle", "assign_erp_role", "erp_module_access", "system_allocation", 
        "create_company_email_id", "system_configuration", "company_email", "chat_software_access", 
        "sitting_arrangements", "bts_project_name", "buddy_name"
    ];

    FIELDS_TO_HIDE.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 1);
        }
    });
    
    console.log("Applied Admin User field configuration");
}

// Alternative approach using role hierarchy (if you want to apply multiple configurations)
function set_field_config_with_role_hierarchy(frm) {
    // Apply configurations in order of precedence (most specific to least specific)
    if (frappe.user.has_role("Admin User")) {
        set_admin_user_field_config(frm);
    }
    else if (frappe.user.has_role("IT User")) {
        set_it_user_field_config(frm);
    }
    else if (frappe.user.has_role("Reporting Manager")) {
        set_reporting_manager_field_config(frm);
    }
}

// Alternative approach for checking multiple roles and applying combined configurations
function set_field_config_multiple_roles(frm) {
    let fieldsToHide = [];
    
    if (frappe.user.has_role("Reporting Manager")) {
        fieldsToHide = fieldsToHide.concat([
            "system_allocation", "create_company_email_id", "system_configuration", "company_email", 
            "chat_software_access", "sitting_arrangements", "bts_project_name", "buddy_name", 
            "cug", "special_requirements", "visiting_cards"
        ]);
    }
    
    if (frappe.user.has_role("IT User")) {
        fieldsToHide = fieldsToHide.concat([
            "crm_access_required", "stock_requirement", "company_mobile_no", "git_project_access_required", 
            "engineer_dongle", "assign_erp_role", "erp_module_access"
        ]);
    }
    
    if (frappe.user.has_role("Admin User")) {
        fieldsToHide = fieldsToHide.concat([
            "crm_access_required", "stock_requirement", "company_mobile_no", "git_project_access_required", 
            "engineer_dongle", "assign_erp_role", "erp_module_access", "system_allocation", 
            "create_company_email_id", "system_configuration", "company_email", "chat_software_access", 
            "sitting_arrangements", "bts_project_name", "buddy_name"
        ]);
    }
    
    // Remove duplicates and apply
    const uniqueFieldsToHide = [...new Set(fieldsToHide)];
    
    uniqueFieldsToHide.forEach(field => {
        if (frm.fields_dict[field]) {
            frm.set_df_property(field, "hidden", 1);
        }
    });
}
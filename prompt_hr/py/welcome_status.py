
import frappe
import traceback

# ? FUNCTION TO CREATE WELCOME PAGE RECORD FOR NEW USERS
def create_welcome_status(doc):
    try:
        # ? CHECK IF RECORD ALREADY EXISTS
        if frappe.db.exists("Welcome Page", {"user": doc.name}):
            frappe.log_error(
                title="Welcome Page Already Exists",
                message=f"Welcome Page for user {doc.name} already exists. Skipping creation."
            )
            return

        # ? CREATE NEW WELCOME PAGE RECORD
        welcome_status = frappe.new_doc("Welcome Page")
        welcome_status.user = doc.name
        welcome_status.is_completed = 0
        welcome_status.insert(ignore_permissions=True)

        # ? SHARE WELCOME PAGE WITH USER
        frappe.share.add(
            doctype="Welcome Page",
            name=welcome_status.name,
            user=doc.name,
            read=1,
            write=1,
            share=0
        )

        frappe.db.commit()

        frappe.log_error(
            title="Welcome Page Creation",
            message=f"Welcome Page created and shared with user {doc.name}."
        )

    except Exception as e:
        frappe.log_error(
            title="Welcome Page Creation Error",
            message=f"Error creating Welcome Page for user {doc.name}: {str(e)}\n{traceback.format_exc()}"
        )

def after_insert(doc,method):
    # ? CREATE WELCOME PAGE RECORD FOR NEW USERS
    create_welcome_status(doc)


    import frappe

def check_field_permission(doctype, fieldname, role):
    """
    Check if a specific role has read access to a field in a DocType
    
    Args:
        doctype (str): The DocType name (e.g., "Employee")
        fieldname (str): The field name to check
        role (str): The role name to check permissions for
        
    Returns:
        bool: True if the role has read access to the field, False otherwise
    """
    # First check if the field exists in the DocType
    if not frappe.get_meta(doctype).get_field(fieldname):
        frappe.msgprint(f"Field '{fieldname}' does not exist in DocType '{doctype}'")
        return False
    
    # Get all DocPerm records for this DocType
    docperms = frappe.get_all(
        "DocPerm", 
        filters={
            "parent": doctype,
            "role": role,
            "read": 1,  # Only get permissions where read=1
            "permlevel": [">=", 0]  # Get all permission levels
        },
        fields=["permlevel", "read", "if_owner"]
    )
    
    # If no DocPerm records with read=1, role doesn't have read access
    if not docperms:
        return False
    
    # Get field's permlevel
    field_permlevel = frappe.get_value("DocField", 
                                      {"parent": doctype, "fieldname": fieldname}, 
                                      "permlevel") or 0
    
    # Check if role has permission at the field's permlevel
    for perm in docperms:
        if perm.permlevel == field_permlevel:
            return True
    
    return False

# Usage example
def test_field_permissions():
    """Test the field permission function with example data"""
    result = {}
    
    # Test some Employee fields for HR Manager role
    fields_to_check = ["employee_name", "salary", "bank_account_no", "personal_email"]
    role = "HR Manager"
    doctype = "Employee"
    
    for field in fields_to_check:
        has_access = check_field_permission(doctype, field, role)
        result[field] = has_access
        
    return result

# Function to check field permissions for multiple roles
def check_roles_field_permissions(doctype, fieldname, roles):
    """
    Check if multiple roles have read access to a specific field
    
    Args:
        doctype (str): The DocType name
        fieldname (str): The field name to check
        roles (list): List of role names to check
        
    Returns:
        dict: Dictionary mapping role names to access status (True/False)
    """
    result = {}
    
    for role in roles:
        has_access = check_field_permission(doctype, fieldname, role)
        result[role] = has_access
        
    return result

# Example: Check which roles can access salary field
# ! prompt_hr.py.welcome_status.check_salary_field_access
@frappe.whitelist()
def check_salary_field_access():
    roles = ["HR Manager", "HR User", "Employee", "Employee Self Service"]
    return check_roles_field_permissions("Employee", "employee_name", roles)
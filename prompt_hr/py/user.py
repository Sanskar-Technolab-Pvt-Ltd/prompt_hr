
import frappe

def before_save(doc, method=None):
    """ENSURE 'CREATE CHECKIN' ROLE IS SET BASED ON EMPLOYEE'S ATTENDANCE CAPTURE SCHEME."""
    target_role = "Create Checkin"

    # ? FETCH EMPLOYEE ATTENDANCE CAPTURE SCHEME
    attendance_scheme = frappe.db.get_value(
        "Employee", {"user_id": doc.name}, "custom_attendance_capture_scheme"
    )
    if not attendance_scheme:
        return

    # ? EXTRACT CURRENT ROLES FOR QUICK LOOKUP
    current_roles = {r.role for r in doc.roles}

    # ? SCHEMES REQUIRING THE 'CREATE CHECKIN' ROLE
    manual_schemes = {
        "Mobile-Web Checkin-Checkout",
        "Geofencing"
    }

    if attendance_scheme == "Biometric" or attendance_scheme == "Biometric-Mobile Checkin-Checkout":
        # ? REMOVE THE ROLE IF SCHEME IS STRICTLY BIOMETRIC
        doc.roles = [r for r in doc.roles if r.role != target_role]

    elif attendance_scheme in manual_schemes:
        # ? ADD THE ROLE ONLY IF NOT ALREADY PRESENT
        if target_role not in current_roles:
            doc.append("roles", {"role": target_role})
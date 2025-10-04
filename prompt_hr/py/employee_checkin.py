# File: prompt_hr/doctype/employee_checkin/employee_checkin.py
import frappe,math
from frappe import _
from prompt_hr.py.employee import check_if_employee_create_checkin_is_validate_via_web


def before_insert(doc, method):
    """
    ! HOOK: Before insert of Employee Checkin
    ? Logic:
        - Call validation function
        - If returns 0 → Throw message and stop insert
        - If returns 1 → Allow insert
    """

    # ? Get user_id of the current user
    user_id = frappe.session.user

    # ? Call validation function
    is_allowed = check_if_employee_create_checkin_is_validate_via_web(user_id)

    # ? If not allowed, stop the insert
    if is_allowed == 0:
        frappe.throw(_("You are not allowed to create Check-in. "))
    
    get_employee_checkin(doc,method)   


def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/lon points."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@frappe.whitelist()
def get_employee_checkin(doc,method):
    emp = frappe.get_doc("Employee", doc.employee)

    if emp.custom_attendance_capture_scheme == "Geofencing":
        if not (doc.latitude and doc.longitude):
            frappe.throw("Please provide Latitude and Longitude for check-in.")
            
        if not emp.default_shift:
            frappe.throw(f"Please set Default Shift for Employee: {doc.employee}")

        shift_assignment = frappe.get_all(
            "Shift Assignment",
            filters={"employee": doc.employee, "shift_type": emp.default_shift, "status": "Active", "docstatus": 1},
            
        )
        
        if not shift_assignment:
            frappe.throw(f"Please assign Shift Assignment: {emp.default_shift} to Employee: {doc.employee}")

        assignment_doc = frappe.get_doc("Shift Assignment", shift_assignment[0].name)

        if not assignment_doc.shift_location:
            frappe.throw(f"Please set Shift Location for Shift Assignment: {assignment_doc.name}")

        shift_location = frappe.get_doc("Shift Location", assignment_doc.shift_location)

        if not (shift_location.latitude and shift_location.longitude and shift_location.checkin_radius):
            frappe.throw(f"Please set Latitude, Longitude and Check-in Radius for Shift Location: {shift_location.name}")

        # Calculate distance between shift location and employee checkin location
        distance = haversine_distance(
            float(shift_location.latitude),
            float(shift_location.longitude),
            float(doc.latitude),
            float(doc.longitude),
        )
        
        if distance > float(shift_location.checkin_radius):
            frappe.throw(f"You are outside the allowed check-in area ({distance:.2f}m > {shift_location.checkin_radius}m).")

        return {"status": "success", "distance": distance}

    return {"status": "skipped"}

def on_update(doc,method=None):
    share_leave_with_manager(doc)
    
def share_leave_with_manager(leave_doc):
  
    # Get employee linked to this leave
    employee_id = leave_doc.employee
    
    if not employee_id:
        return

    # Get the manager linked in Employee's custom_dotted_line_manager field
    manager_id = frappe.db.get_value("Employee", employee_id, "custom_dotted_line_manager")
    
    if not manager_id:
        return

    # Get the manager's user ID (needed for sharing the document)
    manager_user_id = frappe.db.get_value("Employee", manager_id, "user_id")
    
    if not manager_user_id:
        return

    # Check if the Employee Checkin is already shared with the manager
    existing_share = frappe.db.exists("DocShare", {
        "share_doctype": "Employee Checkin",
        "share_name": leave_doc.name,
        "user": manager_user_id
    })

    if existing_share:
        return

    # Share the Employee Checkin with manager (read-only)
    frappe.share.add_docshare(
        doctype="Employee Checkin",
        name=leave_doc.name,
        user=manager_user_id,
        read=1,      # Read permission
        write=0,
        share=0,
        flags={"ignore_share_permission": True}
    )

import frappe
from frappe import _

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

    # Check if the Shift Request is already shared with the manager
    existing_share = frappe.db.exists("DocShare", {
        "share_doctype": "Shift Request",
        "share_name": leave_doc.name,
        "user": manager_user_id
    })

    if existing_share:
        return

    # Share the Shift Request with manager (read-only)
    frappe.share.add_docshare(
        doctype="Shift Request",
        name=leave_doc.name,
        user=manager_user_id,
        read=1,      # Read permission
        write=0,
        share=0
    )

    
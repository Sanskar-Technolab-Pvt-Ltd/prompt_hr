import frappe


@frappe.whitelist(allow_guest=True)
def update_job_requisition_status(doc, event):
    """Method to update job requisition status based on workflow state.
    """
    try:
        # print(f"Updating job requisition status for {doc.name}")
        if doc.workflow_state != doc.status:
            doc.status = doc.workflow_state
            
    except Exception as e:
        frappe.log_error(f"Error updating job requisition status", frappe.get_traceback())
        frappe.throw(f"Error updating job requisition status: {str(e)}")
    
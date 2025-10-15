import frappe
from prompt_hr.py.utils import expense_claim_and_travel_request_workflow_email


def on_update(doc, method):
    # ? SEND EMAIL NOTIFICATION FOR EXPENSE CLAIM WORKFLOW
    # expense_claim_and_travel_request_workflow_email(doc)
    workflow_states_to_handle = [
        "Pending",
        "Approved by Reporting Manager",
        "Rejected by Reporting Manager",
        "Escalated",
        "Approved by BU Head",
        "Rejected by BU Head",
        "Booked",
        "Sent to Accounting Team"
    ]
    
    if doc.workflow_state in workflow_states_to_handle:
        print("\n\nworkflow state",doc.workflow_state)
        # Trigger email notification and document sharing
        after_workflow_action(doc)
        
    if doc.has_value_changed('workflow_state'):
        print("\n\nfirst condition is true")
        send_workflow_notification(doc)

def before_save(doc, method):

    attachment_validation(doc)
    
    
def attachment_validation(doc):
    grade = frappe.db.get_value("Employee", doc.get("employee"), "grade")

    mandatory_attachment_travel_modes = frappe.db.get_all(
    "Travel Mode Table", {"grade": grade, "attachment_mandatory": True}, "mode_of_travel",
    pluck="mode_of_travel" 
    )

    for row in doc.get("itinerary"):
        if row.get("custom_travel_mode") in mandatory_attachment_travel_modes and not row.get("custom_attachment"):
            frappe.throw(f"Attachment is Mandatory for Row: {row.get('idx')} in Travel Itinerary Table.")


# ! prompt_hr.py.travel_request.get_eligible_travel_modes
# ? FUNCTION TO GET ELEGIBLE TRAVEL MODE WITH RESEPECT TO EMPLOYEE AND COMPANY
@frappe.whitelist()
def get_eligible_travel_modes(employee, company):
    travel_budget = frappe.db.get_value("Travel Budget", {"company": company}, "name")
    if not travel_budget:
        return None

    grade = frappe.db.get_value("Employee", employee, "grade")
    if not grade:
        return None

    travel_modes = frappe.get_all(
        "Travel Mode Table",
        filters={
            "parent": travel_budget,
            "grade": grade,
        },
        fields=["mode_of_travel"],
        pluck="mode_of_travel",
    )
    return travel_modes if travel_modes else None

def after_workflow_action(doc):
   
    # if doc.workflow_state == "Approved by Reporting Manager":
    print("\n\nFunction is calling.....")
    
    share_map = {
        "Pending": get_reporting_manager,
        "Approved by Reporting Manager": get_travel_desk_users,
        "Rejected by Reporting Manager": get_employee_id,
        "Escalated": get_bu_head,
        "Approved by BU Head": get_travel_desk_users,
        "Rejected by BU Head": get_travel_desk_users,
        "Booked": get_employee_id,
        "Sent to Accounting Team": get_accounts_team_users
    }
    # Get all users with role 'Travel Desk User'
    share_func = share_map.get(doc.workflow_state)
    print("\n\nshare function",share_func)
    if not share_func:
        return

    users_to_share = share_func(doc)
    print("\n\nUser to share",users_to_share)
    if not users_to_share:
        return

    # Make sure users_to_share is always a list
    if isinstance(users_to_share, str):
        users_to_share = [users_to_share]

    print("\n\ndoctype is shared with this users",users_to_share)
    for user in users_to_share:
        # Skip invalid users
        if user in ["All", "Administrator", "ADMIN"]:
            print("\n\nif condition true for user")
            continue
        
        try:
            print("Inside try block")
            # Share the document with the user
            frappe.share.add_docshare(
                doctype=doc.doctype,
                name=doc.name,
                user=user,       
                read=1,
                write=1,
                share=1,
                flags={"ignore_share_permission": True}
            )
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Error sharing Travel Request")
            
            

def send_workflow_notification(doc):
    """Send email based on workflow state transition"""
    workflow_state = doc.workflow_state
    
    print("\n\nWorkflow state",workflow_state)
    # Map workflow states to email templates
    email_template_map = {
        "Pending": "Travel Request - Pending Approval",
        "Approved by Reporting Manager": "Travel Request - RM Approved",
        "Rejected by Reporting Manager": "Travel Request - RM Rejected",
        "Escalated": "Travel Request - Escalated to BU Head",
        "Approved by BU Head": "Travel Request - BU Head Approved",
        "Rejected by BU Head": "Travel Request - BU Head Rejected",
        "Booked": "Travel Request - Booking Confirmed",
        "Sent to Accounting Team": "Travel Request - Sent to Accounts"
    }
    
    template_name = email_template_map.get(workflow_state)
    if template_name:
        send_email_with_template(doc,template_name)
    
def send_email_with_template(doc, template_name):
    """Send email using Email Template"""
    
    # Define recipients and CC based on template
    recipient_config = {
        "Travel Request - Pending Approval": {
            "recipients": get_reporting_manager(doc),
            "cc": []
        },
        "Travel Request - RM Approved": {
            "recipients": get_travel_desk_users(doc),
            "cc": get_employee_id(doc)
        },
        "Travel Request - RM Rejected": {
            "recipients": get_employee_id(doc),
            "cc": get_employee_id(doc)
        },
        "Travel Request - Escalated to BU Head": {
            "recipients": get_bu_head(doc),
            "cc": [get_reporting_manager(doc), get_employee_id(doc)]
        },
        "Travel Request - BU Head Approved": {
            "recipients": get_travel_desk_users(doc),
            "cc": [get_reporting_manager(doc), get_employee_id(doc)]
        },
        "Travel Request - BU Head Rejected": {
            "recipients": get_travel_desk_users(doc),
            "cc": [get_reporting_manager(doc), get_employee_id(doc)]
        },
        "Travel Request - Booking Confirmed": {
            "recipients":get_employee_id(doc),
            "cc": [get_reporting_manager(doc)]
        },
        "Travel Request - Sent to Accounts": {
            "recipients": get_accounts_team_users(doc),
            "cc": []
        }
    }
    
    config = recipient_config.get(template_name, {})
    recipients = config.get("recipients", [])
    cc = config.get("cc", [])
    
    print("\n\nemail id is added in CC",cc)
    if not recipients:
        return
    
    try:
        # Get email template
        email_template = frappe.get_doc("Email Template", template_name)
        
        # Render template with document context
        subject = frappe.render_template(email_template.subject, {"doc": doc})
        message = frappe.render_template(email_template.response_html, {"doc": doc})
        
        # Send email
        frappe.sendmail(
            recipients=recipients,
            cc=cc,
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            expose_recipients="header"
        )
        
        frappe.msgprint(f"Email sent successfully to {(recipients)}")
        
    except Exception as e:
        frappe.log_error(
            f"Failed to send email: {str(e)}",
            f"Travel Request Email Error - {doc.name}"
        )

# Helper methods
def get_reporting_manager(doc):
    if doc.employee:
        reports_to = frappe.db.get_value('Employee', doc.employee, 'reports_to')
        if reports_to:
            manager_user_id = frappe.db.get_value('Employee', reports_to, 'user_id')
            if manager_user_id:
                print("\n\nManager user id",manager_user_id)
                return manager_user_id
            else:
                return ""
        else:
            return ""
        
def get_bu_head(doc):
    if doc.employee:
        business_unit = frappe.db.get_value('Employee',doc.employee,'custom_business_unit')
        if business_unit:
            bu_head = frappe.db.get_value('Business Unit',business_unit,'business_unit_head')
            if bu_head:
                bu_id = frappe.db.get_value('Employee',bu_head,'user_id')
                if bu_id:
                    print("\n\nBU id",bu_id)
                    return bu_id
    
def get_employee_id(doc):
    if doc.employee:
        user_id = frappe.db.get_value('Employee',doc.employee,'user_id')
        if user_id:
            return user_id
        
def get_travel_desk_users(doc):
    """Get all users with Travel Desk User role"""
    travel_desk_users = frappe.get_all(
        'Has Role',
        filters={'role': 'Travel Desk User', 'parenttype': 'User'},
        fields=['parent']
    )
    print("\n\nTravel Desk Users",travel_desk_users)
    return [user.parent for user in travel_desk_users] 

def get_accounts_team_users(doc):
    """Get all users with Accounts Travel Approver role"""
    accounts_users = frappe.get_all(
        'Has Role',
        filters={'role': 'S - Accounts Travel Approver', 'parenttype': 'User'},
        fields=['parent']
    )
    return [user.parent for user in accounts_users]

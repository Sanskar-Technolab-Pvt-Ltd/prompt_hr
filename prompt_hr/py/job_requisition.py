import frappe
from frappe import throw
from prompt_hr.py.utils import send_notification_email,get_hr_managers_by_company, fetch_company_name

@frappe.whitelist()
def on_update(doc, method):
    if doc.custom_target_hiring_duration:
        if doc.custom_target_hiring_duration == "Custom Date":
            doc.db_set("custom_target_hiring_date", doc.expected_by if doc.expected_by else frappe.utils.nowdate())
        else:
            try:
                days = int(doc.custom_target_hiring_duration.split()[0])
            except (ValueError, IndexError):
                days = 0
            doc.db_set("custom_target_hiring_date", frappe.utils.add_days(doc.posting_date, days))


def notify_approver(doc, method):
    """Method to notify the approver when a job requisition is created or saved until workflow state is not pending
    """
    try:
        
        is_insert = doc.flags.in_insert
        company_id = doc.company
        workflow_approval_list = frappe.db.get_all("Workflow Approval", {"applicable_doctype": 'Job Requisition', "company": company_id}, 'name')
        
        applicable_workflow_approval = None
        workflow_approval_without_criteria = None
        user_emails = []
        by_roles = []
        transitions_list=[]
        # for_prompt = fetch_company_name(prompt=1)
        # for_indifoss = fetch_company_name(indifoss=1)
                
        # if for_prompt.get("error"):
        #     throw(for_prompt.get("message"))
        # if for_indifoss.get("error"):
        #     throw(for_indifoss.get("message"))
    
        
        if workflow_approval_list:
            is_workflow_approval_found = False
            
            for workflow_approval in workflow_approval_list:
                all_criteria = frappe.db.get_all("Workflow Approval Criteria", {"parenttype": "Workflow Approval", "parent": workflow_approval.get("name")}, ["field_name",   "expected_value"])
                
                if not len(all_criteria):
                    workflow_approval_without_criteria = workflow_approval.get("name")
                    
                if all_criteria and all(str(doc.get(criteria.get("field_name"))).strip() == str(criteria.get("expected_value")).strip() for criteria in all_criteria):
                    applicable_workflow_approval = workflow_approval.get("name")
                    is_workflow_approval_found = True
                    break
            
            if not is_workflow_approval_found:
                applicable_workflow_approval = workflow_approval_without_criteria
                
            if applicable_workflow_approval:
                workflow_approval_doc = frappe.get_doc("Workflow Approval", {"applicable_doctype": doc.doctype})

                transitions_list = [row for row in workflow_approval_doc.workflow_approval_hierarchy if row.state == doc.workflow_state]
                use_default_workflow = False
                
        else:
                default_workflow = frappe.db.get_value("Workflow", {"is_active": 1, "document_type": "Job Requisition"}, 'name')
                
                
                def_workflow_doc = frappe.get_doc("Workflow", default_workflow)
                
                transitions_list = [row for row in def_workflow_doc.transitions if row.state == doc.workflow_state]
                use_default_workflow = True
                
        if transitions_list:
                for transition in transitions_list:
                    if transition.get("allowed_by") == "User" or not use_default_workflow:
                        if frappe.db.exists("Employee", {"status": "Active", "company": doc.company, "user_id": transition.get("user")}):
                            if transition.get("user") not in user_emails:
                                user_emails.append(transition.get("user"))
                    
                    elif transition.get("allowed_by") == "Role" or use_default_workflow:
                        if use_default_workflow:
                            if transition.get("allowed") not in by_roles and transition.get("allowed") != "All":
                                by_roles.append(transition.get("allowed"))
                        else:
                            if transition.get("role") not in by_roles:
                                by_roles.append(transition.get("role"))
                        
                
                if by_roles :
                    for role in by_roles:
                        user_list = frappe.db.get_all("Has Role", {"parenttype": "User", "role": role}, "parent as user")

                        for user in user_list:
                            user_id = None 

                            if frappe.db.exists("Employee", {"status": "Active", "company": doc.company, "user_id": user.get("user")}):
                                if role == "Head of Department":
                                    hod_emp = frappe.db.get_value("Department", doc.department, "custom_department_head")
                                    if hod_emp:
                                        hod_user = frappe.db.get_value("Employee", hod_emp, "user_id")
                                        if hod_user:
                                            user_id = hod_user
                                else:
                                    user_id = user.get("user")

                                
                                if user_id and (user_id not in user_emails and user_id != "Administrator"):
                                    user_emails.append(user_id)

                if user_emails:
                    if is_insert:
                        send_notification_email(
                            recipients=user_emails,
                            notification_name="Job Requisition Created",
                            doctype="Job Requisition",
                            docname=doc.name,
                            fallback_subject= "Job Requisition Created",
                            fallback_message="Job Requisition has been created. Please check and perform next process"
                        )
                    else:
                        send_notification_email(
                            recipients=user_emails,
                            notification_name="Job Requisition Updated",
                            doctype="Job Requisition",
                            docname=doc.name,
                            fallback_subject="Job Requisition Updated",
                            fallback_message="Job Requisition has been updated"
                        )
        else:
                hr_manager_user_emails = []
                hr_manager_user_list = frappe.db.get_all("Has Role", {"parenttype": "User", "role": "S - HR Director (Global Admin)"}, "parent as user")
                
                if hr_manager_user_list:
                    for hr_manager in hr_manager_user_list:
                        if frappe.db.exists("Employee", {"user_id": hr_manager.get("user"), "status":"Active", "company": doc.company}):
                            hr_manager_user_emails.append(hr_manager.get("user"))
                    
                    send_notification_email(
                        recipients=hr_manager_user_emails,
                        notification_name="Job Requisition Final Stage",
                        doctype="Job Requisition",
                        docname=doc.name,
                        fallback_subject="Job Requisition Update",
                        fallback_message=f"Dear HR Manager, <br> There is an update in job requisition, please review it"
                    )
        
    except Exception as e:
        frappe.log_error("Error while notifying approver", frappe.get_traceback())
        throw(str(e))



@frappe.whitelist()
def add_or_update_custom_last_updated_by(doc, method):
    """ Method to set custom_last_updated_by_employee and custom_employee_name fields in Job Requisition to recognize the last user who modified the document.
    """
    try:
        if doc.modified_by:
            employee_id = frappe.get_value("Employee", {"user_id": doc.modified_by}, "name")
            
            if employee_id:
                employee_name = frappe.get_value("Employee", employee_id, "employee_name")
                doc.custom_last_updated_by_employee = employee_id
                doc.custom_employee_name = employee_name
            else:
                doc.custom_last_updated_by_employee = None
                doc.custom_employee_name = None
                
    except Exception as e:
        frappe.log_error(f"Error in add_or_update_custom_last_updated_by: {str(e)}", "Job Requisition")
    

def set_requested_by(doc, event):
    """ Method to set requested_by field in Job Requisition if not set
    """
    try:
        if not doc.requested_by:
            user = frappe.session.user
            employee_id = frappe.get_value("Employee", {"user_id": user}, "name")
            
            if employee_id:
                employee_name = frappe.get_value("Employee", employee_id, "employee_name")
                doc.requested_by = employee_id
                doc.requested_by_name = employee_name
# 
    except Exception as e:
        frappe.log_error(f"Error in set_requested_by Job Requisition", frappe.get_traceback())
    

# def after_insert(doc, event):
#     try:
#         # ? SEND NOTIFICATION EMAIL TO HR MANAGERS
#         hr_emails = get_hr_managers_by_company(doc.company)
#         if hr_emails:
#             send_notification_email(
#                 recipients=hr_emails,
#                 doctype=doc.doctype,
#                 docname=doc.name,
#                 notification_name="New Job Requisition Alert"
#             )
#         else:
#             frappe.log_error("No HR Managers Found", f"No HR Managers found for company: {doc.company}")
#     except Exception as e:
#         frappe.log_error("Error in after_insert", str(e))



@frappe.whitelist()
def get_workflow_approvals(company, doctype, docname):
    """
    #! GET WORKFLOW APPROVALS FOR GIVEN COMPANY AND DOCTYPE
    #! IF NO CUSTOM APPROVAL FOUND, USE DEFAULT WORKFLOW CONFIG
    """
    table_data = []

    #? FETCH CUSTOM WORKFLOW APPROVALS
    approvals = frappe.get_all(
        'Workflow Approval',
        filters={
            'company': company,
            'applicable_doctype': doctype
        },
        fields=['name'],
        order_by='modified desc',
    )

    doc = frappe.get_doc(doctype, docname)
    filtered_approvals = []

    if approvals:
        for approval in approvals:
            criteria = frappe.get_all(
                'Workflow Approval Criteria',
                filters={'parent': approval.name},
                fields=['field_name', 'expected_value']
            )
            if not criteria:
                filtered_approvals.append(approval)
            else:
                is_approval_applicable = True
                for c in criteria:
                    if doc.get(c.field_name):
                        if str(doc.get(c.field_name)) != str(c.expected_value):
                            is_approval_applicable = False
                            break
                    else:
                        is_approval_applicable = False
                        break

                if is_approval_applicable:
                    filtered_approvals.append(approval)
    #? CASE 1 — USE CUSTOM WORKFLOW APPROVAL (IF FOUND)
    if filtered_approvals:
        approval = filtered_approvals[0]
        workflow_approval_hierarchy = frappe.get_all(
            'Workflow Approval Hierarchy',
            filters={'parent': approval.name, "state": doc.workflow_state},
            fields=['*'],
            order_by='idx asc'
        )
        if workflow_approval_hierarchy:
            for row in workflow_approval_hierarchy:
                table_data.append({
                    "state": row.state,
                    "action": row.action,
                    "next_state": row.next_state,
                    "allowed_by": row.allowed_by,
                    "value": row.employee if row.allowed_by == "User" else row.role,
                })

    #? CASE 2 — FALLBACK TO DEFAULT WORKFLOW
    else:
        workflow_name = frappe.db.get_value('Workflow', {'document_type': doctype, 'is_active': 1}, 'name')
        if workflow_name:
            transitions = frappe.get_all(
                'Workflow Transition',
                filters={'parent': workflow_name, 'state': doc.workflow_state},
                fields=['state', 'action', 'next_state', 'allowed'],
                order_by='idx asc'
            )

            for row in transitions:
                table_data.append({
                    "state": row.state,
                    "action": row.action,
                    "next_state": row.next_state,
                    "allowed_by": "Role",
                    "value": row.allowed
                })

    return table_data

import frappe
from prompt_hr.utils import get_next_date
from prompt_hr.py.utils import send_notification_email



# @frappe.whitelist(allow_guest=True)
# def update_job_requisition_status(doc, event):
#     """Method to update job requisition status based on workflow state.
#         runs on validate hook
#     """
#     try:
#         # print(f"Updating job requisition status for {doc.name}")
        
#         print(f"\n\n\n Workflow state: {doc.workflow_state} is new  {doc.is_new()}\n\n\n")
#         if doc.workflow_state != doc.status:
#             job_requisition_notification(doc)
            
            
#     except Exception as e:
#         frappe.log_error(f"Error updating job requisition status", frappe.get_traceback())
#         frappe.throw(f"Error updating job requisition status: {str(e)}")


def job_requisition_notification(doc):
    """Method to send notifications based on workflow state change runs on validate hook.
    """
    
    try:
        pass
        # if doc.workflow_state != doc.status:
        
        #     if doc.workflow_state == "Pending":
        #         employee_id = frappe.db.get_value("Department", doc.department, "custom_department_head")
                
        #         if employee_id:
                    
        #             user_id = frappe.db.get_value("Employee", employee_id, "user_id")
        #             if user_id:
        #                 user_email = frappe.db.get_value("User", user_id, "email")
        #                 if user_email:
        #                     pass
        #                     print(f"Sending email to {user_email}")
        #                     notification = frappe.get_doc({
        #                             "doctype": "Notification Log",
        #                             "subject": "Job Requisition Created",
        #                             "for_user": user_id,
        #                             "type": "Energy Point",
        #                             "document_type": "Job Requisition",
        #                             "document_name": doc.name,
        #                         })
        #                     notification.insert(ignore_permissions=True) 
                            
        #                     frappe.sendmail(
        #                         recipients=[user_email,],
        #                         subject="Job Requisition has been created",
        #                         content=f"Job requisition {doc.name} has been created",
        #                         # now = True
        #                         )
                    
        #     if doc.workflow_state == "Approved by HOD":
                
        #         user_ids = frappe.db.get_all("Employee", {"company": doc.company, "designation": "Managing Director"}, "user_id")
        #         user_emails = [frappe.db.get_value("User", user_id.get("user_id"), "email") for user_id in user_ids if user_id.get("user_id")]

        #         if user_emails:    
                    
        #             for user_email in user_emails:
        #                 notification = frappe.get_doc({
        #                             "doctype": "Notification Log",
        #                             "subject": "Job Requisition Approved By HOD",
        #                             "for_user": user_email,
        #                             "type": "Energy Point",
        #                             "document_type": "Job Requisition",
        #                             "document_name": doc.name,
        #                         })
        #             notification.insert(ignore_permissions=True)
                    
                    
        #             frappe.sendmail(
        #                         recipients=user_emails,
        #                         subject="Job Requisition Approved By HOD",
        #                         content=f"Job requisition {doc.name} has been Approved by HOD",
        #                         # now=True
        #                         )

        #     if doc.workflow_state == "Rejected by HOD":
                
        #         employee_user_id = frappe.db.get_value("Employee", doc.requested_by, "user_id")
                
        #         user_email = frappe.db.get_value("User", employee_user_id, "email")

        #         if user_email:
        #             notification = frappe.get_doc({
        #                             "doctype": "Notification Log",
        #                             "subject": "Job Requisition Rejected By HOD",
        #                             "for_user": employee_user_id,
        #                             "type": "Energy Point",
        #                             "document_type": "Job Requisition",
        #                             "document_name": doc.name,
        #                         })
        #             notification.insert(ignore_permissions=True)
        #             frappe.sendmail(
        #                         recipients=[user_email,],
        #                         subject="Job Requisition Rejected By HOD",
        #                         content=f"Job Requisition {doc.name} has been Rejected by HOD",
        #                         # now = True                       
        #                         )
                    
        #     if doc.workflow_state == "Rejected by Director":
        #         employee_user_id = frappe.db.get_value("Employee", doc.requested_by, "user_id")
                
        #         user_email = frappe.db.get_value("User", employee_user_id, "email")

        #         if user_email:
        #             notification = frappe.get_doc({
        #                             "doctype": "Notification Log",
        #                             "subject": "Job Requisition Rejected By Director",
        #                             "for_user": employee_user_id,
        #                             "type": "Energy Point",
        #                             "document_type": "Job Requisition",
        #                             "document_name": doc.name,
        #                         })
        #             notification.insert(ignore_permissions=True)
        #             frappe.sendmail(
        #                         recipients=[user_email,],
        #                         subject="Job Requisition Rejected By Director",
        #                         content=f"Job Requisition {doc.name} has been Rejected by Director",
        #                         # now = True                       
        #                         )
            
    except Exception as e:
        frappe.log_error(f"Error sending notification", frappe.get_traceback())
        frappe.throw(f"Error sending notification: {str(e)}")
        
@frappe.whitelist()
def update_job_applicant_status_based_on_interview(doc, event):
    """Method to update Job Applicant status and set custom_interview_status and custom_interview_round based on Interview.
        using validate and submit hook
    """
    try:                
        
        if event == "on_submit":
            if doc.interview_round:
                is_final_round = frappe.db.get_value("Interview Round", doc.interview_round, "custom_is_final_round") or None
                
                if is_final_round and doc.status == "Cleared":
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Final Interview Selected")
                    
        if event == "validate":
            if doc.job_applicant:
                job_applicant_interview_status = frappe.db.get_value("Job Applicant", doc.job_applicant, "custom_interview_status") or None
                job_applicant_status = frappe.db.get_value("Job Applicant", doc.job_applicant, "status") or None
                # job_applicant_status_field = frappe.get_meta("Job Applicant").get_field("status")
            
                if job_applicant_interview_status:
                    print(f"\n\n  exists {job_applicant_interview_status} \n\n")
                    
                    if doc.status == "Pending" and job_applicant_interview_status != "Scheduled":
                
                        # new_job_applicant_status = f"{doc.interview_round}-Scheduled"
                        
                        # if new_job_applicant_status not in job_applicant_status_field.options:
                        #     options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                        
                        #     if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                        #         frappe.db.set_value("Property Setter", property_setter, "value", options)
                        #     else:
                        #         property_setter = frappe.new_doc("Property Setter")
                        #         property_setter.doctype_or_field = "DocField"
                        #         property_setter.doc_type = "Job Applicant"
                        #         property_setter.field_name = "status"
                        #         property_setter.property = "options"
                        #         property_setter.property_type = "Select"
                        #         property_setter.value = options
                        #         property_setter.insert(ignore_permissions=True)
                        #     frappe.clear_cache(doctype="Job Applicant")   
                        # else:
                        #     print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                        
                        # frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                    
                    if doc.status == "Under Review" and job_applicant_interview_status != "Under Review":
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                    
                    
                    if doc.status == "Cleared" and job_applicant_interview_status != "Cleared":
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")
                    
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Cleared")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                    
                    if doc.status == "Rejected" and job_applicant_interview_status != "Rejected":
                        
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")                        
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Rejected")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                        
                else:
                    if doc.status == "Pending":
                    
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                    
                    if doc.status == "Under Review":
                        
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                    
                    if doc.status == "Cleared":
                        
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Cleared")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                    
                    if doc.status == "Rejected":
                        
                        if job_applicant_status and job_applicant_status != "Interview in Progress":
                            frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Interview in Progress")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Rejected")
                        frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
            
    except Exception as e:
        frappe.log_error(f"Error updating job requisition status", frappe.get_traceback())
        frappe.throw(f"Error updating job requisition status: {str(e)}")


@frappe.whitelist()
def update_job_applicant_status_based_on_job_offer(doc, event):
    """Method to update Job Applicant status, based on JOB Offer Status.
    """
    
    try:
        print(f"\n\n\n EVENT {event}\n\n\n")
        if event == "validate":
            if doc.status == "Awaiting Response":
                frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Job Offer Given")
        
        if event == "on_submit":
            if doc.workflow_state == "Rejected":
                doc.status = "Rejected"
                
            # ? Get job offer owner email
            owner_email = doc.owner
            # ? Send email on APPROVED and REJECTED BY HR
            
            if owner_email and owner_email not in ["Administrator", "Guest"]:
                send_notification_email(
                    recipients=[owner_email],
                    notification_name="Job Offer Update",  # Notification Doc
                    doctype="Job Offer",
                    docname=doc.name,
                    send_link=False,
                    fallback_subject=f"Job Offer: {doc.name} - {doc.workflow_state}",
                    fallback_message=f"""
                        Hello,<br><br>
                        The Job Offer <b>{doc.name}</b> for candidate <b>{doc.applicant_name}</b> 
                        has been <b>{{doc.workflow_state}}</b> by {frappe.session.user}.<br><br>
                        Regards,<br>HR Team
                    """,
                    send_header_greeting=True,
                )

            if doc.status in ["Accepted", "Accepted with Conditions"]:
                print("\n\n setting job applicant status to job offer accepted \n\n")
                frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Job Offer Accepted")
        
            if doc.status == "Rejected":
                frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Job Offer Rejected")
        
    except Exception as e:
        frappe.log_error(f"Error updating job applicant status", frappe.get_traceback())
        frappe.throw(f"Error updating job applicant status: {str(e)}")
        
        
        
# @frappe.whitelist()
# def add_probation_feedback_data_to_employee(doc, event):
#     """Method to add Probation Details to Employee if company is equal to IndiFOSS Analytical Pvt Ltd when Probation Feedback Form is submitted.
#     """
#     try:
#         if doc.employee and doc.company == "IndiFOSS Analytical Pvt Ltd":
#             if doc.probation_status == "Confirm":
#                 if doc.confirmation_date:
#                     frappe.db.set_value("Employee", doc.employee, "final_confirmation_date", doc.confirmation_date)
#                     frappe.db.set_value("Employee", doc.employee, "custom_probation_status", "Confirmed")
                    
            
#             elif doc.probation_status == "Extend":
#                 probation_end_date = str(frappe.db.get_value("Employee", doc.employee, "custom_probation_end_date")) or None
                
#                 if probation_end_date:
#                     # extended_probation_end_date = add_to_date(probation_end_date, months=doc.extension_period)
#                     next_date_response = get_next_date(probation_end_date, doc.extension_period)
                    
#                     if not next_date_response.get("error"):
                        
#                         extended_probation_end_date = next_date_response.get("message")
                        
#                     else:
                        
#                         frappe.throw(f"Error getting next date: {next_date_response.get('message')}")
#                 else:
#                     frappe.throw("No probation end date found for employee.")
#                     extended_probation_end_date = None

                
#                 employee_doc = frappe.get_doc("Employee", doc.employee)
                
#                 current_user = frappe.session.user
                
#                 if current_user:
#                     employee = frappe.db.get_value("Employee", {"user_id": current_user}, ["name", "employee_name"], as_dict=True)
#                 else:
#                     employee = None
#                 if employee_doc:
#                     employee_doc.append("custom_probation_extension_details", {
#                         "probation_end_date": employee_doc.custom_probation_end_date,
#                         "extended_date": extended_probation_end_date,
#                         "reason": doc.reason,
#                         "extended_by": employee.get("name") if employee else '',
#                         "extended_by_emp_name": employee.get("employee_name") if employee else ''
#                     })
#                     employee_doc.custom_probation_status = "Pending"
#                     employee_doc.save(ignore_permissions=True)
#                     frappe.db.commit()
            
#             elif doc.probation_status == "Terminate":        
#                     frappe.db.set_value("Employee", doc.employee, "custom_probation_status", "Terminated")
                
#     except Exception as e:
#         frappe.log_error(f"Error updating job applicant status", frappe.get_traceback())
#         frappe.throw(f"Error updating job applicant status: {str(e)}")
        

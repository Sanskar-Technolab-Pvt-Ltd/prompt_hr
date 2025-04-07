import frappe





@frappe.whitelist(allow_guest=True)
def update_job_requisition_status(doc, event):
    """Method to update job requisition status based on workflow state.
        runs on validate hook
    """
    try:
        # print(f"Updating job requisition status for {doc.name}")
        
        print(f"\n\n\n Workflow state: {doc.workflow_state} is new  {doc.is_new()}\n\n\n")
        if doc.workflow_state != doc.status:
            doc.status = doc.workflow_state
            
            job_requisition_notification(doc)
            
            
    except Exception as e:
        frappe.log_error(f"Error updating job requisition status", frappe.get_traceback())
        frappe.throw(f"Error updating job requisition status: {str(e)}")


def job_requisition_notification(doc):
    """Method to send notifications based on workflow state change.
    """
    
    try:
        if doc.workflow_state == "Pending":
            employee_id = frappe.db.get_value("Department", doc.department, "custom_department_head")
            
            
            
            if employee_id:
                
                user_id = frappe.db.get_value("Employee", employee_id, "user_id")
                if user_id:
                    user_email = frappe.db.get_value("User", user_id, "email")
                    if user_email:
                        pass
                        print(f"Sending email to {user_email}")
                        notification = frappe.get_doc({
                                "doctype": "Notification Log",
                                "subject": "Job Requisition Created",
                                "for_user": user_id,
                                "type": "Energy Point",
                                "document_type": "Job Requisition",
                                "document_name": doc.name,
                            })
                        notification.insert(ignore_permissions=True) 
                        
                        frappe.sendmail(
                            recipients=[user_email,],
                            subject="Job Requisition has been created",
                            content=f"Job requisition {doc.name} has been created",
                            # now = True
                            )
                
        if doc.workflow_state == "Approved by HOD":
            
            user_ids = frappe.db.get_all("Employee", {"company": doc.company, "designation": "Managing Director"}, "user_id")
            user_emails = [frappe.db.get_value("User", user_id.get("user_id"), "email") for user_id in user_ids if user_id.get("user_id")]

            if user_emails:    
                
                for user_email in user_emails:
                    notification = frappe.get_doc({
                                "doctype": "Notification Log",
                                "subject": "Job Requisition Approved By HOD",
                                "for_user": user_email,
                                "type": "Energy Point",
                                "document_type": "Job Requisition",
                                "document_name": doc.name,
                            })
                notification.insert(ignore_permissions=True)
                
                
                frappe.sendmail(
                            recipients=user_emails,
                            subject="Job Requisition Approved By HOD",
                            content=f"Job requisition {doc.name} has been Approved by HOD",
                            # now=True
                            )

        if doc.workflow_state == "Rejected by HOD":
            
            employee_user_id = frappe.db.get_value("Employee", doc.requested_by, "user_id")
            
            user_email = frappe.db.get_value("User", employee_user_id, "email")

            if user_email:
                notification = frappe.get_doc({
                                "doctype": "Notification Log",
                                "subject": "Job Requisition Rejected By HOD",
                                "for_user": employee_user_id,
                                "type": "Energy Point",
                                "document_type": "Job Requisition",
                                "document_name": doc.name,
                            })
                notification.insert(ignore_permissions=True)
                frappe.sendmail(
                            recipients=[user_email,],
                            subject="Job Requisition Rejected By HOD",
                            content=f"Job Requisition {doc.name} has been Rejected by HOD",
                            # now = True                       
                            )
                
        if doc.workflow_state == "Rejected by Director":
            employee_user_id = frappe.db.get_value("Employee", doc.requested_by, "user_id")
            
            user_email = frappe.db.get_value("User", employee_user_id, "email")

            if user_email:
                notification = frappe.get_doc({
                                "doctype": "Notification Log",
                                "subject": "Job Requisition Rejected By Director",
                                "for_user": employee_user_id,
                                "type": "Energy Point",
                                "document_type": "Job Requisition",
                                "document_name": doc.name,
                            })
                notification.insert(ignore_permissions=True)
                frappe.sendmail(
                            recipients=[user_email,],
                            subject="Job Requisition Rejected By Director",
                            content=f"Job Requisition {doc.name} has been Rejected by Director",
                            # now = True                       
                            )
        
    except Exception as e:
        frappe.log_error(f"Error sending notification", frappe.get_traceback())
        frappe.throw(f"Error sending notification: {str(e)}")
        
        
        
@frappe.whitelist()
def update_job_applicant_status_based_on_interview(doc, event):
    """Method to update Job Applicant status and set custom_interview_status and custom_interview_round based on Interview.
        using validate hook
    """
    try:                
        # print(f"\n\n\n Workflow state: {doc.workflow_state} is new  {doc.is_new()}\n\n\n")
        if doc.job_applicant:
            job_applicant_status = frappe.db.get_value("Job Applicant", doc.job_applicant, "custom_interview_status") or None
            job_applicant_status_field = frappe.get_meta("Job Applicant").get_field("status")
        
            if job_applicant_status:
                print(f"\n\n  exists {job_applicant_status} \n\n")
                
                if doc.status == "Pending" and job_applicant_status != "Scheduled":
            
                    new_job_applicant_status = f"{doc.interview_round}-Scheduled"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                    else:
                        print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                
                if doc.status == "Under Review" and job_applicant_status != "Under Review":
                    new_job_applicant_status = f"{doc.interview_round}-Under Review"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                    else:
                        print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                
                
                if doc.status == "Cleared" and job_applicant_status != "Cleared":
                    print(f"\n\n Clearing \n\n")
                    
                    new_job_applicant_status = f"{doc.interview_round}-Cleared"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            print(f"\n\n Updating Property Setter {property_setter}\n\n")
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            print(f"\n\n Creating Property Setter \n\n")
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                        
                    else:
                        print(f"\n\n {new_job_applicant_status} already exists in options \n\n")
                            
                    print(f"\n\n {new_job_applicant_status} Setting this options \n\n")    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Cleared")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                
                if doc.status == "Rejected" and job_applicant_status != "Rejected":
                    new_job_applicant_status = f"{doc.interview_round}-Rejected"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            print(f"\n\n Updating Property Setter {property_setter} {options}\n\n")
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                            
                        else:
                            print(f"\n\n Creating Property Setter \n\n")
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                        
                    else:
                        print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    print(f"\n\n {new_job_applicant_status} Setting this options \n\n")    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Rejected")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                    
            else:
                if doc.status == "Pending":
                    
                    new_job_applicant_status = f"{doc.interview_round}-Scheduled"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                        print(f"\n\n Setting options to {options} \n\n")
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            print(f"\n\n Creating Property Setter {property_setter}\n\n")
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                        
                    # else:
                    #     print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                
                if doc.status == "Under Review":
                    
                    new_job_applicant_status = f"{doc.interview_round}-Under Review"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                        print(f"\n\n Setting options to {options} \n\n")
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            print(f"\n\n Creating Property Setter {property_setter}\n\n")
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                        
                    # else:
                    #     print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Scheduled")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                
                if doc.status == "Cleared":
                    
                    new_job_applicant_status = f"{doc.interview_round}-Cleared"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                        print(f"\n\n Setting options to {options} \n\n")
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            print(f"\n\n Creating Property Setter {property_setter}\n\n")
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                        
                    # else:
                    #     print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Cleared")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
                
                if doc.status == "Rejected":
                    
                    new_job_applicant_status = f"{doc.interview_round}-Rejected"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                        print(f"\n\n Setting options to {options} \n\n")
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            print(f"\n\n Creating Property Setter {property_setter}\n\n")
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                        
                    # else:
                    #     print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_status", "Rejected")
                    frappe.db.set_value("Job Applicant", doc.job_applicant, "custom_interview_round", doc.interview_round)
            
    except Exception as e:
        frappe.log_error(f"Error updating job requisition status", frappe.get_traceback())
        frappe.throw(f"Error updating job requisition status: {str(e)}")
        
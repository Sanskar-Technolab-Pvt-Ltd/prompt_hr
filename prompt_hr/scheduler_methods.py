import frappe

from frappe.utils import date_diff, today, add_to_date, getdate



@frappe.whitelist()
def create_probation_feedback_form():
    """Scheduler method to create probation feedback form based on the days after when employee joined mentioned in the HR Settings.
        - And Also notify the employee's reporting manager if the remarks are not added to the form.  
    """
    
    try:
        print(f"\n\n API Called \n\n")
        first_feedback_days = frappe.db.get_single_value("HR Settings", "custom_first_feedback_after")
        second_feedback_days = frappe.db.get_single_value("HR Settings", "custom_second_feedback_after")
        
        
        if first_feedback_days or second_feedback_days:
        
            employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": "Prompt Equipments PVT LTD", "custom_probation_status": "Pending"}, "name")
            print(f"\n\n API Called employee list {employees_list}\n\n")
            
            for employee in employees_list:
                if employee.get("name"):
                    emp_joining_date = frappe.db.get_value("Employee", employee.get("name"), "date_of_joining")
                    
                    first_feedback_form_id = frappe.db.get_value("Employee", employee.get("name"), "custom_first_probation_feedback") or None
                    second_feedback_form_id = frappe.db.get_value("Employee", employee.get("name"), "custom_second_probation_feedback") or None
                    
                    create_only_one = True if not first_feedback_form_id and not second_feedback_form_id else False
                    
                    
                    if emp_joining_date:
                        date_difference= date_diff(today(), emp_joining_date)
                        
                        if first_feedback_days <= date_difference:
                            if not first_feedback_form_id:
                                print(f" \n\n creating First Feedback Form \n\n")
                                employee_doc = frappe.get_doc("Employee", employee.get("name"))
                                first_probation_form = frappe.get_doc({
                                    "doctype":"Probation Feedback Form",
                                    "employee": employee.get("name"),
                                    "employee_name": employee_doc.get("employee_name"),
                                    "department": employee_doc.get("department"),
                                    "designation": employee_doc.get("designation"),
                                    "company": employee_doc.get("company"),
                                    "product_line": employee_doc.get("custom_product_line"),
                                    "business_unit": employee_doc.get("custom_business_unit"),
                                    "reporting_manager": employee_doc.get("reports_to"),
                                    "probation_feedback_for": "30 Days",
                                    "evaluation_date": today(),
                                })
                                
                                
                                question_list = frappe.db.get_all("Probation Question", {"company": "Prompt Equipments PVT LTD", "probation_feedback_for": "30 Days"}, "name")
                                
                                if question_list:
                                    print(f"\n\n question list \n\n")
                                    for question in question_list:
                                        first_probation_form.append("probation_feedback_prompt", {
                                            "question": question.get("name"),
                                            "frequency": "30 Days"
                                        })
                                        
                                first_probation_form.insert(ignore_permissions=True)
                                employee_doc.custom_first_probation_feedback = first_probation_form.name
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()
                            else:
                                remarks_added = frappe.db.exists("Probation Feedback Prompt", {"parenttype": "Probation Feedback Form", "parent": first_feedback_form_id, "rating": ["not in", ["0", ""]]}, "name")
                                
                                
                                if not remarks_added:
                                    reporting_manager_emp_id = frappe.db.get_value("Probation Feedback Form", first_feedback_form_id, "reporting_manager") or None
                                    
                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                        
                                
                                    if reporting_manager_emp_id:
                                        
                                        reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id") or None
                                        
                                        
                                        if reporting_manager_user_id:
                                            reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, first_feedback_form_id, employee.get("employee_name"))
                                                
                        if second_feedback_days <= date_difference:
                            if not second_feedback_form_id and not create_only_one:
                                
                                
                                employee_doc = frappe.get_doc("Employee", employee.get("name"))
                                second_probation_form = frappe.get_doc({
                                    "doctype":"Probation Feedback Form",
                                    "employee": employee.get("name"),
                                    "employee_name": employee_doc.get("employee_name"),
                                    "department": employee_doc.get("department"),
                                    "designation": employee_doc.get("designation"),
                                    "company": employee_doc.get("company"),
                                    "product_line": employee_doc.get("custom_product_line"),
                                    "business_unit": employee_doc.get("custom_business_unit"),
                                    "reporting_manager": employee_doc.get("reports_to"),
                                    "probation_feedback_for": "60 Days",
                                    "evaluation_date": today()
                                })
                                
                                
                                question_list = frappe.db.get_all("Probation Question", {"company": "Prompt Equipments PVT LTD", "probation_feedback_for": "60 Days"}, "name")
                                
                                if question_list:
                                    for question in question_list:
                                        second_probation_form.append("probation_feedback_prompt", {
                                            "question": question.get("name"),
                                            "frequency": "60 Days"
                                        })
                                
                                second_probation_form.insert(ignore_permissions=True)
                                employee_doc.custom_second_probation_feedback = second_probation_form.name
                                employee_doc.save(ignore_permissions=True)
                                
                                
                                
                                
                                frappe.db.commit()
                            elif second_feedback_form_id:
                                    print(f" \n\n Second Feedback Form already created \n\n")

                                    remarks_added = frappe.db.exists("Probation Feedback Prompt", {"parenttype": "Probation Feedback Form", "parent": second_feedback_form_id, "rating": ["not in", ['0', '']]})
                                    if not remarks_added:
                                        reporting_manager_emp_id = frappe.db.get_value("Probation Feedback Form", second_feedback_form_id, "reporting_manager") or None
                                        if not reporting_manager_emp_id:
                                            reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None

                                        if reporting_manager_emp_id:
                                            reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id") or None
                                            if reporting_manager_user_id:
                                                reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                                if reporting_manager_email:
                                                    send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, second_feedback_form_id, employee.get("employee_name"))
                                                    
    except Exception as e:
        frappe.log_error("Error while creating probation feedback form", frappe.get_traceback())


def send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id,probation_feedback_form_id, employee_id):
    """Method to send a reminder email to the reporting manager"""
    
    try:
        notification = frappe.get_doc({
                "doctype": "Notification Log",
                "subject": "Add Remarks to Feedback Form",
                "for_user": reporting_manager_user_id,
                "type": "Energy Point",
                "document_type": "Probation Feedback Form",
                "document_name": probation_feedback_form_id,
            })
        notification.insert(ignore_permissions=True) 
        
        frappe.sendmail(
            recipients=[reporting_manager_email,],
            subject="Feedback Form Reminder",
            content=f"Reminder: Add Remarks to Feedback Form {probation_feedback_form_id} for {employee_id}",
            # now = True
            )
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("Error while sending second feedback mail", frappe.get_traceback())
        print(f" \n\n Second Feedback Mail Failed: {frappe.get_traceback()} \n\n")




@frappe.whitelist()
def create_confirmation_evaluation_form():
    try:
        employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": "Prompt Equipments PVT LTD", "custom_probation_status": "Pending"}, "name")
        
        print(f"\n\n EMPLOYEES LIST: {employees_list}\n\n")
        
        if employees_list:
            for employee_id in employees_list:
                probation_days = frappe.db.get_value("Employee", employee_id.get("name"), "custom_probation_period")
                
                if probation_days:
                    
                    joining_date = frappe.db.get_value("Employee", employee_id.get("name"), "date_of_joining")
                    
                    print(f"\n\n JOINING DATE: {joining_date} {type(joining_date)}\n\n")
                    probation_end_date = getdate(add_to_date(joining_date, days=probation_days))
                    print(f"\n\n PROBATION END DATE: {probation_end_date} {type(probation_end_date)}\n\n")
                    
                    today_date = getdate()
                    days_remaining = (probation_end_date - today_date).days
                    
                    print(f"\n\n DAYS REMAINING: {days_remaining} {type(days_remaining)}\n\n")
                    if 0 <= days_remaining <= 15:
                            confirmation_eval_form = frappe.db.get_value("Employee", employee_id.get("name"), "custom_confirmation_evaluation_form")
                            try:
                                if not confirmation_eval_form:
                                    print(f"\n\n Creating Confirmation Evaluation Form \n\n")
                                    employee_doc = frappe.get_doc("Employee", employee_id.get("name"))
                                    confirmation_eval_doc = frappe.get_doc({
                                        "doctype": "Confirmation Evaluation Form",
                                        "employee": employee_id.get("name"),
                                        "evaluation_date": today(),
                                        "probation_status": "Pending",
                                    })
                                    
                                    category_list = ["Functional/ Technical Skills", "Behavioural Skills"]
                                    
                                    parameters_list = frappe.db.get_all("Confirmation Evaluation Parameter", {"category": ["in", category_list]}, ["name", "category"])
                                    
                                    for parameter in parameters_list:
                                        
                                        confirmation_eval_doc.append("table_txep", {
                                            "category": parameter.get("category"),
                                            "parameters": parameter.get("name"),
                                        })
                                    
                                    confirmation_eval_doc.insert(ignore_permissions=True)
                                    employee_doc.custom_confirmation_evaluation_form = confirmation_eval_doc.name
                                    employee_doc.save(ignore_permissions=True)
                                    frappe.db.commit()
                                    
                                    # frappe.db.set_value("Employee", employee_id.get("name"), "custom_confirmation_evaluation_form", confirmation_eval_doc.name)
                                    
                                    
                            except Exception as e:
                                frappe.log_error("Error while creating confirmation evaluation form", frappe.get_traceback())
                                
    except Exception as e:
        frappe.log_error("Error while creating confirmation evaluation form", frappe.get_traceback())
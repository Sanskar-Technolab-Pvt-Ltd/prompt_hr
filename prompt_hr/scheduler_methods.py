import frappe

import frappe.commands
from frappe.utils import date_diff, today, add_to_date, getdate, get_datetime

def create_probation_feedback_form():
    """Scheduler method to create probation feedback form based on the days after when employee joined mentioned in the HR Settings.
        - And Also notify the employee's reporting manager if the remarks are not added to the form.  
    """
    
    try:          
        
        probation_feedback_for_prompt()
        probation_feedback_for_indifoss()
                                                        
    except Exception as e:
        frappe.log_error("Error while creating probation feedback form", frappe.get_traceback())

#*CREATING PROBATION FEEDBACK FOR PROMPT EMPLOYEES
def probation_feedback_for_prompt():
    """Method to create probation feedback form for Prompt employees"""
    first_feedback_days = frappe.db.get_single_value("HR Settings", "custom_first_feedback_after")
    second_feedback_days = frappe.db.get_single_value("HR Settings", "custom_second_feedback_after")
    company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
    
    if company_abbr:
        if first_feedback_days or second_feedback_days:
            company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
            
            if company_id:
                # employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": "Prompt Equipments PVT LTD", "custom_probation_status": "Pending"}, "name")
                employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id, "custom_probation_status": "Pending"}, "name")
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
                                    
                                    
                                    question_list = frappe.db.get_all("Probation Question", {"company": company_id, "probation_feedback_for": "30 Days"}, "name")
                                    
                                    if question_list:
                                        
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
                                    
                                    
                                    question_list = frappe.db.get_all("Probation Question", {"company": company_id, "probation_feedback_for": "60 Days"}, "name")
                                    
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
            else:
                frappe.log_error("Issue while checking for probation feedback form for Prompt", f"No Company found for abbreviation {company_abbr}")
    else:
        frappe.log_error("Issue while check for probation feedback form for Prompt", "Please set abbreviation in HR Settings FOR Prompt")                                                
    

#*CREATING PROBATION FEEDBACK FOR INDIFOSS EMPLOYEES
def probation_feedback_for_indifoss():
    """Method to create probation feedback form for Indifoss employees"""
    
    first_feedback_days_for_indifoss = frappe.db.get_single_value("HR Settings", "custom_first_feedback_after_for_indifoss")
    second_feedback_days_for_indifoss = frappe.db.get_single_value("HR Settings", "custom_second_feedback_after_for_indifoss")
    confirmation_days_for_indifoss = frappe.db.get_single_value("HR Settings", "custom_release_confirmation_form_for_indifoss")
    
    company_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
    if company_abbr:
        
        if first_feedback_days_for_indifoss or second_feedback_days_for_indifoss or confirmation_days_for_indifoss:
            company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
            indifoss_employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id, "custom_probation_status": "Pending"}, "name")

            if indifoss_employees_list:
                for employee in indifoss_employees_list:
                    emp_joining_date = frappe.db.get_value("Employee", employee.get("name"), "date_of_joining")
                    
                    probation_feedback_form_id = frappe.db.get_value("Employee", employee.get("name"), "custom_probation_review_form") or None
                    if emp_joining_date:    
                        date_difference = date_diff(today(), emp_joining_date)
                        
                        if first_feedback_days_for_indifoss <= date_difference < second_feedback_days_for_indifoss:
                            
                            if not probation_feedback_form_id:
                                probation_form = frappe.get_doc({
                                    "doctype":"Probation Feedback Form",
                                    "employee": employee.get("name"),
                                    "evaluation_date": today()
                                })

                                general_sub_category_list = ["Common Parameters", "Communication", "Interpersonal Relationships and Interactions", "Commitment"]
                                
                                factor_category_general_list = frappe.db.get_all("Factor Category Parameters", {"parent_category": ["in", general_sub_category_list]}, ["name", "parent_category", "description"])
                                
                                if factor_category_general_list:
                                    for factor_category in factor_category_general_list:
                                        probation_form.append("probation_feedback_indifoss", {
                                            "category": "General",
                                            "sub_category": factor_category.get("parent_category"),
                                            "factor_category": factor_category.get("name"),
                                            "description_of_assessment_category": factor_category.get("description")
                                        })
                                
                                probation_form.insert(ignore_permissions=True)
                                if probation_form.name:
                                    print(f"\n\n {probation_form.name}\n\n")
                                    frappe.db.set_value("Employee", employee.get("name"), "custom_probation_review_form", probation_form.name)
                                
                                # if probation_form.reporting_manager:
                                #     reporting_manager_emp_id = probation_form.reporting_manager
                                #     if not reporting_manager_emp_id:
                                #         reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                #     reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")
                                    
                                #     if reporting_manager_user_id:
                                #         reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                #         if reporting_manager_email:
                                #             send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_form.name, employee.get("name"))
                                frappe.db.commit()
                            else:
                                remarks_added = frappe.db.exists("Probation Feedback IndiFOSS", {"parenttype": "Probation Feedback Form", "parent": probation_feedback_form_id, "45_days": ["not in", ['0', '']]})
                                
                                if not remarks_added:
                                    reporting_manager_emp_id = frappe.db.get_value("Probation Feedback Form", probation_feedback_form_id, "reporting_manager") or None
                                    
                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                        
                                    if reporting_manager_emp_id:
                                        reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id") or None
                                        
                                        if reporting_manager_user_id:
                                            reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_feedback_form_id, employee.get("name"))
                        
                        
                        if second_feedback_days_for_indifoss <= date_difference < confirmation_days_for_indifoss:
                            if not probation_feedback_form_id:
                                probation_form = frappe.get_doc({
                                    "doctype":"Probation Feedback Form",
                                    "employee": employee.get("name"),
                                    "evaluation_date": today()
                                })

                                general_sub_category_list = ["Common Parameters", "Communication", "Interpersonal Relationships and Interactions", "Commitment"]
                                
                                factor_category_general_list = frappe.db.get_all("Factor Category Parameters", {"parent_category": ["in", general_sub_category_list]}, ["name", "parent_category", "description"])
                                
                                if factor_category_general_list:
                                    for factor_category in factor_category_general_list:
                                        probation_form.append("probation_feedback_indifoss", {
                                            "category": "General",
                                            "sub_category": factor_category.get("parent_category"),
                                            "factor_category": factor_category.get("name"),
                                            "description_of_assessment_category": factor_category.get("description")
                                        })
                                
                                probation_form.insert(ignore_permissions=True)
                                if probation_form.name:
                                    frappe.db.set_value("Employee", employee.get("name"), "custom_probation_review_form", probation_form.name)
                                frappe.db.commit()
                                # if probation_form.reporting_manager:
                                #     reporting_manager_emp_id = probation_form.reporting_manager
                                #     if not reporting_manager_emp_id:
                                #         reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                #     reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")
                                    
                                #     if reporting_manager_user_id:
                                #         reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                #         if reporting_manager_email:
                                #             send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_form.name, employee.get("name"))

                            else:
                                remarks_added = frappe.db.exists("Probation Feedback IndiFOSS", {"parenttype": "Probation Feedback Form", "parent": probation_feedback_form_id, "90_days": ["not in", ['0', '']]})
                                
                                if not remarks_added:
                                    reporting_manager_emp_id = frappe.db.get_value("Probation Feedback Form", probation_feedback_form_id, "reporting_manager") or None
                                    
                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                        
                                    if reporting_manager_emp_id:
                                        reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id") or None
                                        
                                        if reporting_manager_user_id:
                                            reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_feedback_form_id, employee.get("name"))
                        
                        if confirmation_days_for_indifoss <= date_difference:
                            if not probation_feedback_form_id:
                                probation_form = frappe.get_doc({
                                    "doctype":"Probation Feedback Form",
                                    "employee": employee.get("name"),
                                    # "employee_name": employee.get("employee_name"),
                                    # "department": employee.get("department"),
                                    # "designation": employee.get("designation"),
                                    # "company": employee.get("company"),
                                    # "product_line": employee.get("custom_product_line"),
                                    # "business_unit": employee.get("custom_business_unit"),
                                    # "reporting_manager": employee.get("reports_to"),
                                    "evaluation_date": today()
                                })

                                general_sub_category_list = ["Common Parameters", "Communication", "Interpersonal Relationships and Interactions", "Commitment"]
                                
                                factor_category_general_list = frappe.db.get_all("Factor Category Parameters", {"parent_category": ["in", general_sub_category_list]}, ["name", "parent_category", "description"])
                                
                                if factor_category_general_list:
                                    for factor_category in factor_category_general_list:
                                        probation_form.append("probation_feedback_indifoss", {
                                            "category": "General",
                                            "sub_category": factor_category.get("parent_category"),
                                            "factor_category": factor_category.get("name"),
                                            "description_of_assessment_category": factor_category.get("description")
                                        })
                                
                                probation_form.insert(ignore_permissions=True)
                                if probation_form:
                                    frappe.db.set_value("Employee", employee.get("name"), "custom_probation_review_form", probation_form.name)
                                frappe.db.commit()
                                # if probation_form.reporting_manager:
                                #     reporting_manager_emp_id = probation_form.reporting_manager
                                #     if not reporting_manager_emp_id:
                                #         reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                #     reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")
                                    
                                #     if reporting_manager_user_id:
                                #         reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                #         if reporting_manager_email:
                                #             send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_form.name, employee.get("name"))
                            
                            else:
                                remarks_added = frappe.db.exists("Probation Feedback IndiFOSS", {"parenttype": "Probation Feedback Form", "parent": probation_feedback_form_id, "180_days": ["not in", ['0', '']]})
                                
                                if not remarks_added:
                                    reporting_manager_emp_id = frappe.db.get_value("Probation Feedback Form", probation_feedback_form_id, "reporting_manager") or None
                                    
                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                        
                                    if reporting_manager_emp_id:
                                        reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id") or None
                                        
                                        if reporting_manager_user_id:
                                            reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_feedback_form_id, employee.get("name"))

#*SENDING MAIL TO REPORTING MANAGER*
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



# * CREATING CONFIRMATION EVALUATION FORM AND IF ALREADY CREATED THEN, SENDING MAIL TO REPORTING MANAGER OR HEAD OF DEPARTMENT BASED ON THE RATING ADDED OR NOT
def create_confirmation_evaluation_form_for_prompt():
    try:
        
        company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
        create_cff_before_days = frappe.db.get_single_value("HR Settings", "custom_release_confirmation_form") or 15
        
        if company_abbr:
            company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
            if company_id:
                employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id, "custom_probation_status": "Pending"}, "name")
                
                if employees_list:
                    for employee_id in employees_list:
                        probation_days = frappe.db.get_value("Employee", employee_id.get("name"), "custom_probation_period")
                        
                        if probation_days:
                            
                            joining_date = frappe.db.get_value("Employee", employee_id.get("name"), "date_of_joining")
                            
                            probation_end_date = getdate(add_to_date(joining_date, days=probation_days))
                            
                            today_date = getdate()
                            days_remaining = (probation_end_date - today_date).days
                            
                            
                            if 0 <= days_remaining <= create_cff_before_days:
                                    confirmation_eval_form = frappe.db.get_value("Employee", employee_id.get("name"), "custom_confirmation_evaluation_form")
                                    try:
                                        if not confirmation_eval_form:
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
                                        elif confirmation_eval_form:
                                            
                                            confirmation_eval_form_doc = frappe.get_doc("Confirmation Evaluation Form", confirmation_eval_form)
                                            
                                            rh_rating_added = confirmation_eval_form_doc.rh_rating_added
                                            dh_rating_added = confirmation_eval_form_doc.dh_rating_added
                                            context = {
                                                "doc": confirmation_eval_form_doc,
                                                "doctype": "Confirmation Evaluation Form",
                                                "docname": confirmation_eval_form_doc.name,}
                                            notification_template = frappe.get_doc("Notification", "Confirmation Evaluation Form Remarks Reminder")
                                            subject = frappe.render_template(notification_template.subject, context)
                                            message = frappe.render_template(notification_template.message, context)
                                            
                                            if not rh_rating_added:
                                                reporting_head = confirmation_eval_form_doc.reporting_manager
                                                reporting_head_user_id = frappe.db.get_value("Employee", reporting_head, "user_id") if reporting_head else None
                                                reporting_head_email = frappe.db.get_value("User", reporting_head_user_id, "email") if reporting_head_user_id else None
                                                
                                                if reporting_head_email:
                                                    
                                                    try:
                                                        frappe.sendmail(
                                                            recipients=[reporting_head_email],
                                                            subject=subject,
                                                            message=message,
                                                            reference_doctype="Confirmation Evaluation Form",
                                                            reference_name=confirmation_eval_form_doc.name,
                                                            now=True
                                                        )
                                                    except Exception as e:
                                                        frappe.log_error("Error while sending confirmation evaluation form reminder mail", frappe.get_traceback())
                                                    
                                                
                                            elif rh_rating_added and not dh_rating_added:
                                                
                                                head_of_department = confirmation_eval_form_doc.hod
                                                head_of_department_employee = frappe.db.get_value("Employee", head_of_department, "user_id") if head_of_department else None
                                                head_of_department_email = frappe.db.get_value("User", head_of_department_employee, "email") if head_of_department_employee else None
                                                
                                                if head_of_department_email:
                                                    frappe.sendmail(
                                                        recipients=[head_of_department_email],
                                                        subject=subject,
                                                        message=message,
                                                        reference_doctype="Confirmation Evaluation Form",
                                                        reference_name=confirmation_eval_form_doc.name,
                                                        now=True
                                                    )                                                                                                        
                                    except Exception as e:
                                        frappe.log_error("Error while creating confirmation evaluation form", frappe.get_traceback())
                                        
            else:
                frappe.log_error("Issue while creating confirmation form for prompt", f"Company Not found for abbreviation {company_abbr}")                            
        else:
            frappe.log_error("Issue while creating confirmation form for prompt", "Company abbreviation Not Found Please Set Company abbreviation for Prompt in HR Settings")                            
    except Exception as e:
        frappe.log_error("Error while creating confirmation evaluation form", frappe.get_traceback())
        
def inform_employee_for_confirmation_process():
    """ Method to inform employee about confirmation process  before the days set user in HR Settings probation period is over 
    """
    try:
        
        company_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
        company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id, "custom_probation_status": "Pending"}, "name")
        
        inform_days_before_confirmation = frappe.db.get_single_value("HR Settings", "custom_inform_employees_probation_end_for_indifoss")
        if inform_days_before_confirmation:
            final_inform_days = -abs(inform_days_before_confirmation)
        else:
            final_inform_days = -5
        if employee_list:
            
            for employee in employee_list:
                employee_doc = frappe.get_doc("Employee", employee.get("name"))
                probation_period = employee_doc.custom_probation_period or 0 + employee_doc.custom_extended_period or 0
                
                if probation_period:
                    joining_date = employee_doc.date_of_joining
                    if joining_date:
                        
                        probation_end_date = add_to_date(joining_date, days=probation_period)
                        if probation_end_date:
                            five_days_before_date = add_to_date(probation_end_date, days= final_inform_days, as_string=True)
                            if five_days_before_date and five_days_before_date == today():
                                
                                employee_email = frappe.db.get_value("User", employee_doc.user_id, "email") if employee_doc.user_id else None
                                
                                if employee_email:
                                    notification_template = frappe.get_doc("Notification", "Inform Employee about Confirmation Process")
                                    if notification_template:
                                        subject = frappe.render_template(notification_template.subject, {"doc": employee_doc})
                                        message = frappe.render_template(notification_template.message, {"doc": employee_doc})
                                
                                        frappe.sendmail(
                                            recipients=[employee_email],
                                            subject=subject,
                                            message=message,
                                            now=True    
                                        )
                                    else:
                                        frappe.sendmail(
                                            recipients=[employee_email],
                                            subject="Confirmation Process Reminder",
                                            message=f"Dear {employee_doc.employee_name or 'Employee'}, your probation period is ending soon. Please check with your reporting manager for the confirmation process.",
                                            now=True    
                                        )
    except Exception as e:
        frappe.log_error("Error while sending confirmation process reminder email", frappe.get_traceback())
        
def validate_employee_holiday_list():
    """ checking if are there any weeklyoff assignment or not if there are then assigning them based on from and to date and updating employee holiday list if required
    """
    try:
        employee_list = frappe.db.get_all("Employee",{"status": "Active"}, "name")
        
        if not employee_list:
            frappe.log_error("No Employee Found", "No Employees are found to check for weeklyoff assignment")
        
        today_date = getdate(today())
        
        for employee_id in employee_list:
            weeklyoff_assignment_id = frappe.db.exists("WeeklyOff Assignment", {"employee": employee_id.get("name")}, "name")
            
            if weeklyoff_assignment_id:
                weeklyoff_assignment_doc = frappe.get_doc("WeeklyOff Assignment", weeklyoff_assignment_id)
                
                if not weeklyoff_assignment_doc:
                    frappe.log_error("Not able to fetch Weekoff assignment",  f"Weekoff Assignment not found {weeklyoff_assignment_id}")
                start_date = weeklyoff_assignment_doc.start_date
                end_date = weeklyoff_assignment_doc.end_date
                
                employee_doc = frappe.get_doc("Employee", employee_id)
                
                if (start_date and end_date) and (start_date <= today_date <= end_date):
                    # * SETTING NEW WEEKLYOFF TYPE FOR EMPLOYEE IF THE CURRENT DATE IS WITHIN THE WEEKOFF ASSIGNMENT PERIOD
                    if weeklyoff_assignment_doc.new_weeklyoff_type != employee_doc.custom_weeklyoff:
                        employee_doc.custom_weeklyoff = weeklyoff_assignment_doc.new_weeklyoff_type
                        employee_doc.save(ignore_permissions=True)
                        frappe.db.commit()

                elif not end_date and (start_date and start_date <= today_date):
                    # * PERMANENTLY SETTING NEW WEEKLYOFF TYPE FOR EMPLOYEE IF END DATE IS NOT DEFINED
                    if weeklyoff_assignment_doc.new_weeklyoff_type != employee_doc.custom_weeklyoff:
                        employee_doc.custom_weeklyoff = weeklyoff_assignment_doc.new_weeklyoff_type
                        employee_doc.save(ignore_permissions=True)
                        frappe.db.commit()

                
                elif end_date and end_date < today_date:
                    # * SETTING BACK THE OLD WEEKLYOFF TYPE ONCE THE WEEKOFF ASSIGNMENT PERIOD IS OVER
                    if weeklyoff_assignment_doc.old_weeklyoff_type != employee_doc.custom_weeklyoff:
                        employee_doc.custom_weeklyoff = weeklyoff_assignment_doc.old_weeklyoff_type
                        employee_doc.save(ignore_permissions=True)
                        frappe.db.commit()
                    
                
        
    except Exception as e:
        frappe.log_error("Error while checking for weeklyoff assignment", frappe.get_traceback())


@frappe.whitelist()
def generate_attendance():
    """Generate Employee Attendance and Check the weekoff 
    """
    try:
        employee_list = frappe.db.get_all("Employee", {"status": "Active"}, "name")
        
        yesterday_date = add_to_date(days=-1, as_string=True)
        
        start = get_datetime(yesterday_date + " 00:00:00")
        end = get_datetime(yesterday_date + " 23:59:59")
        if employee_list:
            for employee_id in employee_list:
                emp_check_in = frappe.db.get_all("Employee Checkin", {"employee": employee_id.get("name"), "log_type": "IN", "time": ["between", [start, end]]}, "name", group_by="time asc")
                print(f"\n\n {emp_check_in} \n\n")
        
    except Exception as e:
        frappe.log_error("Error While Generating Attendance", frappe.get_traceback())
    
    
    
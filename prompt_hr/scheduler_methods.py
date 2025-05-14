import frappe

import frappe.commands
from frappe.utils import date_diff, today, add_to_date, getdate, get_datetime, add_months
from prompt_hr.py.utils import fetch_company_name
from datetime import timedelta, datetime


@frappe.whitelist()
def create_probation_feedback_form():
    """Scheduler method to create probation feedback form based on the days after when employee joined mentioned in the HR Settings.
        - And Also notify the employee's reporting manager if the remarks are not added to the form.  
    """
    
    try:          
        print("aaaa\n\n\n\n")
        probation_feedback_for_prompt()
        probation_feedback_for_indifoss()
                                                        
    except Exception as e:
        frappe.log_error("Error while creating probation feedback form", frappe.get_traceback())

#*CREATING PROBATION FEEDBACK FOR PROMPT EMPLOYEES
def probation_feedback_for_prompt():
    """Method to create probation feedback form for Prompt employees"""
    print("jsfdjsfdndksfdnsfdnknsfd\n\n\n\n")
    first_feedback_days = frappe.db.get_single_value("HR Settings", "custom_first_feedback_after")
    second_feedback_days = frappe.db.get_single_value("HR Settings", "custom_second_feedback_after")
    company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
    
    if company_abbr:
        if first_feedback_days or second_feedback_days:
            company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
            
            if company_id:
                # employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": "Prompt Equipments PVT LTD", "custom_probation_status": "Pending"}, "name")
                employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id, "custom_probation_status": "Pending"}, "name")
                print(f"\n\n\n\n\n\n\n\n\n\n {employees_list} \n\n\n\n")
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
@frappe.whitelist()
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
    
@frappe.whitelist()
def validate_employee_holiday_list():
    """ checking if are there any weeklyoff assignment or not if there are then assigning them based on from and to date and updating employee holiday list if required
    """
    try:
        employee_list = frappe.db.get_all("Employee",{"status": "Active"}, "name")
        
        if not employee_list:
            frappe.log_error("No Employee Found", "No Employees are found to check for weeklyoff assignment")
        
        today_date = getdate(today())
        
        for employee_id in employee_list:
            weeklyoff_assignment_list = frappe.db.get_all("WeeklyOff Assignment", {"employee": employee_id.get("name"), "docstatus": 1}, "name")
            
            if weeklyoff_assignment_list:
                
                for weeklyoff_assignment_id in weeklyoff_assignment_list:
                    weeklyoff_assignment_doc = frappe.get_doc("WeeklyOff Assignment", weeklyoff_assignment_id.get("name"))
                    
                    if not weeklyoff_assignment_doc:
                        frappe.log_error("Not able to fetch Weekoff assignment",  f"Weekoff Assignment not found {weeklyoff_assignment_id}")
                        
                    if weeklyoff_assignment_doc.start_date <= today_date:
                        start_date = weeklyoff_assignment_doc.start_date
                        end_date = weeklyoff_assignment_doc.end_date
                        
                        employee_doc = frappe.get_doc("Employee", employee_id.get("name"))
                        
                        if (start_date and end_date) and (start_date <= today_date < end_date):
                            # * SETTING NEW WEEKLYOFF TYPE FOR EMPLOYEE IF THE CURRENT DATE IS WITHIN THE WEEKOFF ASSIGNMENT PERIOD
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
                                
                        elif not end_date and (start_date and start_date <= today_date):
                            # * PERMANENTLY SETTING NEW WEEKLYOFF TYPE FOR EMPLOYEE IF END DATE IS NOT DEFINED
                            if weeklyoff_assignment_doc.new_weeklyoff_type != employee_doc.custom_weeklyoff:
                                frappe.db.set_value("WeeklyOff Assignment", {"employee": employee_id.get("name")}, "old_weeklyoff_type", weeklyoff_assignment_doc.new_weeklyoff_type)
                                employee_doc.custom_weeklyoff = weeklyoff_assignment_doc.new_weeklyoff_type
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()

                
                
                    
                
        
    except Exception as e:
        frappe.log_error("Error while checking for weeklyoff assignment", frappe.get_traceback())


@frappe.whitelist()
def assign_checkin_role():
    """ Method to assign create checkin role to the employee if that employee has attendance request and the current date falls within the from and to date of that attendance request
    """
    
    try:
        
        today_date = getdate(today())
        checkin_role = "Create Checkin"
        attendance_request_list = frappe.db.get_all("Attendance Request", {"docstatus": 1, "custom_status": "Approved", "from_date": ["<=", today_date], "to_date": [">=", today_date]}, ["name", "employee"])
        
        valid_users = set()
        
        if attendance_request_list:
            for attendance_request_data in attendance_request_list:
                emp_user_id = frappe.db.get_value("Employee", attendance_request_data.get("employee"), "user_id")
                valid_users.add(emp_user_id)
                if not user_has_role(emp_user_id, checkin_role):
                    user_doc = frappe.get_doc("User", emp_user_id)
                    user_doc.append("roles",{
                        "role": checkin_role
                    })
                    user_doc.save(ignore_permissions=True)
            
            frappe.db.commit()
        
        # * REMOVING CHECKIN ROLE IF THE USER IS NOT QUALIFIED
        all_employee_list = frappe.db.get_all("Employee", {"status": "Active", "user_id": ["is", "set"]}, ["name", "user_id"])
        
        if all_employee_list:
            print(f"\n\n all employee list {all_employee_list} \n\n")
            for employee_id in all_employee_list:
                
                if employee_id.get("user_id") and user_has_role(employee_id.get("user_id"), checkin_role):
                    # frappe.remove_role(employee_id.get("user_id", checkin_role))
                    user_doc = frappe.get_doc("User", employee_id.get("user_id"))
                    
                    for role in user_doc.get("roles"):
                        if role.role == checkin_role:
                            user_doc.remove(role)
                            break
                    
                    user_doc.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error("Error in assign_checkin_role scheduler method", frappe.get_traceback())
        


def user_has_role(user, role):
    """Method to check if the user has the given role or not
    """
    return frappe.db.exists("Has Role", {"parent": user, "role": role})



@frappe.whitelist()
def penalize_employee_for_late_entry_for_indifoss():
    """Method to check if the employee is late and the penalization criteria is satisfied then give penalty to employee
    """
    try:
        
        
        allowed_late_entries = frappe.db.get_single_value("HR Settings", "custom_late_coming_allowed_per_month_for_indifoss")
        
        
        
        if allowed_late_entries:
        
            company_id = fetch_company_name(indifoss=1)
            
            if company_id.get("error"):
                frappe.log_error("Error in penalize_employee_for_late_entry", frappe
                                .get_traceback())
            
            if not company_id.get("error") and company_id.get("company_id"):
                indifoss_employee_list = frappe.db.get_all("Employee", {"status":"Active", "company": company_id.get("company_id")}, "name")
                
                if indifoss_employee_list:
                    
                    today_date = getdate(today())
                                    
                    month_first_date = today_date.replace(day=1)
        
                    next_month = add_months(month_first_date, 1)
            
                    month_last_date = next_month - timedelta(days=1)
                    
                    days_diff_from_month_first_date = date_diff(today_date, month_first_date)

                    for emp_id in indifoss_employee_list:
                        
                        late_attendance_list = frappe.db.get_all("Attendance", {"docstatus": 1, "employee": emp_id.get("name"), "attendance_date": ["between", [month_first_date, month_last_date]], "late_entry":1}, ["name", "attendance_date"], order_by="attendance_date asc")
                    
                        if late_attendance_list:
                            for attendance_id in late_attendance_list[allowed_late_entries:]:
                                if not frappe.db.exists("Leave Application", {"employee": emp_id.get("name"), "from_date": attendance_id.get("attendance_date")}):
                                        create_leave_application(emp_id.get("name"), attendance_id.get("attendance_date"), attendance_id.get("name"))
            else:
                if not company_id.get("company_id"):
                    frappe.log_error("Error in penalize_employee_for_later_entry", "Company ID not found")
    except Exception as e:
        frappe.log_error("Error in penalize_employee_for_late_entry", frappe.get_traceback())

@frappe.whitelist() 
def penalize_incomplete_week_for_indifoss():
    """Method to apply penalty if the employee has not completed the weekly hours
    """
    try:
        
        company_id = fetch_company_name(indifoss=1)
        today_date = getdate(today())
        
        if company_id.get("error"):
            frappe.log_error("Error in penalize_incomplete_week scheduler", frappe.get_traceback())
        
        employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id.get("company_id")}, ["name","custom_last_weekly_hours_evaluation", "custom_next_weekly_hours_evaluation", "custom_weeklyoff"])

        if employee_list:
            for emp in employee_list:
                weekly_off_type = emp.get("custom_weeklyoff")
                
                if weekly_off_type:
                    weekly_off_days = get_week_off_days(emp.get("custom_weeklyoff"))
                    print(f"\n\n weekly off days {emp.get('name')} {weekly_off_days} {type(weekly_off_days)}\n\n")
                    if weekly_off_days:
                        num_weekoffs = len(weekly_off_days)
                        expected_work_hours = 7 - num_weekoffs
                        
                        if emp.get("custom_next_weekly_hours_evaluation") and getdate(emp.get("custom_next_weekly_hours_evaluation")) > today_date:
                            pass
                        
                        if emp.get("custom_last_weekly_hours_evaluation"):
                            pass
                        else:
                            pass
                
    except Exception as e:
        frappe.log_error("Error in penalize_incomplete_week scheduler", frappe.get_traceback())
        
        
def get_week_off_days(weekly_off_type):
    print(f"\n\n weekly_off_type {weekly_off_type} \n\n")
    days = frappe.db.get_all("WeekOff Multiselect", {"parenttype": "WeeklyOff Type", "parent": weekly_off_type}, "weekoff", pluck="weekoff")
    return days or []
    
def create_leave_application(emp_id, leave_date, attendance_id):
    """Method to create leave application
    """
    try:
        leave_type = frappe.db.get_single_value("HR Settings", "custom_leave_type_for_indifoss")
        deduction_of_leave = frappe.db.get_single_value("HR Settings", "custom_deduction_of_leave_for_indifoss")
        
        rh_employee = frappe.db.get_value("Employee", emp_id, "reports_to")

        leave_application_doc = frappe.new_doc("Leave Application") 
        
        leave_application_doc.employee = emp_id
        leave_application_doc.leave_type = leave_type
        leave_application_doc.from_date = leave_date
        leave_application_doc.to_date = leave_date
        leave_application_doc.custom_is_penalty_leave = 1

        # if rh_employee:   
        #     if rh_employee:
        #         rh_emp_id = frappe.db.get_value("Employee", rh_employee, "user_id")
        #         leave_application_doc.leave_approver = rh_emp_id

        if deduction_of_leave == "Half day":
            leave_application_doc.half_day = 1
        
        leave_application_doc.description = f"Late Entry Penalization for Attendance - {attendance_id}"
        leave_application_doc.status = "Approved"
        leave_application_doc.insert(ignore_permissions=True)
        leave_application_doc.submit()
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("Error while creating leave application", frappe.get_traceback())

# @frappe.whitelist()
# def generate_attendance():
#     """Generate Employee Attendance and Check the weekoff 
#     """
#     try:
#         employee_list = frappe.db.get_all("Employee", {"status": "Active"}, "name")
        
#         yesterday_date = add_to_date(days=-1, as_string=True)
        
#         start = get_datetime(yesterday_date + " 00:00:00")
#         end = get_datetime(yesterday_date + " 23:59:59")
#         if employee_list:
#             for employee_id in employee_list:
#                 emp_check_in = frappe.db.get_all("Employee Checkin", {"employee": employee_id.get("name"), "log_type": "IN", "time": ["between", [start, end]]}, "name", group_by="time asc")
#                 print(f"\n\n {emp_check_in} \n\n")
        
#     except Exception as e:
#         frappe.log_error("Error While Generating Attendance", frappe.get_traceback())
    
# @frappe.whitelist()
# def allow_checkin_from_website_to_employee():
#     """Method to check if the current date is between the from and to date of attendance request then allow the employee to checkin from website for the time period
#     """
#     try:
#         attendance_request = frappe.db.get_all("Attendance Request", {"docstatus": 1, "custom_status": "Approved"})
#     except Exception as e:
#         frappe.log_error("Error in allow_checkin_from_website_to_employee schedular method", frappe.get_traceback())

import frappe

import frappe.commands
from frappe.utils import date_diff, today, add_to_date, getdate, get_datetime, add_months, add_days
from prompt_hr.py.utils import fetch_company_name
from prompt_hr.py.auto_mark_attendance import mark_attendance, is_holiday_or_weekoff
from datetime import timedelta, datetime
from prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process import (
    raise_exit_checklist,
    raise_exit_interview,
)
from datetime import datetime, timedelta


@frappe.whitelist()
def auto_attendance():
    mark_attendance(is_scheduler=1)

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
        FOR INDIFOSS
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
        
        print(f"\n\n attendance request list {attendance_request_list} \n\n")
        
        valid_users = set()
        
        if attendance_request_list:
            for attendance_request_data in attendance_request_list:
                emp_user_id = frappe.db.get_value("Employee", attendance_request_data.get("employee"), "user_id")
                valid_users.add(emp_user_id)
                if not user_has_role(emp_user_id, checkin_role):
                    print(f"\n\n applying checkin role {emp_user_id} \n\n")
                    user_doc = frappe.get_doc("User", emp_user_id)
                    user_doc.append("roles",{
                        "role": checkin_role
                    })
                    user_doc.save(ignore_permissions=True)
            
            frappe.db.commit()
        print(f"\n\n valid users {valid_users} \n\n")
        # * REMOVING CHECKIN ROLE IF THE USER IS NOT QUALIFIED
        all_employee_list = frappe.db.get_all("Employee", {"status": "Active", "user_id": ["is", "set"]}, ["name", "user_id"])
        
        if all_employee_list:
            print(f"\n\n all employee list {all_employee_list} \n\n")
            for employee_id in all_employee_list:
                
                if employee_id.get("user_id") and employee_id.get("user_id") not in valid_users and user_has_role(employee_id.get("user_id"), checkin_role):
                    # frappe.remove_role(employee_id.get("user_id", checkin_role))
                    user_doc = frappe.get_doc("User", employee_id.get("user_id"))
                    
                    for role in user_doc.get("roles"):
                        if role.role == checkin_role :
                            print(f"\n\n removing checkin role {employee_id.get('user_id')} \n\n")
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
    
    #* TO BE ADDED IN HOOKS
    try:
        allowed_late_entries = frappe.db.get_single_value("HR Settings", "custom_late_coming_allowed_per_month_for_indifoss")
        late_entry_leave_type = frappe.db.get_single_value("HR Settings", "custom_leave_type_for_indifoss")
        late_entry_leave_deduction = frappe.db.get_single_value("HR Settings", "custom_deduction_of_leave_for_indifoss")
        is_lwp_for_late_entry = 1 if frappe.db.get_single_value("HR Settings", "custom_deduct_leave_penalty_for_indifoss") == "Deduct leave without pay" else 0
        
        late_entry_deduct_leave = 0.5 if late_entry_leave_deduction == "Half day" else 1.0
        
        
        
        if not allowed_late_entries:
            allowed_late_entries = 0
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
                # days_diff_from_month_first_date = date_diff(today_date, month_first_date)

                leave_period_data = frappe.db.get_value("Leave Period", {"is_active": 1, "company": company_id.get("company_id")}, ["name", "from_date", "to_date"], as_dict=True)
                
                
                for emp_id in indifoss_employee_list:
                    if (not check_employee_penalty_criteria(emp_id.get("name"), "For Late Arrival")):
                        return
                    print("penalize_employee_for_late_entry_for_indifoss",emp_id.get('name'))
                    remaining_leave_balance_for_late_entry = 0.0
                    leave_allocation_id = None
                    
                    if not is_lwp_for_late_entry:
                        
                        remaining_leave_balance_for_late_entry = get_remaining_leaves(late_entry_leave_type, emp_id.get("name"), company_id)
                        
                        
                                    
                        if not remaining_leave_balance_for_late_entry > 0:
                            earned_leave = 0.0
                            lwp_leave = late_entry_deduct_leave
                            
                        else:
                            if remaining_leave_balance_for_late_entry >= late_entry_deduct_leave:
                                earned_leave = late_entry_deduct_leave
                                lwp_leave = 0.0
                                
                            else:
                                earned_leave = remaining_leave_balance_for_late_entry
                                lwp_leave = late_entry_deduct_leave - remaining_leave_balance_for_late_entry                
                            leave_allocation_id = frappe.db.get_value("Leave Allocation", {"employee": emp_id.get("name"), "leave_type": late_entry_leave_type, "docstatus": 1}, "name")
                    else:
                        earned_leave = 0.0
                        lwp_leave = late_entry_deduct_leave
                        
                    
                    
                    late_attendance_list = frappe.db.get_all("Attendance", {"docstatus": 1, "employee": emp_id.get("name"), "attendance_date": ["between", [month_first_date, month_last_date]], "late_entry":1, "custom_apply_penalty": 1}, ["name", "attendance_date"], order_by="attendance_date asc")
                
                    if late_attendance_list:
                        for attendance_id in late_attendance_list[allowed_late_entries:]:
                            
                            leave_application_exists = frappe.db.exists("Leave Application", {"employee": emp_id.get("name"), "docstatus": 1,"from_date": ["<=",attendance_id.get("attendance_date")], "to_date": [">=",attendance_id.get("attendance_date")]})
                            
                            attendance_regularization_exists = frappe.db.get_all("Attendance Regularization", {"employee": emp_id.get("name"), "attendance": attendance_id.get("name"),"regularization_date": attendance_id.get("attendance_date")}, "name")
                            
                            employee_late_penalty_exists = frappe.db.exists("Employee Penalty", {"employee": emp_id.get("name"), "attendance": attendance_id.get("name"), "for_late_coming": 1})
                            
                            if not (leave_application_exists or attendance_regularization_exists or employee_late_penalty_exists):
                                create_employee_penalty(
                                                            emp_id.get("name"), 
                                                            attendance_id.get("attendance_date"), 
                                                            late_entry_deduct_leave, 
                                                            attendance_id=attendance_id.get("name"), 
                                                            leave_type=late_entry_leave_type,
                                                            leave_balance_before_application=remaining_leave_balance_for_late_entry, 
                                                            leave_period_data=leave_period_data, 
                                                            earned_leave=earned_leave, 
                                                            lwp_leave=lwp_leave,
                                                            leave_allocation_id = leave_allocation_id,  
                                                            is_lwp_for_late_entry = is_lwp_for_late_entry,
                                                            for_late_coming=1
                                                        )
        else:
            if not company_id.get("company_id"):
                frappe.log_error("Error in penalize_employee_for_later_entry", "Company ID not found")
    except Exception as e:
        frappe.log_error("Error in penalize_employee_for_late_entry", frappe.get_traceback())

@frappe.whitelist() 
def penalize_incomplete_week_for_indifoss():
    """Method to apply penalty if the employee has not completed the weekly hours
    """
    #* TO BE ADDED IN HOOKS
    try:
        
        company_id = fetch_company_name(indifoss=1)
        today_date = getdate(today())
        
        expected_work_hours = frappe.db.get_single_value("HR Settings", "custom_weekly_hours_criteria_for_penalty_for_indifoss")
        
        weekly_hours_leave_type = frappe.db.get_single_value("HR Settings", "custom_leave_type_weekly_for_indifoss")
        weekly_hours_leave_deduction = frappe.db.get_single_value("HR Settings", "custom_deduction_of_leave_weekly_for_indifoss")
        
        insufficient_hours_deduct_leave = 0.5 if weekly_hours_leave_deduction == "Half day" else 1.0
        
        
        is_lwp_for_insufficient_hours = 1 if frappe.db.get_single_value("HR Settings", "custom_deduct_leave_penalty_weekly_for_indifoss") == "Deduct leave without pay" else 0
        
        
        if company_id.get("error"):
            frappe.log_error("Error in penalize_incomplete_week scheduler", frappe.get_traceback())
        
        employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id.get("company_id")}, ["name","custom_last_weekly_hours_evaluation", "custom_next_weekly_hours_evaluation", "custom_weeklyoff"])

        
        if employee_list:
            for emp in employee_list:
                if (not check_employee_penalty_criteria(emp.get("name"), "For Work Hours")):
                    return
                print("penalize_incomplete_week_for_indifoss", emp.get("name"))
                remaining_leave_balance = 0.0
                leave_allocation_id = None
                    
                if not is_lwp_for_insufficient_hours:
                        
                        print(f"\n\n leave type {weekly_hours_leave_type} {emp.get('name')} {company_id}\n\n")
                        remaining_leave_balance = get_remaining_leaves(weekly_hours_leave_type, emp.get("name"), company_id.get("company_id"))
                                    
                        print(f"\n\n remaining  {remaining_leave_balance}\n\n")
                        
                        if not remaining_leave_balance > 0:
                            earned_leave = 0.0
                            lwp_leave = insufficient_hours_deduct_leave
                            
                        else:
                            if remaining_leave_balance >= insufficient_hours_deduct_leave:
                                earned_leave = insufficient_hours_deduct_leave
                                lwp_leave = 0.0
                                
                            else:
                                earned_leave = remaining_leave_balance
                                lwp_leave = insufficient_hours_deduct_leave - remaining_leave_balance                
                            leave_allocation_id = frappe.db.get_value("Leave Allocation", {"employee": emp.get("name"), "leave_type": weekly_hours_leave_type, "docstatus": 1}, "name")
                            print(f"\n\n leave allocation {leave_allocation_id}\n\n")
                else:   
                    earned_leave = 0.0
                    lwp_leave = insufficient_hours_deduct_leave
                
                
                leave_period_data = frappe.db.get_value("Leave Period", {"is_active": 1, "company": company_id.get("company_id")}, ["name", "from_date", "to_date"], as_dict=True)
                
                weekly_off_type = emp.get("custom_weeklyoff")
                
                
                if weekly_off_type:
                    weekly_off_days = get_week_off_days(emp.get("custom_weeklyoff"))
                    if weekly_off_days:
                        num_weekoffs = len(weekly_off_days)
                        expected_work_days = 7 - num_weekoffs
                        if emp.get("custom_next_weekly_hours_evaluation") and getdate(emp.get("custom_next_weekly_hours_evaluation")) != today_date:
                            continue
                        
                        
                        if emp.get("custom_last_weekly_hours_evaluation"):
                            eval_start, eval_end = get_next_work_week(emp.get("custom_last_weekly_hours_evaluation"), weekly_off_days, expected_work_days)
                        else:
                            eval_start, eval_end = get_last_full_work_week(today_date, weekly_off_days, expected_work_days)
                        
                        leave_application_list = frappe.db.get_all("Leave Application", {"employee": emp.get("name"), "status": "Approved", "from_date":["between", [eval_start, eval_end]]}, ["name", "half_day"])
                        
                        print(f"\n\n {eval_start} {eval_end} \n\n")
                        leave_hours = 0.0
                        if leave_application_list:
                            
                            full_day_leave_hours = 9
                            half_day_leave_hours = 4.5

                            for leave in leave_application_list:
                                if leave.get("half_day") == 1:
                                    leave_hours += half_day_leave_hours
                                else:
                                    leave_hours += full_day_leave_hours
                        
                        emp_holiday_list = frappe.db.get_value("Employee", emp.get("name"), "holiday_list")
                        if emp_holiday_list:
                            holiday_count = frappe.db.count("Holiday", {"parenttype": "Holiday List", "parent": emp_holiday_list, "holiday_date": ["between", [eval_start, eval_end]]})
                            leave_hours += holiday_count * 9
                        
                        
                        working_days = get_working_days(eval_start, eval_end, weekly_off_days)
                        total_hours = get_total_working_hours(emp.name, working_days)
                        
                        if leave_hours:
                            expected_work_hours -= leave_hours
                            
                        if total_hours < expected_work_hours:
                            attendance_id = frappe.db.get_all("Attendance", {"employee": emp.get("name"), "attendance_date": ["between", [eval_start, eval_end]], "status": ["in", ["Present", "Work From Home", "Half Day"]]}, ["name", "attendance_date"], order_by="attendance_date desc", limit=1)
                            
                            if attendance_id:
                                
                                leave_application_exists = frappe.db.exists("Leave Application", {"employee": emp.get("name"), "docstatus": 1, "from_date": ["<=",attendance_id[0].get("attendance_date")], "to_date": [">=",attendance_id[0].get("attendance_date")]})
                
                                attendance_regularization_exists = frappe.db.get_all("Attendance Regularization", {"employee": emp.get("name"), "attendance": attendance_id[0].get("name"),"regularization_date": attendance_id[0].get("attendance_date")}, "name")
                
                                employee_late_penalty_exists = frappe.db.exists("Employee Penalty", {"employee": emp.get("name"), "attendance": attendance_id[0].get("name"), "for_insufficient_hours": 1})
                                
                                # if not frappe.db.exists("Leave Application", {"employee": emp.get("name"), "from_date": attendance_id[0]}):
                                if not (leave_application_exists or attendance_regularization_exists or employee_late_penalty_exists):
                                    print(f"\n\n Creating Penalty \n\n")
                                    create_employee_penalty(
                                                emp.get("name"), 
                                                eval_end,
                                                insufficient_hours_deduct_leave, 
                                                attendance_id=attendance_id[0].get("name"), 
                                                leave_type=weekly_hours_leave_type, 
                                                leave_balance_before_application=remaining_leave_balance, 
                                                leave_period_data=leave_period_data, 
                                                earned_leave=earned_leave, 
                                                lwp_leave=lwp_leave, 
                                                leave_allocation_id=leave_allocation_id,  
                                                is_lwp_for_insufficient_hours = is_lwp_for_insufficient_hours, 
                                                for_insufficient_hours=1
                                            )
                                    
                                    
                                    
                                    # create_leave_application(emp.get("name"), eval_end, attendance_id[0], for_time_penalization=1, indifoss=1) 
                        last_update_date = get_next_working_day_after_weekoffs(eval_end + timedelta(days=1), weekly_off_days)
                        next_update_date = get_next_working_day_after_weekoffs(last_update_date + timedelta(days=7), weekly_off_days)
                        
                        frappe.db.set_value("Employee", emp.get("name"), "custom_last_weekly_hours_evaluation", last_update_date)
                        frappe.db.set_value("Employee", emp.get("name"), "custom_next_weekly_hours_evaluation", next_update_date)
                        
                        
                        
                            
    except Exception as e:
        frappe.log_error("Error in penalize_incomplete_week scheduler", frappe.get_traceback())




@frappe.whitelist()
def penalize_prompt_employee():
    """Method to to check for late coming or daily hours criteria and apply penalty
    """
    
    try:
        # * TO BE ADDED IN HOOKS
        hr_settings_doc = frappe.get_doc("HR Settings")
        allowed_late_entries = hr_settings_doc.custom_late_coming_allowed_per_month_for_prompt
        
        #* FOR LATE COMING
        late_entry_leave_type = hr_settings_doc.custom_leave_type_for_prompt
        late_entry_leave_deduction = hr_settings_doc.custom_deduction_of_leave_for_prompt
        is_lwp_for_late_entry = 1 if hr_settings_doc.custom_deduct_leave_penalty_for_prompt == "Deduct leave without pay" else 0
        
        
        late_entry_deduct_leave = 0.5 if late_entry_leave_deduction == "Half day" else 1.0
        
        leave_penalty_buffer_days = hr_settings_doc.custom_buffer_period_for_leave_penalty_for_prompt
        
        #* GETTING DATE TO CHECK THE ATTENDANCE FOR THAT DATE FOR LATE COMING
        if leave_penalty_buffer_days:    
                leave_penalty_check_attendance_date = getdate(add_to_date(today(), days=-(leave_penalty_buffer_days + 1)))
        else:
                leave_penalty_check_attendance_date = getdate(today())
                
        
        #* FOR DAILY HOURS
        expected_work_hours = hr_settings_doc.custom_daily_hours_criteria_for_penalty_for_prompt
        daily_hours_leave_type = hr_settings_doc.custom_leave_type_daily_for_prompt
        daily_hours_leave_deduction = hr_settings_doc.custom_deduction_of_leave_daily_for_prompt
        working_hours_buffer_days = hr_settings_doc.custom_buffer_period_for_daily_hours_penalty_for_prompt
        
        insufficient_hours_deduct_leave = 0.5 if daily_hours_leave_deduction == "Half day" else 1.0
        
        
        is_lwp_for_insufficient_hours = 1 if hr_settings_doc.custom_deduct_leave_penalty_daily_for_prompt == "Deduct leave without pay" else 0
        
        #* GETTING DATE TO CHECK THE ATTENDANCE FOR THAT DATE FOR INSUFFICIENT DAILY HOURS
        if working_hours_buffer_days:    
                daily_hours_attendance_date = getdate(add_to_date(today(), days=-(working_hours_buffer_days + 1)))
        else:
                daily_hours_attendance_date = getdate(add_to_date(today(), days=-1))
        
        if not allowed_late_entries:
                allowed_late_entries = 0
        
        
        
        #* FOR NO ATTENDANCE
        
        no_attendance_buffer_days = hr_settings_doc.custom_buffer_period_for_no_attendance_penalty_for_prompt
        is_lwp_for_no_attendance = 1
        no_attendance_deduct_leave = 1.0
    
        #* GETTING DATE TO CHECK THE ATTENDANCE FOR THAT DATE FOR INSUFFICIENT DAILY HOURS
        if no_attendance_buffer_days:    
                no_attendance_date = getdate(add_to_date(today(), days=-(no_attendance_buffer_days + 1)))
        else:
                no_attendance_date = getdate(add_to_date(today(), days=-1))

        
        
        
        #* FETCHING COMPANY ID
        company_id = fetch_company_name(prompt=1)
        if company_id.get("error"):
                frappe.log_error("Error in penalize_employee_for_late_entry", frappe.get_traceback())
        
        
        
        prompt_employee_list = []
        if not company_id.get("error") and company_id.get("company_id"):
            prompt_employee_list = frappe.db.get_all("Employee", {"status":"Active", "company": company_id.get("company_id")}, ["name", 'holiday_list'])
        
        
            no_attendance_leave_type = frappe.db.get_value("Leave Type", {"is_lwp": 1, "custom_company": company_id.get("company_id")}, "name")
            
            if prompt_employee_list:
                        
                month_first_date = leave_penalty_check_attendance_date.replace(day=1)
                next_month = add_months(month_first_date, 1)
                month_last_date = next_month - timedelta(days=1)
                
                
                leave_period_data = frappe.db.get_value("Leave Period", {"is_active": 1, "company": company_id.get("company_id")}, ["name", "from_date", "to_date"], as_dict=True)
                
                for emp_id in prompt_employee_list:                    
                    # * CALCULATING REMAINING LEAVE BALANCE FOR LATE ENTRY
                    employee_scheduled_for_late_entry_penalty = penalize_employee_for_late_entry_for_prompt(
                                                                emp_id,
                                                                company_id.get("company_id"), 
                                                                month_first_date, 
                                                                month_last_date, 
                                                                allowed_late_entries, 
                                                                leave_penalty_check_attendance_date,
                                                                leave_period_data,
                                                                is_lwp_for_late_entry,
                                                                late_entry_leave_type,
                                                                late_entry_deduct_leave)
                    
                    # ? SEND NEXT DAY PENALTY ALERT FOR LATE ENTRY
                    if employee_scheduled_for_late_entry_penalty:
                        send_penalty_warnings(employee_scheduled_for_late_entry_penalty,"Late Entry")
                    
                    holiday_list = emp_id.get("holiday_list")    

                    if holiday_list:
                        if frappe.db.get_all("Holiday", {"parenttype": "Holiday List", "parent": holiday_list, "holiday_date": daily_hours_attendance_date}, "name"):
                            continue
                    
                    employee_scheduled_for_incomplete_day_penalty = penalize_incomplete_day_for_prompt(
                        emp_id,
                        daily_hours_attendance_date,
                        expected_work_hours,
                        leave_period_data,
                        is_lwp_for_insufficient_hours,
                        daily_hours_leave_type,
                        insufficient_hours_deduct_leave,
                        company_id.get("company_id")
                    )

                    # ? SEND NEXT DAY PENALTY ALERT FOR INCOMPLETE DAY
                    if employee_scheduled_for_incomplete_day_penalty:
                        send_penalty_warnings(employee_scheduled_for_incomplete_day_penalty,"Incomplete Day")
                    
                    
                    employee_scheduled_for_no_attendance_penalty = penalization_for_no_attendance_for_prompt(
                        emp_id,
                        no_attendance_date,
                        leave_period_data,
                        no_attendance_leave_type,
                        no_attendance_deduct_leave,
                        # company_id.get("company_id")
                    )

                    # ? SEND NEXT DAY PENALTY ALERT FOR NO ATTENDANCE
                    if employee_scheduled_for_no_attendance_penalty:
                        send_penalty_warnings(employee_scheduled_for_no_attendance_penalty,"No Attendance")

    except Exception as e:
        frappe.log_error("Error in penalize_prompt_employee", frappe.get_traceback())
@frappe.whitelist()
def penalize_employee_for_late_entry_for_prompt(emp_id, company_id, month_first_date, month_last_date, allowed_late_entries, check_attendance_date, leave_period_data, is_lwp_for_late_entry, late_entry_leave_type, late_entry_deduct_leave):
    """Method to check if the employee is late and the penalization criteria is satisfied and no regularization is created then give penalty to employee
    """
    # *  TO BE ADDED IN HOOKS
    try:
        if (not check_employee_penalty_criteria(emp_id.get("name"), "For Late Arrival")):
                return
        print("penalize_employee_for_late_entry_for_prompt", emp_id.get("name"))            
        late_attendance_list = frappe.db.get_all("Attendance", {"docstatus": 1, "employee": emp_id.get("name"), "attendance_date": ["between", [month_first_date, month_last_date]], "late_entry": 1, "custom_apply_penalty": 1}, ["name", "attendance_date"], order_by="attendance_date asc")
        
        leave_allocation_id = None
        remaining_leave_balance_for_late_entry = get_remaining_leaves(late_entry_leave_type, emp_id.get("name"), company_id)

        if not is_lwp_for_late_entry:            
                        
            if not remaining_leave_balance_for_late_entry > 0:
                earned_leave = 0.0
                lwp_leave = late_entry_deduct_leave
                
            else:
                if remaining_leave_balance_for_late_entry >= late_entry_deduct_leave:
                    earned_leave = late_entry_deduct_leave
                    lwp_leave = 0.0
                    
                else:
                    earned_leave = remaining_leave_balance_for_late_entry
                    lwp_leave = late_entry_deduct_leave - remaining_leave_balance_for_late_entry                
                leave_allocation_id = frappe.db.get_value("Leave Allocation", {"employee": emp_id.get("name"), "leave_type": late_entry_leave_type, "docstatus": 1}, "name")
        else:
            earned_leave = 0.0
            lwp_leave = late_entry_deduct_leave

        if late_attendance_list:
            employee_scheduled_for_penalty_tomorrow = None
            for attendance_id in late_attendance_list[allowed_late_entries:]:
                
                
                leave_application_exists = frappe.db.exists("Leave Application", {"employee": emp_id.get("name"), "docstatus": 1,"from_date": ["<=",attendance_id.get("attendance_date")], "to_date": [">=",attendance_id.get("attendance_date")]})
                
                attendance_regularization_exists = frappe.db.get_all("Attendance Regularization", {"employee": emp_id.get("name"), "attendance": attendance_id.get("name"),"regularization_date": attendance_id.get("attendance_date")}, "name")
                
                employee_late_penalty_exists = frappe.db.exists("Employee Penalty", {"employee": emp_id.get("name"), "attendance": attendance_id.get("name"), "for_late_coming": 1})
                
                if not (leave_application_exists or attendance_regularization_exists or employee_late_penalty_exists) and getdate(attendance_id.get("attendance_date")) <= check_attendance_date :

                        print(f"\n\n Creating Leave Application for {emp_id.get('name')} for late entry on {attendance_id.get('attendance_date')} \n\n")
                        create_employee_penalty(
                            emp_id.get("name"), 
                            attendance_id.get("attendance_date"), 
                            late_entry_deduct_leave, 
                            attendance_id=attendance_id.get("name"), 
                            leave_type=late_entry_leave_type,
                            leave_balance_before_application=remaining_leave_balance_for_late_entry, 
                            leave_period_data=leave_period_data, 
                            earned_leave=earned_leave, 
                            lwp_leave=lwp_leave,
                            leave_allocation_id = leave_allocation_id,  
                            is_lwp_for_late_entry = is_lwp_for_late_entry,
                            for_late_coming=1)
                
                # ? RETURN EMPLOYEE NAME FOR NEXT-DAY PENALIZATION ALERT
                if not (leave_application_exists or attendance_regularization_exists or employee_late_penalty_exists) and getdate(attendance_id.get("attendance_date")) == add_to_date(check_attendance_date,days=1):
                    employee_scheduled_for_penalty_tomorrow  = emp_id.get("name")

            return employee_scheduled_for_penalty_tomorrow

        return None

    except Exception as e:
        frappe.log_error("Error in penalize_employee_for_late_entry", frappe.get_traceback())


@frappe.whitelist() 
def penalize_incomplete_day_for_prompt(emp, check_attendance_date, expected_work_hours, leave_period_data, is_lwp_for_insufficient_hours, daily_hours_leave_type, insufficient_hours_deduct_leave, company_id):
    """Method to apply penalty if the employee has not completed the weekly hours
    """
    #* TO BE ADDED IN HOOKS
    try:
        if (not check_employee_penalty_criteria(emp.get("name"), "For Work Hours")):
                return
        print("penalize_incomplete_day_for_prompt",emp.get("name"))     
        attendance_list = frappe.db.get_all("Attendance", {"docstatus": 1, "employee": emp.get("name"), "attendance_date": check_attendance_date, "working_hours": ["<",expected_work_hours], "custom_apply_penalty": 1}, ["name", "attendance_date"], order_by="attendance_date asc")

        if attendance_list:
            employee_scheduled_for_penalty_tomorrow = None
            remaining_leave_balance = get_remaining_leaves(daily_hours_leave_type, emp.get("name"), company_id)
            if not is_lwp_for_insufficient_hours:
                
                leave_allocation_id = None                                            
                                
                if not remaining_leave_balance > 0:
                    earned_leave = 0.0
                    lwp_leave = insufficient_hours_deduct_leave
                    
                else:
                    if remaining_leave_balance >= insufficient_hours_deduct_leave:
                        earned_leave = insufficient_hours_deduct_leave
                        lwp_leave = 0.0
                        
                    else:
                        earned_leave = remaining_leave_balance
                        lwp_leave = insufficient_hours_deduct_leave - remaining_leave_balance                
                    leave_allocation_id = frappe.db.get_value("Leave Allocation", {"employee": emp.get("name"), "leave_type": daily_hours_leave_type, "docstatus": 1}, "name")
            else:  
                earned_leave = 0.0
                lwp_leave = insufficient_hours_deduct_leave
                leave_allocation_id = None  
                
            for attendance in attendance_list:
                
                leave_application_exists = frappe.db.exists("Leave Application", {"employee": emp.get("name"), "docstatus":1,"from_date": ["<=",attendance.get("attendance_date")], "to_date": [">=",attendance.get("attendance_date")] })
                
                attendance_regularization_exists = frappe.db.get_all("Attendance Regularization", {"employee": emp.get("name"), "attendance": attendance.get("name"),"regularization_date": attendance.get("attendance_date")}, "name")
                
                
                employee_late_penalty_exists = frappe.db.exists("Employee Penalty", {"employee": emp.get("name"), "attendance": attendance.get("name"), "for_insufficient_hours": 1})
                
                
                
                if not (leave_application_exists or attendance_regularization_exists or employee_late_penalty_exists) and getdate(attendance.get("attendance_date")) <= check_attendance_date:
                    create_employee_penalty(
                                                emp.get("name"), 
                                                attendance.get("attendance_date"), 
                                                insufficient_hours_deduct_leave, 
                                                attendance_id=attendance.get("name"), 
                                                leave_type=daily_hours_leave_type, 
                                                leave_balance_before_application=remaining_leave_balance, 
                                                leave_period_data=leave_period_data, 
                                                earned_leave=earned_leave, 
                                                lwp_leave=lwp_leave, 
                                                leave_allocation_id=leave_allocation_id,  
                                                is_lwp_for_insufficient_hours = is_lwp_for_insufficient_hours, 
                                                for_insufficient_hours=1
                                            )
                
                # ? RETURN EMPLOYEE NAME FOR NEXT-DAY PENALIZATION ALERT
                if not (leave_application_exists or attendance_regularization_exists or employee_late_penalty_exists) and getdate(attendance.get("attendance_date")) == add_to_date(check_attendance_date,days=1):
                    employee_scheduled_for_penalty_tomorrow  = emp.get("name")

            return employee_scheduled_for_penalty_tomorrow

        return None
                                    
    except Exception as e:
        frappe.log_error("Error in penalize_incomplete_day scheduler", frappe.get_traceback())   
        

def penalization_for_no_attendance_for_prompt(emp, check_attendance_date, leave_period_data, no_attendance_leave_type, no_attendance_deduct_leave):
    try:
        print(f"\n\n this function is called\n\n")
        if (not check_employee_penalty_criteria(emp.get("name"), "For No Attendance")):
            return
        print("penalization_for_no_attendance_for_prompt",emp.get("name"))
        if not frappe.db.exists("Attendance", {"employee": emp.get("name"), "attendance_date": check_attendance_date, "docstatus": 1}):
            employee_scheduled_for_penalty_tomorrow = None
            leave_application_exists = frappe.db.exists("Leave Application", {"employee": emp.get("name"), "docstatus":1,"from_date": ["<=", check_attendance_date], "to_date": [">=", check_attendance_date]})
            
            attendance_regularization_exists = frappe.db.exists("Attendance Regularization", {"employee": emp.get("name"), "regularization_date": check_attendance_date}, "name")
            
            employee_penalty_exists = frappe.db.exists("Employee Penalty", {"employee": emp.get("name"), "penalty_date": check_attendance_date, "for_no_attendance": 1})
            
            # ? LOGIC FOR SEND REMINDER MAIL FOR PENALIZATION
            next_day = add_days(check_attendance_date, 1)

            # Check if leave exists on the next day
            leave_application_exists_next_day = frappe.db.exists("Leave Application", {
                "employee": emp.get("name"),
                "docstatus": 1,
                "from_date": ["<=", next_day],
                "to_date": [">=", next_day]
            })

            # Check if attendance regularization exists on the next day
            attendance_regularization_exists_next_day = frappe.db.exists("Attendance Regularization", {
                "employee": emp.get("name"),
                "regularization_date": next_day
            }, "name")

            # Check if penalty already applied for next day (for no attendance)
            employee_penalty_exists_next_day = frappe.db.exists("Employee Penalty", {
                "employee": emp.get("name"),
                "penalty_date": next_day,
                "for_no_attendance": 1
            })
            
            if not (leave_application_exists or attendance_regularization_exists or employee_penalty_exists):
                create_employee_penalty(
                                            emp.get("name"),
                                            check_attendance_date,
                                            no_attendance_deduct_leave,
                                            leave_type=no_attendance_leave_type,
                                            leave_period_data=leave_period_data,
                                            earned_leave= 0.0,
                                            lwp_leave=no_attendance_deduct_leave,
                                            is_lwp_for_no_attendance=1,
                                            for_no_attendance=1,                                            
                                    )
            
            # ? RETURN EMPLOYEE NAME FOR NEXT-DAY PENALIZATION ALERT
            if not (leave_application_exists_next_day or attendance_regularization_exists_next_day or employee_penalty_exists_next_day):
                employee_scheduled_for_penalty_tomorrow  = emp.get("name")

            return employee_scheduled_for_penalty_tomorrow
        
        else:
            print(f"\n\n Attendance Exists\n\n")     
            return None
    except Exception as e:
        frappe.log_error("Error in penalization_for_no_attendance_for_prompt", frappe.get_traceback())
        
def create_employee_penalty(
    employee, 
    penalty_date, 
    deduct_leave, 
    attendance_id = None, 
    leave_type = None, 
    leave_balance_before_application = 0.0, 
    leave_period_data = None, 
    earned_leave = 0.0, 
    lwp_leave = 0.0, 
    leave_allocation_id = None, 
    is_lwp_for_insufficient_hours = 0, 
    is_lwp_for_late_entry = 0, 
    is_lwp_for_no_attendance = 0,
    for_late_coming=0, 
    for_insufficient_hours=0,
    for_no_attendance=0    
    ):
    "Method to Create Employee penalty and add an entry to leave ledger entry"
    #* CREATING EMPLOYEE PENALTY
    penalty_doc = frappe.new_doc("Employee Penalty")
    penalty_doc.employee = employee
    penalty_doc.penalty_date = penalty_date
    penalty_doc.total_leave_penalty = deduct_leave
    penalty_doc.deduct_earned_leave = earned_leave
    penalty_doc.deduct_leave_without_pay = lwp_leave
    penalty_doc.leave_balance_before_application = leave_balance_before_application
    
    if attendance_id:
        penalty_doc.attendance = attendance_id
        frappe.db.set_value("Attendance", attendance_id, "status", "Absent")
    if leave_type:
        penalty_doc.leave_type = leave_type
        
    
    if for_late_coming:
        penalty_doc.for_late_coming = 1
        penalty_doc.remarks = f"Penalty for Late Entry on {attendance_id}"
    
    if for_insufficient_hours:
        penalty_doc.for_insufficient_hours = 1
        penalty_doc.remarks = f"Penalty for insufficient Hours on {attendance_id}"
    
    if for_no_attendance:
        penalty_doc.for_no_attendance = 1
        penalty_doc.remarks = f"Penalty for No Attendance Marked on {penalty_date}"
    penalty_doc.insert(ignore_permissions=True)


    # * Fetch PROMPT Company ID
    company = fetch_company_name(prompt=1)
    employee = frappe.get_doc("Employee", employee)
    if company:
        # * RUN ONLY FOR PROMPT
        company_id = company.get("company_id")
        if company_id and employee.company == company_id:
            notification = frappe.get_doc("Notification", "Employee Penalty Alert")
            if notification:
                if not employee.user_id:
                    frappe.log_error(f"User ID not set for Employee {employee.employee_name}")
                    return
                
                # Fetch user email
                user = frappe.get_doc("User", employee.user_id)
                email_id = getattr(user, "email", None)
                if not email_id:
                    frappe.log_error(f"Email not found for User {employee.user_id}")
                    return
                # Render and send email
                reason = ""
                if (penalty_doc.for_late_coming):
                    reason = "Late Entry"
                elif (penalty_doc.for_insufficient_hours):
                    reason = "Insufficient Working Hours"
                elif(penalty_doc.for_no_attendance):
                    reason = "No Attendance"
                
                subject = frappe.render_template(
                    notification.subject,
                    {"reason": reason, "doc":penalty_doc}
                )
                message = frappe.render_template(
                    notification.message,
                        {"reason": reason, "doc":penalty_doc}
                    
                )
                frappe.sendmail(
                    recipients=[email_id],
                    subject=subject,
                    message=message,
                )


    if attendance_id:
        frappe.db.set_value("Attendance", attendance_id, "custom_employee_penalty_id", penalty_doc.name)

    #* CREATING LEAVE LEDGER ENTRY
    if not (is_lwp_for_late_entry or is_lwp_for_insufficient_hours or is_lwp_for_no_attendance) and earned_leave > 0:
        add_leave_ledger_entry(employee, leave_type, leave_allocation_id, leave_period_data, earned_leave)
    frappe.db.commit()
    
    
    
def get_week_off_days(weekly_off_type):
    """Method to get the week off days based on the weekly off type
    """
    days = frappe.db.get_all("WeekOff Multiselect", {"parenttype": "WeeklyOff Type", "parent": weekly_off_type}, "weekoff", pluck="weekoff")
    return days or []


def get_last_full_work_week(ref_date, weekly_off_days, expected_work_days):
    """Method to get the last full work week based on the reference date and weekly off days and expected work days
    """
    day = ref_date
    while True:    
        #* GOING BACKWARDS FORM THE REFERENCE DATE TO LOCATE THE LAST CONTINUOUS BLOCK OF WEEKLY OFF DAYS.
        
        if day.strftime("%A") in weekly_off_days:
            prev_day = day - timedelta(days=1)
            if prev_day.strftime("%A") in weekly_off_days:
                day = prev_day #* CONTINUE GOING BACKWARDS IF THE PREVIOUS DAY IS ALSO A WEEKOFF
                continue
            break
        day -= timedelta(days=1) #* KEEP MOVING BACK UNTIL WE FIND A WEEKOFF DAY
    
    
    #* DEPENDING ON THE FIRST WEEKOFF DAY WE ARE GOING BACKWARDS TO FIND THE LAST FULL WORK WEEK
    start = day - timedelta(days=1)
    working_days = []
    current = start
    while len(working_days) < expected_work_days:
        if current.strftime("%A") not in weekly_off_days:
            working_days.insert(0, current)  # prepend to maintain chronological order
        current -= timedelta(days=1)
    return working_days[0], working_days[-1]
    # print(f"\n\n {day} \n\n")
    # start = day + timedelta(days=1)
    # working_days = []
    # current = start
    
    # print(f"\n\n {current} \n\n")
    # while len(working_days) < expected_work_days:
    #     if current.strftime("%A") not in weekly_off_days:
    #         working_days.append(current)
    #     current += timedelta(days=1)
    # return working_days[0], working_days[-1]

def get_next_working_day_after_weekoffs(start_date, weekly_off_days):
    
    current = start_date
    while current.strftime("%A") in weekly_off_days:
        current += timedelta(days=1)
    print(f"\n\n current {current} \n\n")
    return current

def get_next_work_week(last_eval_date, weekly_off_days, expected_work_days):
    
    current = last_eval_date
    working_days = []
    while len(working_days) < expected_work_days:
        if current.strftime("%A") not in weekly_off_days:
            working_days.append(current)
        current += timedelta(days=1)
    return working_days[0], working_days[-1]

def get_working_days(start_date, end_date, weekly_off_days):
    days = []
    current = start_date
    while current <= end_date:
        if current.strftime("%A") not in weekly_off_days:
            days.append(current)
        current += timedelta(days=1)
    return days

def get_total_working_hours(employee, dates):
    hours = 0
    for day in dates:
        attendance = frappe.get_all("Attendance", filters={
            "employee": employee,
            "attendance_date": day,
            "status": ["in", ["Present", "Work From Home", "Half Day"]]
        }, fields=["working_hours"])
        hours += sum([i.working_hours for i in attendance])
    return hours
# def calculate_daily_hours(checkins):
#     times = sorted([c.time for c in checkins])
#     if len(times) < 2:
#         return 0
#     total = 0
#     for i in range(0, len(times)-1, 2):
#         diff = (times[i+1] - times[i]).total_seconds() / 3600
#         total += diff
#     return total
        
def get_remaining_leaves(leave_type, employee, company_id):
    """Method to get the remaining leave balance for the employee
    """
    
    leave_ledger_entry_id = frappe.db.get_all("Leave Ledger Entry", {"docstatus": 1,"employee": employee, "leave_type": leave_type, "company": company_id}, ["name", "leaves"])

    if leave_ledger_entry_id:
        leave_balance = sum(i.leaves for i in leave_ledger_entry_id)
    else:
        leave_balance = 0.0
    return leave_balance 

@frappe.whitelist()
def add_leave_ledger_entry(employee, leave_type, leave_allocation_id, leave_period_data, earned_leave):
    
    try:
        # return prompt_penalty_doc
        leave_ledger_entry_doc = frappe.new_doc("Leave Ledger Entry")
        leave_ledger_entry_doc.employee = employee
        leave_ledger_entry_doc.leave_type = leave_type
        leave_ledger_entry_doc.transaction_type = "Leave Allocation"
        leave_ledger_entry_doc.transaction_name = leave_allocation_id
        leave_ledger_entry_doc.from_date = leave_period_data.get("from_date")
        leave_ledger_entry_doc.to_date = leave_period_data.get("to_date")
        # leave_ledger_entry_doc.holiday_list = prompt_penalty_doc.holiday_list
        leave_ledger_entry_doc.leaves = -abs(earned_leave)
        
        
        leave_ledger_entry_doc.insert(ignore_permissions=True)
        leave_ledger_entry_doc.submit()
        
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("Error in add_leave_ledger_entry scheduler method", frappe.get_traceback())
        
        
        
        
        
        
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

def check_employee_penalty_criteria(employee=None, penalization_type=None):
    employee = frappe.get_doc("Employee", employee)
    company_abbr = frappe.db.get_value("Company", employee.company, "abbr")
    hr_settings = frappe.get_single("HR Settings")

    # Field mapping
    criteria = {
        "Business Unit": "custom_business_unit",
        "Department": "department",
        "Address": "custom_work_location",
        "Employment Type": "employment_type",
        "Employee Grade": "grade",
        "Designation": "designation",
        "Product Line": "custom_product_line"
    }

    # Abbreviations
    prompt_abbr = hr_settings.custom_prompt_abbr
    indifoss_abbr = hr_settings.custom_indifoss_abbr

    # Determine which table to use based on company
    if company_abbr == prompt_abbr:
        table = hr_settings.custom_penalization_criteria_table_for_prompt
    elif company_abbr == indifoss_abbr:
        table = hr_settings.custom_penalization_criteria_table_for_indifoss
    else:
        return True  # Default allow if company doesn't match

    if not table:
        return True  # Allow if table is not configured

    is_penalisation = False
    for row in table:
        if row.penalization_type != penalization_type:
            continue

        is_penalisation = True
        if row.select_doctype == "Department" and row.is_sub_department:
            if employee.custom_subdepartment == row.value:
                return True
        else:
            employee_fieldname = criteria.get(row.select_doctype)
            if employee_fieldname and getattr(employee, employee_fieldname, None) == row.value:
                return True

    return not is_penalisation or False

# ? DAILY SCHEDULER TO HANDLE EXIT CHECKLIST & INTERVIEW AUTOMATICALLY
def process_exit_approvals():
    today_date = getdate(today())
    print(f"\n=== Running Exit Approval Scheduler on {today_date} ===\n")

    records = frappe.get_all(
        "Exit Approval Process",
        filters={"resignation_approval": "Approved"},
        fields=[
            "name",
            "employee",
            "company",
            "custom_exit_checklist_notification_date",
            "custom_exit_questionnaire_notification_date",
            "employee_separation",
            "exit_interview",
        ],
    )
    print(f"Found {len(records)} approved exit approvals to process.\n")

    for r in records:
        try:
            print(f"> Processing: {r.name} | Employee: {r.employee} | Company: {r.company}")

            # ? PROCESS CHECKLIST IF DUE AND NOT YET CREATED
            checklist_due = (
                r.custom_exit_checklist_notification_date
                and getdate(r.custom_exit_checklist_notification_date) <= today_date
                and not r.employee_separation
            )
            if checklist_due:
                print("  - Raising Exit Checklist...")
                result = raise_exit_checklist(r.employee, r.company, r.name)
                print(f"  ✔ Checklist Result: {result.get('message')}")

            # ? PROCESS EXIT INTERVIEW IF DUE AND NOT YET CREATED
            interview_due = (
                r.custom_exit_questionnaire_notification_date
                and getdate(r.custom_exit_questionnaire_notification_date) <= today_date
                and not r.exit_interview
            )
            if interview_due:
                print("  - Raising Exit Interview...")
                result = raise_exit_interview(r.employee, r.company, r.name)
                print(f"  ✔ Interview Result: {result.get('message')}")

        except Exception as e:
            print(f"  ✖ ERROR while processing {r.name}: {str(e)}")
            frappe.log_error(
                title="Auto Exit Process Error",
                message=frappe.get_traceback()
                + f"\n\nEmployee: {r.employee}, Company: {r.company}",
            )

    print("\n=== Scheduler Execution Complete ===\n")


def send_penalty_warnings(emp_id, penalization_type):
    try:
        penalization_date = add_days(today(), 1)  # one day before penalization
        notification = frappe.get_doc("Notification", "Alert For Penalization")
        
        # Fetch employee
        employee = frappe.get_doc("Employee", emp_id)
        if not employee.user_id:
            frappe.log_error(f"User ID not set for Employee {emp_id}")
            return
        
        # Fetch user email
        user = frappe.get_doc("User", employee.user_id)
        email_id = getattr(user, "email", None) or getattr(user, "email_id", None)
        if not email_id:
            frappe.log_error(f"Email not found for User {employee.user_id}")
            return
        
        if notification:
            # Render and send email
            subject = frappe.render_template(
                notification.subject,
                {"employee_name": employee.employee_name}
            )
            message = frappe.render_template(
                notification.message,
                {
                    "employee_name": employee.employee_name,
                    "penalization_date": penalization_date,
                    "penalization_type": penalization_type,
                    "company": employee.company
                }
            )
            frappe.sendmail(
                recipients=[email_id],
                subject=subject,
                message=message,
            )
    except Exception as e:
        frappe.log_error(f"Error in send_penalty_warnings: {str(e)}")


def send_attendance_issue():
    # * Set the date to check (1 day before today)
    attendance_check_date = add_days(today(), -1)

    # * Fetch PROMPT Company ID
    company_id = fetch_company_name(prompt=1)
    
    # * Load the notification template
    notification = frappe.get_doc("Notification", "Attendance Issue Reminder")

    # ! Handle company fetch failure
    if company_id.get("error"):
        frappe.log_error("Error in penalize_employee_for_late_entry", frappe.get_traceback())
        return

    prompt_employee_list = []

    # * Proceed if company_id exists
    if company_id.get("company_id"):
        prompt_employee_list = frappe.db.get_all(
            "Employee",
            filters={
                "status": "Active",
                "company": company_id.get("company_id")
            },
            fields=["name", "holiday_list", "user_id", "company"]
        )

        if prompt_employee_list:
            for emp in prompt_employee_list:

                # * Use date range for creation field, or use attendance_date if available
                date_start = attendance_check_date + " 00:00:00"
                date_end = (datetime.strptime(attendance_check_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

                # * GET ATTENDANCE OF EMPLOYEE
                attendance = frappe.get_all(
                    "Attendance",
                    filters=[
                        ["employee", "=", emp.get("name")],
                        ["creation", ">=", date_start],
                        ["creation", "<", date_end],
                        ["docstatus", "=", 1]
                    ],
                    fields=["*"],
                    limit=1
                )

                # ? CASE 1: No attendance found
                if not attendance:
                    # * Check if it's a holiday or weekly off
                    holiday_or_weekoff = is_holiday_or_weekoff(emp.get("name"), attendance_check_date)
                    
                    if holiday_or_weekoff.get("is_holiday"):
                        continue  # ! Skip if it's a holiday
                    
                    employee_name = frappe.db.get_value("Employee", emp.get("name"), "employee_name")
                    # * Render subject & message for "No Attendance"
                    subject = frappe.render_template(
                        notification.subject,
                        {"issue_type": "No Attendance", "doc": {
                            "employee_name": employee_name,
                            "attendance_date": attendance_check_date
                        }}
                    )
                    message = frappe.render_template(
                        notification.message,
                        {"issue_type": "No Attendance", "doc": {
                            "employee_name": employee_name,
                            "attendance_date": attendance_check_date,
                            "company": emp.get("company")
                        }}
                    )

                    if emp.user_id:
                        frappe.sendmail(
                            recipients=[emp.user_id],
                            subject=subject,
                            message=message,
                        )

                # ? CASE 2: Attendance found, check for issues
                else:
                    att = attendance[0]

                    if att.status == "Mispunch" or att.late_entry or att.early_exit:
                        # * Determine attendance issue type
                        if att.status == "Mispunch":
                            attendance_issue = "Attendance Mispunch"
                        elif att.late_entry:
                            attendance_issue = "Late Entry"
                        elif att.early_exit:
                            attendance_issue = "Early Exit"
                        else:
                            attendance_issue = "Attendnace MISMATCH"

                        # * Render subject & message based on issue
                        subject = frappe.render_template(
                            notification.subject,
                            {"issue_type": attendance_issue, "doc": att}
                        )
                        message = frappe.render_template(
                            notification.message,
                            {"issue_type": attendance_issue, "doc": att}
                        )

                        if emp.user_id:
                            frappe.sendmail(
                                recipients=[emp.user_id],
                                subject=subject,
                                message=message,
                            )
                            
# ! DAILY SCHEDULER TO HANDLE ATTENDANCE REQUEST RITUALS
@frappe.whitelist()
def daily_attendance_request_rituals():

    all_employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "custom_attendance_capture_scheme"],
    )

    # ? ATTENDANCE CAPTURE SCHEME MAP BASED ON WORK MODE
    attendance_capture_scheme_map = {
        "Work From Home": "Web Checkin-Checkout",
        "On Duty": "Mobile Clockin-Clockout"
    }

    # ? CREATE EMPLOYEE HASHMAP FOR QUICK ACCESS (NAME AS KEY AND SCHEME AS VALUE)
    employee_map = {emp.name: emp.custom_attendance_capture_scheme for emp in all_employees}

    all_attendance_requests = frappe.get_all(
        "Attendance Request",
        filters={
            "docstatus": 1,
            "custom_status": "Approved",
            "employee": ["in", list(employee_map.keys())],
            "from_date": ["<=", today()],
            "to_date": [">=", today()],
        },
        fields=["name", "employee", "reason"],
    )

    attendance_request_hashmap = {}
    for request in all_attendance_requests:
        employee_name = request.employee
        if employee_name not in attendance_request_hashmap:
            attendance_request_hashmap[employee_name] = []
        attendance_request_hashmap[employee_name].append(request)
    
    for employee, scheme in employee_map.items():
        attendance_request = attendance_request_hashmap.get(employee) 
        if attendance_request:
            reason = attendance_request[0].get("reason")
            scheme = attendance_capture_scheme_map.get(reason)
            if employee_map.get(employee) != scheme:
                # ? UPDATE EMPLOYEE SCHEME IF IT DOES NOT MATCH
                frappe.db.set_value("Employee", employee, "custom_attendance_capture_scheme", scheme)
                frappe.db.commit()
        
        elif not attendance_request and scheme in ["Mobile Clockin-Clockout", "Web Checkin-Checkout"]:
            # ? IF NO ATTENDANCE REQUEST EXISTS FOR THE EMPLOYEE, SET THE SCHEME TO BIOMETRIC
            frappe.db.set_value("Employee", employee, "custom_attendance_capture_scheme", "Biometric")
            frappe.db.commit()
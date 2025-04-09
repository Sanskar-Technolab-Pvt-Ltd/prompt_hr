import frappe

from frappe.utils import date_diff, today



@frappe.whitelist()
def create_probation_feedback_form():
    """Scheduler method to create probation feedback form based on the days after when employee joined mentioned in the HR Settings.
        - And Also notify the employee's reporting manager if the remarks are not added to the form.  
    """
    
    try:
        
        first_feedback_days = frappe.db.get_single_value("HR Settings", "custom_first_feedback_after")
        second_feedback_days = frappe.db.get_single_value("HR Settings", "custom_second_feedback_after")
        
        
        if first_feedback_days or second_feedback_days:
        
            employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": "Prompt Equipments PVT LTD", "custom_probation_status": "Pending"}, "name")
            
            for employee in employees_list:
                if employee.get("name"):
                    emp_joining_date = frappe.db.get_value("Employee", employee.get("name"), "date_of_joining")
                    
                    first_feedback_form = frappe.db.get_value("Employee", employee.get("name"), "custom_first_probation_feedback") or None
                    second_feedback_form = frappe.db.get_value("Employee", employee.get("name"), "custom_second_probation_feedback") or None
                    
                    create_only_one = True if not first_feedback_form and not second_feedback_form else False
                    
                    if emp_joining_date:
                        date_difference= date_diff(today(), emp_joining_date)
                        
                        if first_feedback_days <= date_difference:
                            if not first_feedback_form:
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
                                    "evaluation_date": today()                                                                     
                                })
                                
                                first_probation_form.insert(ignore_permissions=True)
                                employee_doc.custom_first_probation_feedback = first_probation_form.name
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()
                            else:
                                remarks_added = frappe.db.exists("Probation Feedback Prompt", {"parenttype": "Probation Feedback Form", "parent": first_feedback_form, "rating": ["is", "set"]})
                                
                                if not remarks_added:
                                    print(f"Send Mail")
                        
                        if second_feedback_days <= date_difference:
                            if not second_feedback_form and not create_only_one:
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
                                    "evaluation_date": today()
                                })
                                
                                first_probation_form.insert(ignore_permissions=True)
                                employee_doc.custom_second_probation_feedback = first_probation_form.name
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()
                            elif second_feedback_form:
                                    remarks_added = frappe.db.exists("Probation Feedback Prompt", {"parenttype": "Probation Feedback Form", "parent": second_feedback_form, "rating": ["is", "set"]})
                                    
                                    if not remarks_added:
                                        print(f"Send Mail")
    except Exception as e:
        frappe.log_error("Error while creating probation feedback form", frappe.get_traceback())



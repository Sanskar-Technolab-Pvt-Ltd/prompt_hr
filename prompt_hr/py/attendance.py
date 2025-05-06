import frappe
from datetime import timedelta
from frappe import throw
from frappe.utils import get_datetime, time_diff_in_hours, today, getdate, days_diff, add_months, date_diff
from prompt_hr.py.utils import send_notification_email



@frappe.whitelist()
def create_attendance_regularization(attendance_id, update_data):
    """Method to create Attendance Regularization
    """
    try:
        regularization_data = frappe.parse_json(update_data)
        
        if not regularization_data:
            throw("No Regularization data found")
        
        
        attendance_doc = frappe.get_doc("Attendance", attendance_id)
        
        if not attendance_doc:
            throw("No Attendance Found")
        
        attendance_regularization_doc = frappe.new_doc("Attendance Regularization")
        
        attendance_regularization_doc.employee = attendance_doc.employee
        attendance_regularization_doc.attendance = attendance_id
        attendance_regularization_doc.regularization_date = attendance_doc.attendance_date
        
        for row in regularization_data:
            attendance_regularization_doc.append("checkinpunch_details", row)
        
        
        attendance_regularization_doc.save(ignore_permissions=True)
        
        # * SENDING EMAIL TO EMPLOYEE'S REPORTING HEAD
        if attendance_regularization_doc.name:
            rh_emp = frappe.db.get_value("Employee", attendance_doc.employee, "reports_to")
            if rh_emp:
                rh_user_id = frappe.db.get_value("Employee", rh_emp, "user_id")
                if rh_user_id:
                    send_notification_email(
                        recipients=[rh_user_id],
                        notification_name="Attendance Regularization Created",
                        doctype="Attendance Regularization",
                        docname=attendance_regularization_doc.name,
                        send_link=True,
                        fallback_subject=f"Attendance Regularization Created for {attendance_doc.attendance_date}",
                        fallback_message=f"Dear Reporting Head, <br>   I would like to inform you that I have created an Attendance Regularization record for {attendance_doc.attendance_date}. <br>The record is now available in the system for your review and necessary action."
                        
                    )                    
        
        return {"attendance_regularization_id": attendance_regularization_doc.name}
        
        
        
    except Exception as e:
        frappe.log_error("Error While creating Attendance Regularization", frappe.get_traceback())
        throw(str(e))
        


@frappe.whitelist()
def validate_for_regularization(attendance_id, attendance_date, employee_id):
    """
        Checking company and checking the condition based on the company deciding whether the employee is allowed to create attendance regularization or not
    """
    try:
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
        
        if not prompt_abbr:
            throw("No Abbreviation set for Prompt in HR Settings")
        prompt_company_id = frappe.db.get_value("Company", {"abbr": prompt_abbr}, "name")
        
        indifoss_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
        
        if not indifoss_abbr:
            throw("No Abbreviation set for IndiFOSS in HR Settings")
        
        indifoss_company_id = frappe.db.get_value("Company", {"abbr": indifoss_abbr}, "name")
        
        employee_company_id = frappe.db.get_value("Employee", employee_id, "company")
        
        if not employee_company_id:
            throw("Employee Company not found, please verify employee is linked to a company or not")
        
        if employee_company_id == prompt_company_id:
            is_allowed = allow_regularization_for_prompt(attendance_date)

            if not is_allowed.get("error") and is_allowed.get("is_allowed"):
                return {"error": 0, "is_allowed": 1}
            elif is_allowed.get("error"):
                return {"error": 1, "message": is_allowed.get("message")}
            
            
        elif employee_company_id == indifoss_company_id:
            is_allowed = validate_regularization_creation_for_indifoss(attendance_date, employee_id)
            
            if not is_allowed.get("error") and is_allowed.get("is_allowed"):
                return {"error": 0, "is_allowed": 1}
            elif is_allowed.get("error"):
                return {"error": 1, "message": is_allowed.get("message")}
            
            
    except Exception as e:
        throw(str(e))


def allow_regularization_for_prompt(attendance_date):
    """Method to check if the employee is allowed to create attendance regularization for PROMPT
    """
    try:
        print(f"\n\n for prompt \n\n")
        allowed_past_days = frappe.db.get_single_value("HR Settings", "custom_allowed_to_raise_regularizations_for_past_days_for_prompt")
        
        if not allowed_past_days or allowed_past_days == 0 or allowed_past_days is None:
            return {"error": 1, "message": "Allowed to raise regularizations for past days is not defined in HR Settings"}
        
        today_date = getdate() #*BY DEFAULT GIVES TODAY DATE
        attendance_date = getdate(attendance_date)
        
        past_days_diff = days_diff(today_date, attendance_date)

        print(f"\n\n past_days_diff {past_days_diff}\n\n")
        if past_days_diff <= allowed_past_days:
            return {"error": 0, "is_allowed": 1}
        elif past_days_diff > allowed_past_days:
            return {"error": 1, "message": "Days Limit Exceeded. Regularization cannot be created"}
        
    except Exception as e:
        frappe.log_error("Error While checking for is employee allowed to create regularization", frappe.get_traceback())
        return {"error": 1, "message": str(e)}
    

def validate_regularization_creation_for_indifoss(attendance_date, employee_id):
    """Method to check if the employee is allowed to create regularization for IndiFOSS
    """
    try:
        
        allowed_times_in_month = frappe.db.get_single_value("HR Settings", "custom_allowed_regularizations_monthly_for_indifoss")
        
        if not allowed_times_in_month:
            return {"error": 1, "message": "Allowed regularizations monthly is no set in HR Settings"}
        attendance_date = getdate(attendance_date)
        
        first_date = attendance_date.replace(day=1)
        
        next_month = add_months(first_date, 1)
        
        last_date = next_month - timedelta(days=1)
        
        
        regularizations_count = frappe.db.get_count("Attendance Regularization", {"employee": employee_id, "regularization_date": ["between", [first_date, last_date]]})
        
        
        if regularizations_count < allowed_times_in_month:
            return {"error": 0, "is_allowed": 1}
        elif regularizations_count >= allowed_times_in_month:
            return {"error": 1, "message": "Limit exceeded to create regularization in a month"}
    except Exception as e:
        frappe.log_error("Error while validating regularization creation", frappe.get_traceback())
        return {"error": 1, "message": str(e)}
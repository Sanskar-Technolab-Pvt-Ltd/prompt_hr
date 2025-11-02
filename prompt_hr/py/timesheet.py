import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, cint
from datetime import datetime




@frappe.whitelist()
def set_billing_rate(doc):
    
    doc = frappe.parse_json(doc)
    billing_rate = 0        
    monthly_salary = 0
    
        
    gross_salary = frappe.db.get_value("Employee", doc.employee, "custom_gross_salary")
    ctc_salary = frappe.db.get_value("Employee", doc.employee, "ctc") 
    
    if gross_salary:
        monthly_salary = gross_salary
    else:
        monthly_salary = ctc_salary
    
    working_days = frappe.db.get_single_value("HR Settings", "custom_working_days_to_calculate_billing_rate_for_prompt") or 28
    daily_salary = 0
    
    shift = frappe.db.get_value("Employee", doc.employee, "default_shift")
    shift_hours = 0
    break_hours = 0
    if shift:
        shift_data = frappe.db.get_values("Shift Type", shift, ["start_time", "end_time", "custom_break_time"], as_dict=True) 
        
    
    if shift_data:
        shift_data = shift_data[0]
        if shift_data.get("start_time") and shift_data.get("end_time"):
            fmt = "%H:%M:%S"
            start = datetime.strptime(str(shift_data.get("start_time")), fmt)
            end = datetime.strptime(str(shift_data.get("end_time")), fmt)
            
            total_hours = (end - start).total_seconds() / 3600
            if shift_data.get("custom_break_time"):
                break_hours = ( shift_data.get("custom_break_time") or 0) / 60
                
            shift_hours = total_hours - break_hours
                    
    if gross_salary:
        daily_salary = float(monthly_salary / working_days)
    
    
    if daily_salary and shift_hours:    
        billing_rate = float(daily_salary / shift_hours)

        
    return {"billing_rate": billing_rate}



# * IF THE USER IS PROJEC CO-ORDINATOR OR HAS ANY OF THE HR MANAGER ROLES THEN RETURNING 1 ELSE O
@frappe.whitelist()
def show_filds_for(project = None):
    try:
        current_user = frappe.session.user
        hr_manager_roles = ["S - HR Director (Global Admin)", "S - HR L1", "S - HR L2"]
        
        if project and frappe.db.exists("Project", {"name": project, "custom_project_coordinator": current_user}):
            return {"error": 0, "show_fields": 1}
            
        else:
            if any(role in frappe.get_roles(current_user) for role in hr_manager_roles):
                return {"error": 0, "show_fields": 1}                    
        
        return {"error": 0, "show_fields": 0}
    except Exception as e:
        frappe.log_error("error_show_fields_for", frappe.get_traceback())
        return {"error": 1, "message": str(e), "show_fields": 0}
         

def is_within_allowed_weeks(self, weeks: int) -> bool:
        """
        Return True if start_date >= today - (weeks * 7) days
        """
        


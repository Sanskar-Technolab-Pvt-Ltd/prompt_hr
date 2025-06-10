import frappe
from frappe.utils import getdate, today, add_months
from datetime import timedelta
from bs4 import BeautifulSoup 

# ! prompt_hr.api.mobile.upcoming_holidays.get
# ? GET UPCOMING HOLIDAYS DETAIL

@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF EMPLOYEE  DOC EXISTS OR NOT
        employee_exists = frappe.db.exists("Employee", name)

        # ? IF EMPLOYEE DOC NOT
        if not employee_exists:
            frappe.throw(
                f"Employee: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET EMPLOYEE  DOC
        employee = frappe.get_doc("Employee", name)
        
        # ? IF NOT HOLIDAYS
        if not employee.holiday_list:
            frappe.throw(
                f"Employee: {name} - Holiday List Does Not Exists!",
                frappe.DoesNotExistError,
            )
        
        # ? GET HOLIDAYS  DOC
        holiday_list = frappe.get_doc("Holiday List", employee.holiday_list)
        
        # ? IF NOT HOLIDAYS
        if not holiday_list:
            frappe.throw(
                f"Employee: {name} - Holiday List Does Not Exists!",
                frappe.DoesNotExistError,
            )
            
        today_date = getdate(today())
        month_first_date = today_date.replace(day=1)
        next_month = add_months(month_first_date, 1)
        month_last_date = next_month - timedelta(days=1)
      
        
        # GET HOLIDAYS FOR CURRENT MONTH EXCLUDING WEEKLY OFFS
        holidays = []
        for holiday in holiday_list.holidays:
            holiday_date = getdate(holiday.holiday_date)
            if (month_first_date <= holiday_date <= month_last_date 
                and not holiday.weekly_off):
                
                # EXTRACT PLAIN TEXT FROM HTML DESCRIPTION
                description_text = holiday.description
                if holiday.description and "<div" in holiday.description.lower():
                    soup = BeautifulSoup(holiday.description, 'html.parser')
                    description_text = soup.get_text().strip()
                    
                holidays.append({
                    "holiday_date": holiday.holiday_date,
                    "description": description_text
                })

        if not holidays:
            frappe.throw(f"No holidays found for current month {month_first_date} to {month_last_date} (excluding weekly offs)")

        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Upcoming Holidays Detail", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Upcoming Holidays Loaded Successfully!",
            "data": holidays,
        }
        
import frappe

from datetime import datetime
from dateutil.relativedelta import relativedelta


def get_next_date(start_date_str, months):
    """Method to calculate the next date based on given start date and number of months.
    start_date_str: string in 'YYYY-MM-DD' format
    months: float, e.g. 1.5 means 1 month and 15 days (assuming 30-day avg for fraction)
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        
        
        whole_months = int(months)
        fractional_month = months - whole_months
        
        
        intermediate_date = start_date + relativedelta(months=whole_months)
        
        
        next_month = intermediate_date + relativedelta(months=1)
        days_in_month = (next_month - intermediate_date).days
        additional_days = int(fractional_month * days_in_month)

        
        final_date = intermediate_date + relativedelta(days=additional_days)
        
        return {"error": 0, "message":final_date.strftime("%Y-%m-%d")}
    except Exception as e:
        frappe.log_error("Error while calculating next date", frappe.get_traceback())
        return {"error": 1, "message": str(e)}
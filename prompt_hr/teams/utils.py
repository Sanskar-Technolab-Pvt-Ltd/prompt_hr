import frappe
from datetime import datetime
import pytz


@frappe.whitelist()
def format_date_time_erpnext_to_teams(date, start_time, end_time):
   
    local_tz = pytz.timezone("Asia/Kolkata")
    
    # Combine date and time
    start_dt_local = datetime.combine(date, datetime.min.time()) + start_time
    end_dt_local = datetime.combine(date, datetime.min.time()) + end_time

    # Localize to IST
    start_dt_localized = local_tz.localize(start_dt_local)
    end_dt_localized = local_tz.localize(end_dt_local)

    
    return {
        "start_time": start_dt_localized.strftime('%Y-%m-%dT%H:%M:%S'),
        "end_time": end_dt_localized.strftime('%Y-%m-%dT%H:%M:%S')
    }


 
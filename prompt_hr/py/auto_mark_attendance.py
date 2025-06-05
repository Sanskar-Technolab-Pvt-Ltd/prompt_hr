import frappe

from frappe import throw
from frappe.utils import datetime, today, getdate, get_datetime, format_duration, time
from datetime import timedelta
from prompt_hr.py.utils import fetch_company_name




def auto_attendance(attendance_date=None, is_scheduler = 1):
    """Method to create attendance for the specified date or current date.
    """
    try:
        pass
        # if is_scheduler:
        #     mark_attendance(prompt=1)
        #     mark_attendance(indifoss=1)
        # else:
        #     if attendance_date:
        #         mark_attendance()
    except Exception as e:
        if is_scheduler:
            frappe.log_error("Error in auto attendance", frappe.get_traceback())
        else:
            throw(f"Error While Marking Attendance \n{e}")
            frappe.log_error("Error while marking attendance", frappe.get_traceback())



@frappe.whitelist()
def mark_attendance(emp_id=None, attendance_date=None, is_scheduler=1, prompt=0, indifoss=0):
    """Method to mark attendance for prompt employee
    """
    
    if not is_scheduler:
        if prompt:
            company_name = fetch_company_name(prompt=1)
        elif indifoss:
            company_name = fetch_company_name(indifoss=1)
        
        if company_name.get("error"):
            throw(company_name.get("message"))
        
        company_id = company_name.get("company_id")

        
        employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id}, ["name", "holiday_list", "custom_is_overtime_applicable"])

        if not employee_list:
            throw("No Employees Found")

        if prompt:
            grace_time_period_for_late_coming = frappe.db.get_single_value("HR Settings", "custom_grace_time_period_for_late_coming_for_prompt") or 0
            grace_time_for_insufficient_hours = frappe.db.get_single_value("HR Settings", "custom_daily_hours_criteria_for_penalty_for_prompt") or 0
        elif indifoss:
            grace_time_period_for_late_coming = frappe.db.get_single_value("HR Settings", "custom_grace_time_period_for_late_coming_for_indifoss") or 0
        
    else:
        prompt_company_name = fetch_company_name(prompt=1)
        indifoss_company_name = fetch_company_name(indifoss=1)
        
        if prompt_company_name.get("error"):
            frappe.log_error("Error in fetch_company_name method", company_name.get("message"))
            return 0
        
        if indifoss_company_name.get("error"):
            frappe.log_error("Error in fetch_company_name method", company_name.get("message"))
            return 0

        
        prompt_company_id = prompt_company_name.get("company_id")
        indifoss_company_id = indifoss_company_name.get("company_id")
        
        employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": ["in", [prompt_company_id, indifoss_company_id]]}, ["name", "holiday_list", "custom_is_overtime_applicable", "company"])
        
        if not employee_list:
            frappe.log_error("Error in mark_attendance_for_prompt", "No Employee Found")    
        
        
        grace_time_period_for_late_coming_for_prompt = frappe.db.get_single_value("HR Settings", "custom_grace_time_period_for_late_coming_for_prompt") or 0
        grace_time_for_insufficient_hours_for_prompt = frappe.db.get_single_value("HR Settings", "custom_daily_hours_criteria_for_penalty_for_prompt") or 0
        
        grace_time_period_for_late_coming_for_indifoss = frappe.db.get_single_value("HR Settings", "custom_grace_time_period_for_late_coming_for_indifoss") or 0
        
            
    mark_attendance_date = getdate(attendance_date) if attendance_date else getdate(today())
    str_mark_attendance_date = mark_attendance_date.strftime("%Y-%m-%d")
    

    day_start_time = get_datetime(mark_attendance_date)
    day_end_time = get_datetime(str_mark_attendance_date + " 23:59:59")     
        
    for employee_data in employee_list:
        if is_scheduler:
            if employee_data.get("company") == prompt_company_id:
                
                is_marked = attendance(
                    employee_data,
                    mark_attendance_date,
                    str_mark_attendance_date,
                    day_start_time,
                    day_end_time,
                    grace_time_period_for_late_coming_for_prompt,
                    grace_time_for_insufficient_hours = grace_time_for_insufficient_hours_for_prompt,
                    prompt = 1
                )

            elif employee_data.get("company") == indifoss_company_id:
                is_marked = attendance(
                    employee_data,
                    mark_attendance_date,
                    str_mark_attendance_date,
                    day_start_time,
                    day_end_time,
                    grace_time_period_for_late_coming_for_indifoss,
                    grace_time_for_insufficient_hours = grace_time_period_for_late_coming_for_indifoss,
                )
        else:
            is_marked = attendance(
                employee_data,
                mark_attendance_date,
                str_mark_attendance_date,
                day_start_time,
                day_end_time,
                grace_time_period_for_late_coming,
                grace_time_for_insufficient_hours,
                prompt = prompt
            )

def attendance(employee_data, mark_attendance_date, str_mark_attendance_date, day_start_time, day_end_time, grace_time_period_for_late_coming, grace_time_for_insufficient_hours=0, prompt=0):
    
    assigned_shift = frappe.db.get_all("Shift Assignment", {"docstatus": 1, "status": "Active","employee": employee_data.get("name"), "start_date":["<=", mark_attendance_date], "end_date":[">=", mark_attendance_date]}, ["name","shift_type"], order_by="creation desc", limit=1)

    #* If no shift assigned then move to next employee
    if not assigned_shift:
        return 0
    
    #* Checking if attendance exists then move to another employee
    attendance_exists = frappe.db.exists("Attendance", {"employee": employee_data.get("name"), "attendance_date": mark_attendance_date, "status": ["!=", "Half Day"]})
    
    #* CHECKING IS THERE ANY HALF DAY ATTENDANCE OR NOT
    half_day_attendance = frappe.db.get_value("Attendance", {"employee": employee_data.get("name"), "attendance_date": mark_attendance_date, "status": "Half Day", "leave_application": ["is", "set"]}, ["name", "custom_half_day_time"], as_dict=True)
    
    if attendance_exists:
        return 0
    
    #* FETCHING SHIFT DETAILS
    shift_type = assigned_shift[0].get("shift_type")
    
    half_day_threshold= frappe.db.get_value("Shift Type", shift_type, "working_hours_threshold_for_half_day")
    absent_threshold = frappe.db.get_value("Shift Type", shift_type, "working_hours_threshold_for_absent")
    
    shift_start_time = frappe.db.get_value("Shift Type", shift_type, "start_time")
    shift_end_time = frappe.db.get_value("Shift Type", shift_type, "end_time")
    
    
    #* GENERATING MIDDLE TIME BASED ON SHIFT START & END TIME AND CHANGING THE VALUE OF shift_start_time or shift_end_time BASED ON THE HALF DAY TIME
    is_half_day = False        
    if half_day_attendance:
        is_half_day = True
        shift_start_datetime = get_datetime(str_mark_attendance_date) + shift_start_time
        shift_end_datetime = get_datetime(str_mark_attendance_date) + shift_end_time
    
        time_diff = shift_end_datetime - shift_start_datetime
    
        middle_time_delta = time_diff / 2
        middle_datetime = shift_start_datetime + middle_time_delta
        
        if half_day_attendance.get("custom_half_day_time") == "First":
            shift_start_time = middle_datetime.time()
        elif half_day_attendance.get("custom_half_day_time") == "Second":
            shift_end_time = middle_datetime.time()
            
    
    #* FETCHING EMPLOYEE'S FIRST CHECKIN & LAST CHECKOUT RECORD
    in_type_emp_checkin = frappe.db.get_all("Employee Checkin", {"employee": employee_data.get("name"), "log_type": "IN", "time": ["between", [day_start_time, day_end_time]]}, ["name", "time"], order_by="time asc", limit=1)
    out_type_emp_checkin = frappe.db.get_all("Employee Checkin", {"employee": employee_data.get("name"), "log_type": "OUT", "time": ["between", [day_start_time, day_end_time]]}, ["name", "time"], order_by="time desc", limit=1)
    
    
    attendance_status = None
    formatted_working_hours = ''
    final_working_hours = 0.0
    ot_duration = 0.0
    is_early_exit = 0
    late_entry = 0
    apply_penalty = 0
    is_only_one_record = 0
    is_overtime_applicable = employee_data.get("custom_is_overtime_applicable")
    remarks = ''
    in_type_emp_checkin_id = None
    in_datetime = None
    out_type_emp_checkin_id = None
    out_datetime = None
    
    
    if not in_type_emp_checkin and not out_type_emp_checkin:
        holiday_or_weekoff = is_holiday_or_weekoff(employee_data.get("name"), mark_attendance_date)
        
        if not holiday_or_weekoff.get("is_holiday") and not holiday_or_weekoff.get("is_weekoff"):
            return 0            
        if holiday_or_weekoff.get("is_holiday"):
            return 0
        if holiday_or_weekoff.get("is_weekoff"):
            attendance_status = "WeekOff"
        
    
    if in_type_emp_checkin:
        in_type_emp_checkin_id = in_type_emp_checkin[0].get("name")
        in_datetime = in_type_emp_checkin[0].get("time")    
    if out_type_emp_checkin:
        out_type_emp_checkin_id = out_type_emp_checkin[0].get("name")
        out_datetime = out_type_emp_checkin[0].get("time")
    
    if in_datetime and out_datetime:
        
        work_duration = out_datetime - in_datetime
        
        work_hours = work_duration.total_seconds() / 3600
        final_working_hours = round(work_hours, 1)
        
        total_minutes = int(work_duration.total_seconds())
        
        formatted_working_hours = format_duration(total_minutes)
        
        if final_working_hours < half_day_threshold and final_working_hours > absent_threshold:
            attendance_status = "Half Day"
            
            if prompt:
                if final_working_hours < grace_time_for_insufficient_hours:
                    apply_penalty = 1
            
        elif final_working_hours < absent_threshold:
            attendance_status = "Absent"
            apply_penalty = 1
        else:
            attendance_status = "Present"
        
        
        if prompt and is_overtime_applicable:
            ot_duration = overtime_duration(out_datetime, shift_end_time)
        
        if not is_half_day:
            late_entry_and_apply_penalty = is_late_entry(in_datetime, shift_start_time, grace_time_period_for_late_coming)
        else:
            late_entry_and_apply_penalty = is_late_entry(in_datetime, shift_start_datetime, grace_time_period_for_late_coming, is_half_day=1)
        
        late_entry = late_entry_and_apply_penalty.get("is_late_entry")
        apply_penalty = late_entry_and_apply_penalty.get("apply_penalty")
        
        shift_end_datetime = get_datetime(out_datetime.date()) + shift_end_time
        if out_datetime < shift_end_datetime:
            is_early_exit = 1
    
    elif in_datetime:
        if not is_half_day:
            late_entry_and_apply_penalty = is_late_entry(in_datetime, shift_start_time, grace_time_period_for_late_coming)
        else:
            late_entry_and_apply_penalty = is_late_entry(in_datetime, shift_start_datetime, grace_time_period_for_late_coming, is_half_day=1)
        
        late_entry = late_entry_and_apply_penalty.get("is_late_entry")
        apply_penalty = late_entry_and_apply_penalty.get("apply_penalty")
        
        is_only_one_record = 1

    elif out_datetime:
        shift_end_datetime = get_datetime(out_datetime.date()) + shift_end_time
        if out_datetime < shift_end_datetime:
            is_early_exit = 1
        is_only_one_record = 1
            
    
    
    attendance_request = frappe.db.get_all("Attendance Request", {"docstatus":1, "custom_status":"Approved", "employee": employee_data.get("name"), "from_date": ["<=", mark_attendance_date], "to_date":[">=", mark_attendance_date]}, ["name", "reason"], limit=1)
    
    attendance_type = None
    if attendance_request:
            attendance_type = attendance_request[0].get("reason")

    if is_only_one_record:
        attendance_status = "Mispunch"
        remarks = "Only single record found"
    
    if attendance_status in ["Half Day", "Absent"] and not apply_penalty:
        apply_penalty = 1
    
    print(f"\n\n status {attendance_status}  {apply_penalty} {formatted_working_hours} \n\n")
    
    if is_half_day:
        update_attendance(half_day_attendance.get("name"), {
            "custom_type": attendance_type,
            "custom_work_hours": formatted_working_hours,
            "working_hours": final_working_hours,
            "custom_overtime": ot_duration,
            "late_entry": late_entry,
            "early_exit": is_early_exit,
            "custom_apply_penalty": apply_penalty,
            "in_time" : in_datetime if in_type_emp_checkin else None,
            "out_time" : out_datetime if out_type_emp_checkin else None,
            "custom_checkin_time" : in_datetime if in_type_emp_checkin else None,
            "custom_checkout_time" : out_datetime if out_type_emp_checkin else None,
            "custom_remarks" : remarks,
            "custom_employee_checkin" : in_type_emp_checkin_id if in_type_emp_checkin else None,
            "custom_employee_checkout" : out_type_emp_checkin_id if out_type_emp_checkin else None
            
        })
    else:
        create_attendance(
            employee_data.get("name"),
            mark_attendance_date,
            attendance_status,
            custom_type = attendance_type,
            custom_work_hours=formatted_working_hours,
            working_hours=final_working_hours,
            custom_overtime = ot_duration,
            late_entry = late_entry,
            early_exit = is_early_exit,
            custom_apply_penalty = apply_penalty,
            shift = shift_type,
            in_time = in_datetime if in_type_emp_checkin else None,
            out_time = out_datetime if out_type_emp_checkin else None,
            custom_checkin_time = in_datetime if in_type_emp_checkin else None,
            custom_checkout_time = out_datetime if out_type_emp_checkin else None,
            custom_remarks = remarks,
            custom_employee_checkin = in_type_emp_checkin_id if in_type_emp_checkin else None,
            custom_employee_checkout = out_type_emp_checkin_id if out_type_emp_checkin else None
        )            
    return 1
def is_holiday_or_weekoff(emp_id, mark_attendance_date):
    """Method to check if today is holiday or weekoff or  not
    """
    emp_holiday_list = frappe.db.get_value("Employee", emp_id, "holiday_list")
    
    if not emp_holiday_list:
        return {"is_holiday": 0, "is_weekoff": 0}
    
    is_holiday = frappe.db.get_all("Holiday", {"parenttype": "Holiday List", "parent": emp_holiday_list, "holiday_date": mark_attendance_date}, "name", limit=1)
    
    weekoff = frappe.db.get_all("WeekOff Change Request", {"status": "Approved", "employee": emp_id}, "name")
    
    is_weekoff = False
    
    
    if weekoff:
        for weekoff_detail in weekoff:
            is_existing_date = frappe.db.get_all("WeekOff Request Details", {"parenttype": "WeekOff Change Request", "parent": weekoff_detail.get("name"), "existing_weekoff_date": mark_attendance_date}, "name", limit=1)
    
            is_new_date = frappe.db.get_all("WeekOff Request Details", {"parenttype": "WeekOff Change Request", "parent": weekoff_detail.get("name"), "new_weekoff_date": mark_attendance_date}, "name", limit=1)
            
            if is_existing_date:
                is_weekoff = False
                break
            
            if is_new_date:
                is_weekoff = True
                break
            
    
    return {"is_holiday": 1 if is_holiday else 0, "is_weekoff": 1 if is_weekoff else 0}
    

def calculate_work_hours():
    pass
def overtime_duration(employee_out_time, shift_end_time):
    """ Method to calculate overtime duration
    """
    
    overtime_details = frappe.db.get_all("Overtime Details", {"parenttype": "HR Settings"}, ["from_time", "to_time", "final_time"])
    
    shift_end_time = get_datetime(employee_out_time.date()) + shift_end_time
    
    overtime = employee_out_time - shift_end_time
    
    overtime_float_value = round(overtime.total_seconds() / 3600, 2)
    
    print(f"\n\n overtime_float_value {overtime_float_value} \n\n")
    final_overtime = 0.0
    
    if overtime_details:
        for overtime_detail in overtime_details:
            if overtime_detail.get("from_time") <= overtime_float_value <= overtime_detail.get("to_time"):
                final_overtime = overtime_detail.get("final_time")
                break
    else:
        final_overtime = overtime_float_value
    
    return final_overtime
    
def is_late_entry(employee_in_datetime, shift_start_time, grace_time , is_half_day = 0):
    """Method to check if the employee is late or not
    """
    print(f"\n\n  sdfdsff {grace_time} \n\n")
    if not is_half_day:
        shift_start_datetime = get_datetime(employee_in_datetime.date()) + shift_start_time
    else:
        shift_start_datetime = shift_start_time
    time_diff = employee_in_datetime - shift_start_datetime
    late_minutes = int(time_diff.total_seconds() // 60)
    
    return {"is_late_entry": 1 if late_minutes > 0 else 0, "apply_penalty": 1 if late_minutes > grace_time else 0}
    

def create_attendance(
    employee,
    attendance_date,
    status,
    custom_type=None,
    custom_work_hours = '',
    working_hours = 0.0,
    custom_overtime= 0.0,
    late_entry = 0,
    early_exit = 0,
    custom_apply_penalty = 0,
    shift = '',
    in_time = None,
    out_time = None,
    custom_checkin_time = None,
    custom_checkout_time = None,
    custom_remarks = '',
    custom_employee_checkin = None,
    custom_employee_checkout = None
    
):
    """Method to create attendance
    """
    
    attendance_doc = frappe.new_doc("Attendance")
    attendance_doc.employee = employee
    attendance_doc.attendance_date = attendance_date
    attendance_doc.status = status
    attendance_doc.custom_type = custom_type
    attendance_doc.custom_work_hours = custom_work_hours
    attendance_doc.working_hours = working_hours
    attendance_doc.custom_overtime = custom_overtime
    attendance_doc.late_entry = late_entry
    attendance_doc.early_exit = early_exit
    attendance_doc.custom_apply_penalty = custom_apply_penalty
    attendance_doc.shift = shift
    attendance_doc.in_time = in_time
    attendance_doc.out_time = out_time
    attendance_doc.custom_checkin_time = custom_checkin_time
    attendance_doc.custom_checkout_time = custom_checkout_time
    attendance_doc.custom_remarks =custom_remarks
    attendance_doc.custom_employee_checkin = custom_employee_checkin
    attendance_doc.custom_employee_checkout = custom_employee_checkout
    
    attendance_doc.insert(ignore_permissions=True)
    attendance_doc.submit()
    frappe.db.commit()


def update_attendance(attendance_id, update_values):
    """Method to Update Attendance
    """
    # attendance_doc = frappe.get_doc("Attendance", attendance_id)
    
    if update_values:
        print(f"\n\nsdsad  {update_values} \n\n")
        for fieldname, values in update_values.items():
            print(f"\n fieldname value {fieldname} {values}\n")
            frappe.db.set_value("Attendance", attendance_id, fieldname, values)
    
    frappe.db.commit()
#*-------------------------------------------------------------------------------------------------------------------------------





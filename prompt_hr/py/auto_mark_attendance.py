import frappe

from frappe import throw
from frappe.utils import datetime, today, getdate, get_datetime, format_duration, time, add_days
from datetime import timedelta
from prompt_hr.py.utils import fetch_company_name




# def auto_attendance(attendance_date=None, is_scheduler = 1):
#     """Method to create attendance for the specified date or current date.
#     """
#     try:
#         pass
#         # if is_scheduler:
#         #     mark_attendance(prompt=1)
#         #     mark_attendance(indifoss=1)
#         # else:
#         #     if attendance_date:
#         #         mark_attendance()
#     except Exception as e:
#         if is_scheduler:
#             frappe.log_error("Error in auto attendance", frappe.get_traceback())
#         else:
#             throw(f"Error While Marking Attendance \n{e}")
#             frappe.log_error("Error while marking attendance", frappe.get_traceback())



@frappe.whitelist()
def mark_attendance(attendance_date=None, company = None,is_scheduler=0, regularize_attendance = 0, attendance_id=None, regularize_start_time = None, regularize_end_time=0, emp_id=None, approved_attendance_request=None):
    """Method to mark attendance for prompt employee
    """
    try:
        
            
        prompt_company_name = fetch_company_name(prompt=1)
        indifoss_company_name = fetch_company_name(indifoss=1)
        employee_list = []
        employee_attendance_error = []
        if not is_scheduler:
            
            #* IF REGULARIZE ATTENDANCE THEN VALIDATING SPECIFIC PARAMETERS AND SHOW MESSAGE IF NOT FOUND
            if regularize_attendance: 
                if not attendance_date:                
                    throw("Please Provide Attendance Date")
                
                if not regularize_start_time:
                    throw("Please Provide Shift Start Time")
                
                if not regularize_end_time:
                    throw("Please Provide Shift End Time")
                
                if not emp_id:
                    throw("Please Provide Employee ID")
                    
                    
            prompt = 0
            indifoss = 0
                
            if prompt_company_name.get("error"):
                throw(prompt_company_name.get("message"))
            
            if indifoss_company_name.get("error"):
                throw(indifoss_company_name.get("message"))
                
            if not company:
                throw("Please Provide Company Name")
                
            if company == prompt_company_name.get("company_id"):
                company_id = prompt_company_name.get("company_id")
                prompt = 1
        
            if company == indifoss_company_name.get("company_id"):
                company_id = indifoss_company_name.get("company_id")
                indifoss = 1
            print(f"\n\n {indifoss} {prompt} \n\n")
            
            
            if regularize_attendance:
                employee_data = frappe.db.get_value("Employee", emp_id, ["name", "holiday_list", "custom_is_overtime_applicable"], as_dict=True)
                if not employee_data:
                    throw("No Employees Found")
                else:
                    shift_assignments = frappe.get_all(
                        "Shift Assignment",
                        filters={
                            "employee": employee_data.get("name"),
                            "docstatus": 1,
                            "start_date": ["<=", attendance_date]
                        },
                        or_filters=[
                            {"end_date": [">=", attendance_date]},
                            {"end_date": ["is", "not set"]}
                        ],
                        fields=["employee", "shift_type"],
                        limit = 1
                    )
                    if not shift_assignments:
                        throw(f"No Active Shift Assignment Found For Employee {employee_data.get('name')}")
                    else:
                        shift_type = shift_assignments[0].get("shift_type")
                        # if not shift_type:
                        #     throw(f"No Shift Type Assigned For Employee {employee_data.get('name')}")
                        employee_data.update({
                            "shift_type": shift_type,
                            "late_entry_grace_period": frappe.db.get_value("Shift Type", shift_type, "late_entry_grace_period")
                        })
            else:
                # ? GET EMPLOYEE
                if emp_id:
                    employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id, "name":emp_id}, ["name", "holiday_list", "custom_is_overtime_applicable"])
                else:
                    employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id}, ["name", "holiday_list", "custom_is_overtime_applicable"])

                #? GET ALL EMPLOYEE IDS
                employee_ids = [emp.name for emp in employee_list]

                #? FETCH SHIFT ASSIGNMENTS FOR TARGET DATE (INCLUDING OPEN-ENDED SHIFTS)
                if attendance_date:
                    shift_assignments = frappe.get_all(
                        "Shift Assignment",
                        filters={
                            "employee": ["in", employee_ids],
                            "docstatus": 1,
                            "start_date": ["<=", attendance_date]
                        },
                        or_filters=[
                            {"end_date": [">=", attendance_date]},
                            {"end_date": ["is", "not set"]}
                        ],
                        fields=["employee", "shift_type"]
                    )
                else:
                    return
                #? GET UNIQUE SHIFT TYPES
                shift_types = list({s.shift_type for s in shift_assignments if s.shift_type})
                
                #? FETCH LATE ENTRY GRACE PERIOD FROM SHIFT TYPE
                shift_type_map = frappe.db.get_all(
                    "Shift Type",
                    filters={"name": ["in", shift_types]},
                    fields=["name", "late_entry_grace_period"],
                    as_list=False
                )
                print(f"\n\n shift type map {shift_type_map} \n\n")
                shift_type_map = {st["name"]: st["late_entry_grace_period"] for st in shift_type_map}

                #? MAKE SHIFT MAP WITH SHIFT TYPE + GRACE PERIOD
                shift_map = {}
                for s in shift_assignments:
                    shift_map[s.employee] = {
                        "shift_type": s.shift_type,
                        "late_entry_grace_period": shift_type_map.get(s.shift_type)
                    }
                print(f"\n\n shift map {shift_map} \n\n")
                #? ENSURE ALL EMPLOYEES ARE PRESENT (DEFAULT NONE IF NOT ASSIGNED)
                for emp in employee_ids:
                    if emp not in shift_map:
                        shift_map[emp] = {
                            "shift_type": None,
                            "late_entry_grace_period": 0
                        }

                #? ENRICH EMPLOYEE LIST WITH SHIFT INFO
                for emp in employee_list:
                    emp.update(shift_map.get(emp.name, {"shift_type": None, "late_entry_grace_period": None}))

                    if not employee_list:
                        throw("No Employees Found")
                if prompt:
                    grace_time_for_insufficient_hours = frappe.db.get_single_value("HR Settings", "custom_daily_hours_criteria_for_penalty_for_prompt") or 0
                elif indifoss:
                    grace_time_period_for_late_coming = frappe.db.get_single_value("HR Settings", "custom_grace_time_period_for_late_coming_for_indifoss") or 0
            
        else:
            
            if prompt_company_name.get("error"):
                frappe.log_error("Error in fetch_company_name method",prompt_company_name.get("message"))
                return 0
            
            if indifoss_company_name.get("error"):
                frappe.log_error("Error in fetch_company_name method", indifoss_company_name.get("message"))
                return 0

            prompt_company_id = prompt_company_name.get("company_id")
            indifoss_company_id = indifoss_company_name.get("company_id")
            if emp_id:
                employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": company_id, "name":emp_id}, ["name", "holiday_list", "custom_is_overtime_applicable"])
            else:
                employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": ["in", [prompt_company_id, indifoss_company_id]]}, ["name", "holiday_list", "custom_is_overtime_applicable", "company"])
            frappe.log_error("mark_attendance_employee_list", f"\n\n employee list {employee_list} \n\n")
            #? GET ALL EMPLOYEE IDS
            employee_ids = [emp.name for emp in employee_list]
            frappe.log_error("mark_attendance_employee_date", f"Employee Date: {attendance_date}")
            #? FETCH SHIFT ASSIGNMENTS FOR TARGET DATE (INCLUDING OPEN-ENDED SHIFTS)
            if attendance_date:
                shift_assignments = frappe.get_all(
                    "Shift Assignment",
                    filters={
                        "employee": ["in", employee_ids],
                        "docstatus": 1,
                        "start_date": ["<=", attendance_date]
                    },
                    or_filters=[
                        {"end_date": [">=", attendance_date]},
                        {"end_date": ["is", "not set"]}
                    ],
                    fields=["employee", "shift_type"]
                )
            else:
                return
            print(f"\n\n shift assignments {shift_assignments} \n\n")
            #? GET UNIQUE SHIFT TYPES
            shift_types = list({s.shift_type for s in shift_assignments if s.shift_type})
            print(f"\n\n shift types {shift_types} \n\n")   
            #? FETCH LATE ENTRY GRACE PERIOD FROM SHIFT TYPE
            shift_type_map = frappe.db.get_all(
                "Shift Type",
                filters={"name": ["in", shift_types]},
                fields=["name", "late_entry_grace_period"],
                as_list=False
            )
            shift_type_map = {st["name"]: st["late_entry_grace_period"] for st in shift_type_map}

            #? MAKE SHIFT MAP WITH SHIFT TYPE + GRACE PERIOD
            shift_map = {}
            for s in shift_assignments:
                shift_map[s.employee] = {
                    "shift_type": s.shift_type,
                    "late_entry_grace_period": shift_type_map.get(s.shift_type)
                }
            print(f"\n\n shift map {shift_map} \n\n")
            
            #? ENSURE ALL EMPLOYEES ARE PRESENT (DEFAULT NONE IF NOT ASSIGNED)
            for emp in employee_ids:
                if emp not in shift_map:
                    shift_map[emp] = {
                        "shift_type": None,
                        "late_entry_grace_period": 0
                    }

            #? ENRICH EMPLOYEE LIST WITH SHIFT INFO
            for emp in employee_list:
                emp.update(shift_map.get(emp.name, {"shift_type": None, "late_entry_grace_period": None}))

            if not employee_list:
                frappe.log_error("Error in mark_attendance_for_prompt", "No Employee Found")    
            
        grace_time_for_insufficient_hours_for_prompt = frappe.db.get_single_value("HR Settings", "custom_daily_hours_criteria_for_penalty_for_prompt") or 0
        
        grace_time_period_for_late_coming_for_indifoss = frappe.db.get_single_value("HR Settings", "custom_grace_time_period_for_late_coming_for_indifoss") or 0
            
        
        mark_attendance_date = getdate(attendance_date) if attendance_date else getdate(add_days(today(), -1))
        str_mark_attendance_date = mark_attendance_date.strftime("%Y-%m-%d")
        
        frappe.log_error(f"mark_attendance_update", f"Scheduler Mark Attendance Started for date {attendance_date}")
        

        day_start_time = get_datetime(mark_attendance_date)
        day_end_time = get_datetime(str_mark_attendance_date + " 23:59:59")     

        if not regularize_attendance:
            for employee_data in employee_list:
                try:
                    if is_scheduler:
                        frappe.log_error(f"mark_attendance_processing_employee", f"{employee_data.get('name')}")
                        if employee_data.get("company") == prompt_company_id:
                            grace_time_period_for_late_coming_for_prompt = employee_data.get("late_entry_grace_period", 0)
                            if employee_data.get("shift_type") is not None:
                                attendance(
                                    employee_data,
                                    mark_attendance_date,
                                    str_mark_attendance_date,
                                    day_start_time,
                                    day_end_time,
                                    grace_time_period_for_late_coming_for_prompt,
                                    grace_time_for_insufficient_hours = grace_time_for_insufficient_hours_for_prompt,
                                    prompt = 1,
                                    indifoss=0,
                                    regularize_attendance=0, 
                                    attendance_id=None,
                                    regularize_start_time=None,
                                    regularize_end_time=None,
                                    approved_attendance_request = approved_attendance_request
                                )
                            else:
                                if is_scheduler:
                                    frappe.log_error(f"Shift is Not Assigned For Employee {employee_data.get('name')}")
                                else:
                                    frappe.log_error(f"Shift is Not Assigned For Employee {employee_data.get('name')}")
                                    employee_attendance_error.append(employee_data.get("name"))

                        elif employee_data.get("company") == indifoss_company_id:
                            
                            
                            attendance(
                                employee_data,
                                mark_attendance_date,
                                str_mark_attendance_date,
                                day_start_time,
                                day_end_time,
                                grace_time_period_for_late_coming_for_indifoss,
                                grace_time_for_insufficient_hours = grace_time_period_for_late_coming_for_indifoss,
                                prompt=0,
                                indifoss = 1,
                                regularize_attendance=0, 
                                attendance_id=None,
                                regularize_start_time=None,
                                regularize_end_time=None,
                                approved_attendance_request=approved_attendance_request
                            )
                    else:
                        grace_time_period_for_late_coming = employee_data.get("late_entry_grace_period", 0)
                        if employee_data.get("shift_type") is not None:
                            attendance(
                                employee_data,
                                mark_attendance_date,
                                str_mark_attendance_date,
                                day_start_time,
                                day_end_time,
                                grace_time_period_for_late_coming,
                                grace_time_for_insufficient_hours if prompt else 0,
                                prompt = prompt,
                                indifoss = indifoss,
                                regularize_attendance=0, 
                                attendance_id=None,
                                regularize_start_time=None,
                                regularize_end_time=None,
                                approved_attendance_request=approved_attendance_request
                            )
                        else:
                            if is_scheduler:
                                    frappe.log_error(f"Shift is Not Assigned For Employee {employee_data.get('name')}")
                            else:
                                frappe.log_error(f"Shift is Not Assigned For Employee {employee_data.get('name')}")
                                employee_attendance_error.append(employee_data.get("name"))
                except Exception as emp_exc:
                    frappe.log_error(f"Error marking attendance for employee {employee_data.get('name')}", frappe.get_traceback())
                    employee_attendance_error.append(employee_data.get("name"))
                    continue
            
            if employee_attendance_error:
                frappe.log_error("auto_attendance_scheduler", f"error while creating attendance for this employees {employee_attendance_error} ")
                
        elif regularize_attendance:
            if not indifoss:
                print(f"\n\n employee_data {employee_data} \n\n")
                grace_time_period_for_late_coming = employee_data.get("late_entry_grace_period", 0)
                if employee_data.get("shift_type") is not None:
                    attendance(
                                employee_data,
                                mark_attendance_date,
                                str_mark_attendance_date,
                                day_start_time,
                                day_end_time,
                                grace_time_period_for_late_coming,
                                grace_time_for_insufficient_hours_for_prompt if prompt else 0,
                                prompt = prompt,
                                indifoss = indifoss,
                                regularize_attendance = regularize_attendance,
                                attendance_id = attendance_id,
                                regularize_start_time = regularize_start_time,
                                regularize_end_time = regularize_end_time,
                                approved_attendance_request = approved_attendance_request
                                )
                else:
                    print(f"\n\n no shift type for this employee {employee_data.get('name')} \n\n")
                    if is_scheduler:
                        frappe.log_error(f"Shift is Not Assigned For Employee {employee_data.get('name')}")
                    else:
                        frappe.log_error(f"Shift is Not Assigned For Employee {employee_data.get('name')}")
                        employee_attendance_error.append(employee_data.get("name"))
        if employee_attendance_error:
            frappe.msgprint(
                "Attendance could not be marked for some employees due to errors. "
                "Please check the Error Log for detailed information."
            )
    
    except Exception as e:
        if is_scheduler:
            frappe.log_error("Error While Marking Attendance", frappe.get_traceback())
        else:
            frappe.log_error("Error While Marking Attendance", frappe.get_traceback())
            if regularize_attendance:
                throw(str(e))
            
def attendance(employee_data, mark_attendance_date, str_mark_attendance_date, day_start_time, day_end_time, grace_time_period_for_late_coming, grace_time_for_insufficient_hours=0, prompt=0, indifoss=0, regularize_attendance=0, attendance_id=None,   regularize_start_time=None, regularize_end_time=None, approved_attendance_request=None):

    # Prepare filters dictionary first
    shift_filters = {
        "docstatus": 1,
        "status": "Active",
        "employee": employee_data.get("name"),
        "start_date": ["<=", mark_attendance_date]
    }

    # Print the filters
    print(f"[DEBUG] Shift Assignment Filters: {shift_filters}")

    # Now execute the query
    assigned_shift = frappe.db.get_all(
        "Shift Assignment",
        shift_filters,
        ["name", "shift_type"],
        order_by="creation desc",
        limit=1
    )

    # Print result if found
    if assigned_shift:
        print(f"[DEBUG] Assigned Shift Found: {assigned_shift[0]['name']} | Shift Type: {assigned_shift[0]['shift_type']}")
    else:
        print("[DEBUG] No active shift assignment found.")

    

    #* If no shift assigned then move to next employee
    if not assigned_shift:
        print(f"\n\n no assigned shift \n\n")
        return 0
    
    #* Checking if attendance exists then move to another employee
    if not regularize_attendance:
        attendance_exists = frappe.db.exists("Attendance", {"employee": employee_data.get("name"), "docstatus":["!=", 2],"attendance_date": mark_attendance_date, "status": ["!=", "Half Day"]})
        if attendance_exists:
            return 0
    
    #* CHECKING IS THERE ANY HALF DAY ATTENDANCE OR NOT
    half_day_attendance = frappe.db.get_value("Attendance", {"employee": employee_data.get("name"), "docstatus":["!=", 2],"attendance_date": mark_attendance_date, "status": "Half Day", "leave_application": ["is", "set"]}, ["name", "custom_half_day_time"], as_dict=True)
    

    if not half_day_attendance:
        is_half_day_attendance_with_out_leave_application = frappe.db.exists("Attendance",{"employee": employee_data.get("name"), "attendance_date": mark_attendance_date, "status": "Half Day"})
        
        if is_half_day_attendance_with_out_leave_application and not regularize_attendance:
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
            shift_start_datetime = middle_datetime 
            
        elif half_day_attendance.get("custom_half_day_time") == "Second":
            shift_end_datetime = middle_datetime
    
    if is_half_day:
        frappe.log_error("attendance", f"Half Day Attendance {half_day_attendance.get('name')}")
    else:
        frappe.log_error("attendance", f"Not A half Day Attendance {employee_data.get('name')}")
            
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
    create_penalty = 0
    late_entry_with_grace_period = 0
    
    
    if not in_type_emp_checkin and not out_type_emp_checkin and not regularize_attendance:
        holiday_or_weekoff = is_holiday_or_weekoff(employee_data.get("name"), mark_attendance_date)
        
        if not holiday_or_weekoff.get("is_holiday") and not holiday_or_weekoff.get("is_weekoff"):
            if indifoss:
                print(f"\n\n No Attendance \n\n")
                leave_type = frappe.db.get_value("Leave Type", {"is_lwp": 1}, "name")
                
                create_employee_penalty(
                    employee_data.get("name"),
                    mark_attendance_date,
                    1,
                    leave_type=leave_type,
                    lwp_leave=1,
                    for_no_attendance = 1
                    )
            return 0            
        if holiday_or_weekoff.get("is_holiday"):
            return 0
        if holiday_or_weekoff.get("is_weekoff"):
            attendance_status = "WeekOff"
        
    
    if in_type_emp_checkin or regularize_attendance:
        
        if in_type_emp_checkin:
            in_type_emp_checkin_id = in_type_emp_checkin[0].get("name")
        
        if regularize_attendance:
            in_datetime = regularize_start_time
        else:
            in_datetime = in_type_emp_checkin[0].get("time")
            
        
    if out_type_emp_checkin or regularize_attendance:
        if out_type_emp_checkin:
            out_type_emp_checkin_id = out_type_emp_checkin[0].get("name")
            
        if regularize_attendance:
            out_datetime = regularize_end_time
        else:
            out_datetime = out_type_emp_checkin[0].get("time")
    
    if in_datetime and out_datetime:
        
        work_duration = out_datetime - in_datetime
        
        work_hours = work_duration.total_seconds() / 3600
        final_working_hours = round(work_hours, 1)
        
        total_minutes = int(work_duration.total_seconds())
        
        formatted_working_hours = format_duration(total_minutes)
        
        # ! ATTENDANCE STATUS & PENALTY APPLICATION BASED ON FINAL WORKING HOURS
        print("Employee:",employee_data)
        print(f"[DEBUG] Final Working Hours: {final_working_hours}")
        print(f"[DEBUG] Thresholds - Half Day: {half_day_threshold}, Absent: {absent_threshold}")
        print(f"[DEBUG] Grace Time for Insufficient Hours (Prompt): {grace_time_for_insufficient_hours}")

        if final_working_hours < half_day_threshold and final_working_hours > absent_threshold:
            attendance_status = "Half Day"
            print(f"[DEBUG] Attendance Status set to: {attendance_status}")

            if prompt:
                print("[DEBUG] Prompt is enabled, checking grace time condition...")
                if final_working_hours < grace_time_for_insufficient_hours:
                    apply_penalty = 1
                    print(f"[DEBUG] Working hours below grace time ({grace_time_for_insufficient_hours}). Penalty will be applied.")
                else:
                    print(f"[DEBUG] Working hours above grace time. No penalty applied.")
        else:
            if final_working_hours < absent_threshold:
                attendance_status = "Absent"
                apply_penalty = 1
                print(f"[DEBUG] Attendance Status set to: {attendance_status}. Penalty will be applied.")
            else:
                if not is_half_day:
                    attendance_status = "Present"
                    print(f"[DEBUG] Attendance Status set to: {attendance_status}. No penalty applied.")
                else:
                    attendance_status = "Half Day"

        
        
        if prompt and is_overtime_applicable:
            
            if is_half_day:
                ot_duration = overtime_duration(out_datetime, shift_end_datetime, is_half_day = 1)
            else:
                ot_duration = overtime_duration(out_datetime, shift_end_time)
            
            print(f"\n\n OT DURATION  {employee_data.get('name')} {ot_duration}\n\n")
            frappe.log_error(f"OT DURATION {employee_data.get('name')}", f"\n\n OT DURATION  {employee_data.get('name')} {ot_duration}\n\n")    
        
        if not is_half_day:
            late_entry_and_apply_penalty = is_late_entry(in_datetime, shift_start_time, grace_time_period_for_late_coming)
        else:
            late_entry_and_apply_penalty = is_late_entry(in_datetime, shift_start_datetime, grace_time_period_for_late_coming, is_half_day=1)
        
        late_entry = late_entry_and_apply_penalty.get("is_late_entry")
        apply_penalty = late_entry_and_apply_penalty.get("apply_penalty")
        late_entry_with_grace_period = late_entry_and_apply_penalty.get("is_late_entry_with_grace_period")
        
        if not is_half_day:
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
        if not is_half_day:
            shift_end_datetime = get_datetime(out_datetime.date()) + shift_end_time
        if out_datetime < shift_end_datetime:
            is_early_exit = 1
        is_only_one_record = 1
            
    
    
    attendance_request = frappe.db.get_all("Attendance Request", {"docstatus":1, "custom_status":"Approved", "employee": employee_data.get("name"), "from_date": ["<=", mark_attendance_date], "to_date":[">=", mark_attendance_date]}, ["name", "reason"], limit=1)
    
    attendance_type = None
    if attendance_request:
            attendance_type = attendance_request[0].get("reason")
    
    penalty_id = None

    if is_only_one_record:
        attendance_status = "Mispunch"
        if indifoss:
            leave_type = frappe.db.get_value("Leave Type", {"is_lwp": 1}, "name")            
            penalty_id = create_employee_penalty(
                    employee_data.get("name"),
                    mark_attendance_date,
                    1,
                    leave_type=leave_type,
                    lwp_leave=1,
                    for_miss_punch = 1
            )
            attendance_status = "Absent"
        remarks = "Only single record found"
    
    if attendance_status in ["Half Day", "Absent"] and not apply_penalty and prompt:

            if not is_half_day or (is_half_day and attendance_status == "Absent"):
                apply_penalty = 1
    
    if is_half_day or attendance_id:
            if not attendance_id:
                attendance_id = frappe.db.get_value("Attendance", {"employee": employee_data.get("name"), "attendance_date": mark_attendance_date,"docstatus":["!=", 2]}, "name")
            
            if attendance_id:
                update_attendance(attendance_id, {
                    "custom_type": attendance_type,
                    "custom_work_hours": formatted_working_hours,
                    "working_hours": final_working_hours,
                    "custom_overtime": ot_duration,
                    "status": attendance_status,
                    "late_entry": late_entry,
                    "early_exit": is_early_exit,
                    "custom_late_entry_with_grace_period": late_entry_with_grace_period,
                    "in_time" : in_datetime if in_type_emp_checkin or regularize_start_time else None,
                    "out_time" : out_datetime if out_type_emp_checkin or regularize_end_time else None,
                    "custom_checkin_time" : in_datetime if in_type_emp_checkin else None,
                    "custom_checkout_time" : out_datetime if out_type_emp_checkin else None,
                    "custom_remarks" : remarks,
                    "custom_employee_checkin" : in_type_emp_checkin_id if in_type_emp_checkin else None,
                    "custom_employee_checkout" : out_type_emp_checkin_id if out_type_emp_checkin else None,
                                                            
                },
                employee_id=employee_data.get("name"),
                indifoss=indifoss,
                regularize_attendance=regularize_attendance,
                attendance_date=mark_attendance_date
                )
            else:
                update_attendance(half_day_attendance.get("name"), {
                    "custom_type": attendance_type,
                    "custom_work_hours": formatted_working_hours,
                    "working_hours": final_working_hours,
                    "custom_overtime": ot_duration,
                    "late_entry": late_entry,
                    "custom_late_entry_with_grace_period": late_entry_with_grace_period,
                    "early_exit": is_early_exit,
                    "in_time" : in_datetime if in_type_emp_checkin else None,
                    "out_time" : out_datetime if out_type_emp_checkin else None,
                    "custom_checkin_time" : in_datetime if in_type_emp_checkin else None,
                    "custom_checkout_time" : out_datetime if out_type_emp_checkin else None,
                    "custom_remarks" : remarks,
                    "custom_employee_checkin" : in_type_emp_checkin_id if in_type_emp_checkin else None,
                    "custom_employee_checkout" : out_type_emp_checkin_id if out_type_emp_checkin else None

                },
                employee_id=employee_data.get("name"),
                indifoss=indifoss,
                regularize_attendance=regularize_attendance,
                attendance_date=mark_attendance_date
                )
    else:
        print(f"\n Creating Attendance \n\n")
        create_attendance(
            employee_data.get("name"),
            mark_attendance_date,
            attendance_status,
            custom_type = attendance_type,
            custom_work_hours=formatted_working_hours,
            working_hours=final_working_hours,
            custom_overtime = ot_duration,
            late_entry = late_entry,
            custom_late_entry_with_grace_period =late_entry_with_grace_period,
            early_exit = is_early_exit,
            shift = shift_type,
            in_time = in_datetime if in_type_emp_checkin or regularize_start_time else None,
            out_time = out_datetime if out_type_emp_checkin or regularize_end_time else None,
            custom_checkin_time = in_datetime if in_type_emp_checkin else '',
            custom_checkout_time = out_datetime if out_type_emp_checkin else '',
            custom_remarks = remarks,
            custom_employee_checkin = in_type_emp_checkin_id if in_type_emp_checkin else None,
            custom_employee_checkout = out_type_emp_checkin_id if out_type_emp_checkin else None,
            custom_employee_penalty_id = penalty_id,
            regularize_attendance=regularize_attendance,
            prompt=prompt,
            indifoss=indifoss,
            approved_attendance_request = approved_attendance_request
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
def overtime_duration(employee_out_time, shift_end_time, is_half_day=0):
    """ Method to calculate overtime duration
    """
    
    overtime_details = frappe.db.get_all("Overtime Details", {"parenttype": "HR Settings"}, ["from_time", "to_time", "final_time"])
    if not is_half_day:
        shift_end_time = get_datetime(employee_out_time.date()) + shift_end_time
    
    overtime = employee_out_time - shift_end_time
    
    overtime_float_value = round(overtime.total_seconds() / 3600, 2)
    
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
    if not is_half_day:
        shift_start_datetime = get_datetime(employee_in_datetime.date()) + shift_start_time
    else:
        shift_start_datetime = shift_start_time
    time_diff = employee_in_datetime - shift_start_datetime
    late_minutes = int(time_diff.total_seconds() // 60)
    # ? ADD LATE MINUTES WITH GRACE TIME TO CHECK IF THE EMPLOYEE IS LATE ENTRY ONLY OR LATE ENTRY WITH PENALTY
    
    return {"is_late_entry": 1 if late_minutes > grace_time else 0, "apply_penalty": 1 if late_minutes > grace_time else 0, "is_late_entry_with_grace_period": 1 if late_minutes > 0 else 0}
    

def create_attendance(
    employee,
    attendance_date,
    status,
    custom_type=None,
    custom_work_hours = '',
    working_hours = 0.0,
    custom_overtime= 0.0,
    late_entry = 0,
    custom_late_entry_with_grace_period = 0,
    early_exit = 0,
    shift = '',
    in_time = None,
    out_time = None,
    custom_checkin_time = '',
    custom_checkout_time = '',
    custom_remarks = '',
    custom_employee_checkin = None,
    custom_employee_checkout = None,
    custom_employee_penalty_id = None,
    regularize_attendance = 0,
    prompt=0,
    indifoss=0,
    approved_attendance_request = None   
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
    attendance_doc.custom_late_entry_with_grace_period = custom_late_entry_with_grace_period
    attendance_doc.early_exit = early_exit
    attendance_doc.shift = shift
    attendance_doc.in_time = in_time
    attendance_doc.out_time = out_time
    attendance_doc.custom_checkin_time = custom_checkin_time
    attendance_doc.custom_checkout_time = custom_checkout_time
    attendance_doc.custom_remarks =custom_remarks
    attendance_doc.custom_employee_checkin = custom_employee_checkin
    attendance_doc.custom_employee_checkout = custom_employee_checkout
    
    attendance_doc.custom_employee_penalty_id = custom_employee_penalty_id
    if approved_attendance_request:
        attendance_doc.attendance_request = approved_attendance_request
    attendance_doc.insert(ignore_permissions=True)
    
    if indifoss and regularize_attendance:
        emp_penalty_id = frappe.db.get_value("Employee Penalty", {"employee": employee, "attendance": attendance_doc.name}, "name")
        if not emp_penalty_id:
            emp_penalty_id = frappe.db.get_value("Employee Penalty", {"employee": employee, "penalty_date": attendance_date}, "name")
        if emp_penalty_id:
            frappe.delete_doc("Employee Penalty", emp_penalty_id, ignore_permissions=True)
    if custom_employee_penalty_id:
        frappe.db.set_value("Employee Penalty", custom_employee_penalty_id, "attendance", attendance_doc.name)
    attendance_doc.submit()
    frappe.db.commit()


def update_attendance(attendance_id, update_values, employee_id=None,indifoss = 0, regularize_attendance = 0, attendance_date=None):
    """Method to Update Attendance
    """
    # attendance_doc = frappe.get_doc("Attendance", attendance_id)
    print(f"\n\n updating attendance {regularize_attendance, employee_id, indifoss}\n\n")
    if update_values:
        for fieldname, values in update_values.items():
            frappe.db.set_value("Attendance", attendance_id, fieldname, values)
    
        if indifoss and regularize_attendance:
            emp_penalty_id = frappe.db.get_value("Employee Penalty", {"employee": employee_id, "attendance": attendance_id}, "name")
            if not emp_penalty_id:
                emp_penalty_id = frappe.db.get_value("Employee Penalty", {"employee": employee_id, "penalty_date": attendance_date}, "name")
            if emp_penalty_id:
                frappe.db.set_value("Attendance", attendance_id, "custom_employee_penalty_id", '')
                frappe.delete_doc("Employee Penalty", emp_penalty_id, ignore_permissions=True)
    
    
    frappe.db.commit()
#*-------------------------------------------------------------------------------------------------------------------------------




def create_employee_penalty(
    employee, 
    penalty_date, 
    deduct_leave, 
    leave_type = None, 
    lwp_leave = 0.0, 
    for_no_attendance=0,
    for_miss_punch=0
    ):
    "Method to Create Employee penalty and add an entry to leave ledger entry"
    #* CREATING EMPLOYEE PENALTY
    penalty_doc = frappe.new_doc("Employee Penalty")
    penalty_doc.employee = employee
    penalty_doc.penalty_date = penalty_date
    penalty_doc.total_leave_penalty = deduct_leave

    penalty_doc.deduct_leave_without_pay = lwp_leave
    
    
        
    if leave_type:
        penalty_doc.leave_type = leave_type
        
    
    if for_no_attendance:
        penalty_doc.for_no_attendance = 1
        penalty_doc.remarks = f"Penalty for No Attendance Marked on {penalty_date}"
    
    if for_miss_punch:
        penalty_doc.remarks = f"Penalty for Miss punch Marked on {penalty_date}"
    penalty_doc.insert(ignore_permissions=True)
    return penalty_doc.name
import frappe

from frappe import throw
from frappe.utils import datetime, today
from datetime import timedelta
from prompt_hr.py.utils import fetch_company_name




def auto_attendance(attendance_date=None, is_scheduler = 0):
    """Method to create attendance for the specified date or current date.
    """
    try:
        pass
    except Exception as e:
        if is_scheduler:
            frappe.log_error("Error in auto attendance", frappe.get_traceback())
        else:
            throw(f"Error While Marking Attendance \n{e}")
            frappe.log_error("Error while marking attendance", frappe.get_traceback())


def mark_attendance_for_prompt(is_scheduler=0):
    """Method to mark attendance for prompt employee
    """
    prompt_company_name = fetch_company_name(prompt=1)
    
    if prompt_company_name.get("error"):
        
        if is_scheduler:
            frappe.log_error("Error in fetch_company_name method", prompt_company_name.get("message"))
        else:
            throw(prompt_company_name.get("message"))
    
    employee_list = frappe.db.get_all("Employee", {"status": "Active", "company": prompt_company_name.get("company_id")}, ["name", "holiday_list"])
    
    if not employee_list:
        throw("No Employees Found") if is_scheduler else frappe.log_error("Error in mark_attendance_for_prompt", "No Employee Found")    

def mark_attendance_for_indifoss():
    """Method to mark attendance for indifoss employee
    """
    pass



def str_to_timedelta(work_hours):
    if isinstance(work_hours, str):
        parts = work_hours.split(":")
        if len(parts) == 2:  # hh:mm format
            hours, minutes = map(int, parts)
            return timedelta(hours=hours, minutes=minutes)
        elif len(parts) == 3:  # hh:mm:ss format
            hours, minutes, seconds = map(int, parts)
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        else:
            raise ValueError("Invalid work_hours format")
    else:
        return work_hours
    


    

# Custom attendance flow
@frappe.whitelist(allow_guest=True)
def mark_attendance(date, shift):
    
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d').date()

    success_message_printed = False
    
    active_employees = frappe.db.get_all(
        "Employee",
        filters={
            "status": "Active",
            "employment_type": ["not in", ["Professional Contractor", "Labour Contractor", "Owner"]]
            },
        fields=["name"]
    )
    active_employee_names = [emp["name"] for emp in active_employees]

    # Get all shift assignment records
    emp_records = frappe.db.get_all(
        "Shift Assignment",
        filters={
            "status": "Active",
            "shift_type": shift,
            "start_date": ["<=", date],
            "end_date": ["is", "not set"],
            "employee": ["in", active_employee_names]  # Filter by active employees
        },
        fields=["employee", "start_date", "end_date"],
    )


    
    emp_records_with_end_date = frappe.db.get_all(
        "Shift Assignment",
        filters={
            "status": "Active",
            "shift_type": shift,
            "start_date": ["<=", date],
            "end_date": [">=", date],
            "employee": ["in", active_employee_names]  # Filter by active employees
        },
        fields=["employee", "start_date", "end_date"],
    )

    emp_records.extend(emp_records_with_end_date)
    
    
    employee_checkins = {}

    for emp in emp_records:
    
        emp_name = emp.employee
        emp_doc = frappe.get_doc("Employee", emp_name)
        emp_joining_date = emp_doc.get("date_of_joining")

        # Skip if employee's joining date is after the attendance date
        if emp_joining_date and emp_joining_date > date:
            continue

        checkin_records = frappe.db.get_all(
            "Employee Checkin",
            filters={
                "employee": emp_name,
                "shift": shift,
                "custom_date": date
            },
            fields=["employee", "name", "custom_date", "log_type"],
            order_by="custom_date"
        )
        
        if checkin_records:
            for checkin in checkin_records:
                date_key = checkin['custom_date']
                if emp_name not in employee_checkins:
                    employee_checkins[emp_name] = {}
                if date_key not in employee_checkins[emp_name]:
                    employee_checkins[emp_name][date_key] = []
                employee_checkins[emp_name][date_key].append({
                    'name': checkin['name'],
                    'log_type': checkin['log_type']
                })
                
        # If no checkin found for particular shift and there is no holiday on date then mark absent     
        else:
            holiday_list = frappe.db.get_value('Employee', emp_name, 'holiday_list')
            is_holiday = False
            
            if holiday_list:
                holiday_doc = frappe.get_doc('Holiday List', holiday_list)
                holidays = holiday_doc.get("holidays")
                
                for holiday in holidays:
                    holiday_dt = holiday.holiday_date
                    if date == holiday_dt:
                        is_holiday = True
                        break
            
            if not is_holiday:
                exists_atte = frappe.db.get_value('Attendance', {'employee': emp_name, 'attendance_date': date, 'docstatus': 1}, ['name'])
                if not exists_atte:
                    attendance = frappe.new_doc("Attendance")
                    attendance.employee = emp_name
                    attendance.attendance_date = date
                    attendance.shift = shift
                    attendance.status = "Absent"
                    attendance.custom_remarks = "No Checkin found"
                    attendance.insert(ignore_permissions=True)
                    attendance.submit()
                    frappe.db.commit()

    # Calculate working hours
    for emp_name, dates in employee_checkins.items():
        for checkin_date, logs in dates.items():
            first_checkin = None
            last_checkout = None
            first_chkin_time = None
            last_chkout_time = None
            total_work_hours = 0  
            final_OT = 0
            
            for log in logs:
                name = log['name']
                log_type = log['log_type']

                if log_type == "IN" and first_checkin is None:
                    first_checkin = name

                if log_type == "OUT":
                    last_checkout = name

            if first_checkin and last_checkout:
                chkin_datetime = frappe.db.get_value('Employee Checkin', first_checkin, 'time')
                chkout_datetime = frappe.db.get_value('Employee Checkin', last_checkout, 'time')

                first_chkin_time = frappe.utils.get_time(chkin_datetime)
                last_chkout_time = frappe.utils.get_time(chkout_datetime)


            working_hours_calculation_based_on = frappe.db.get_value("Shift Type", shift, "working_hours_calculation_based_on")
            shift_hours = frappe.db.get_value("Shift Type", shift, "custom_shift_hours")

            if working_hours_calculation_based_on == "First Check-in and Last Check-out":
                if first_checkin and last_checkout:
                    
                    work_hours = frappe.utils.time_diff(chkout_datetime, chkin_datetime)
                    total_work_hours += work_hours.total_seconds() / 3600
                    total_work_hours = f"{int(total_work_hours):02d}.{int((total_work_hours % 1) * 60):02d}"

                        

            elif working_hours_calculation_based_on == "Every Valid Check-in and Check-out":
                in_time = None
                total_seconds = 0 

                for log in logs:
                    name = log['name']
                    log_type = log['log_type']

                    if log_type == "IN" and in_time is None:
                        in_time = frappe.db.get_value('Employee Checkin', name, 'time')

                    if log_type == "OUT" and in_time:
                        out_time = frappe.db.get_value('Employee Checkin', name, 'time')

                        # Calculate work time for the pair
                        work_time = frappe.utils.time_diff(out_time, in_time)
                        total_work_hours += work_time.total_seconds() / 3600
                        total_seconds += work_time.total_seconds()  

                        in_time = None  # Reset for the next pair

                total_work_hours = f"{int(total_work_hours):02d}.{int((total_work_hours % 1) * 60):02d}"
                # Convert total work time from seconds to hours, minutes, and seconds
                total_hours = total_seconds // 3600
                total_seconds %= 3600
                total_minutes = total_seconds // 60
                total_seconds %= 60

                # Final work_hours in the format hour:minute:second
                work_hours = "{:02}:{:02}:{:02}".format(int(total_hours), int(total_minutes), int(total_seconds))


         
            # Calculate Overtime
            if work_hours:
                work_hours_timedelta = str_to_timedelta(work_hours)

            if work_hours_timedelta > shift_hours:
                diff = work_hours_timedelta - shift_hours
                total_seconds = abs(diff.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                final_OT = f"{int(hours):02}.{int(minutes):02}"
                # frappe.msgprint(f"Work Hours: {work_hours}")
                # frappe.msgprint(f"Shift Hours: {shift_hours}")
                # frappe.msgprint(f"Overtime: {final_OT}")
                                
            att_status = 'Present'
            att_remarks = ''
            att_late_entry = 0
            att_early_exit = 0

            late_entry_hours_final = 0
            early_exit_hours_final = 0
            # Calculate late entry, early exit and define status
            # Check late entry grace
            half_day_hour = frappe.db.get_value('Shift Type', shift, 'working_hours_threshold_for_half_day')
            absent_hour = frappe.db.get_value('Shift Type', shift, 'working_hours_threshold_for_absent')

            shift_start_time = frappe.db.get_value('Shift Type', shift, 'start_time')
            late_entry_grace_period = frappe.db.get_value('Shift Type', shift, 'late_entry_grace_period')
            shift_start_time = frappe.utils.get_time(shift_start_time)
            shift_start_datetime = datetime.combine(checkin_date, shift_start_time)
            grace_late_datetime = frappe.utils.add_to_date(shift_start_datetime, minutes=late_entry_grace_period)
            grace_late_time = grace_late_datetime.time()

            # Check early exit grace
            shift_end_time = frappe.db.get_value('Shift Type', shift, 'end_time')
            early_exit_grace_period = frappe.db.get_value('Shift Type', shift, 'early_exit_grace_period')
            shift_end_time = frappe.utils.get_time(shift_end_time)
            shift_end_datetime = datetime.combine(checkin_date, shift_end_time)
            grace_early_datetime = frappe.utils.add_to_date(shift_end_datetime, minutes=-early_exit_grace_period)
            grace_early_time = grace_early_datetime.time()
            

            # Determine checkout remarks and final status
            checkout_remarks = frappe.db.get_value('Employee Checkin', last_checkout, 'custom_remarks')
            if checkout_remarks == "Auto-Checkout":
                att_status = 'Absent'
                att_remarks = 'Auto-Checkout'
                total_work_hours = 0
                final_OT = 0
            else:
                if first_chkin_time > grace_late_time:
                    late_entry_timedelta = frappe.utils.time_diff(str(first_chkin_time), str(grace_late_time))
                    total_late_entry_seconds = late_entry_timedelta.total_seconds()

                    late_entry_hour = int(total_late_entry_seconds // 3600)
                    late_entry_minute = int((total_late_entry_seconds % 3600) // 60)
                    late_entry_hours_final = f"{late_entry_hour:02d}.{late_entry_minute:02d}"

                    att_status = 'Half Day'
                    # att_remarks = f"Late Entry, checked in after grace period of {late_entry_grace_period} minutes"
                    att_late_entry = 1

                if last_chkout_time < grace_early_time:

                    early_exit_timedelta = frappe.utils.time_diff(str(grace_early_time), str(last_chkout_time))
                    total_early_exit_seconds = early_exit_timedelta.total_seconds()

                    early_exit_hour = int(total_early_exit_seconds // 3600)
                    early_exit_minute = int((total_early_exit_seconds % 3600) // 60)
                    early_exit_hours_final = f"{early_exit_hour:02d}.{early_exit_minute:02d}"
                 
                    att_early_exit = 1



                if float(total_work_hours) < half_day_hour:
                    att_status = 'Half Day'
                if float(total_work_hours) < absent_hour:
                    att_status = 'Absent'

            # frappe.msgprint(str(emp_name))
            # frappe.msgprint(str(chkin_datetime))
            # frappe.msgprint(str(chkout_datetime))
            # frappe.msgprint(str(first_checkin))
            # frappe.msgprint(str(last_checkout))
            # frappe.msgprint(str(total_work_hours))
            # frappe.msgprint(str(final_OT))
            
            exists_atte = frappe.db.get_value('Attendance', {'employee': emp_name, 'attendance_date': checkin_date, 'docstatus': 1}, ['name'])
            if not exists_atte:
                
                
                attendance = frappe.new_doc("Attendance")
                attendance.employee = emp_name
                attendance.attendance_date = checkin_date
                attendance.shift = shift
                attendance.in_time = chkin_datetime
                attendance.out_time = chkout_datetime
                attendance.custom_employee_checkin = first_checkin
                attendance.custom_employee_checkout = last_checkout
                attendance.custom_work_hours = total_work_hours
                attendance.custom_overtime = final_OT
                attendance.status = att_status
                attendance.custom_remarks = att_remarks
                attendance.late_entry = att_late_entry
                attendance.early_exit = att_early_exit
                attendance.custom_late_entry_hours = late_entry_hours_final
                attendance.custom_early_exit_hours = early_exit_hours_final

                attendance.insert(ignore_permissions=True)
                attendance.submit()
                frappe.db.commit()

                if first_checkin:
                    frappe.db.set_value("Employee Checkin", first_checkin, "attendance", attendance.name)
                if last_checkout:
                    frappe.db.set_value("Employee Checkin", last_checkout, "attendance", attendance.name)

                frappe.msgprint("Attendance is Marked Successfully")
                
            else:
                formatted_date = checkin_date.strftime("%d-%m-%Y")
                attendance_link = frappe.utils.get_link_to_form("Attendance", exists_atte)
                frappe.msgprint(f"Attendance already marked for Employee:{emp_name} for date {formatted_date}: {attendance_link}")

           
  

@frappe.whitelist(allow_guest=True)
def set_attendance_date():
    todaydate = today()

    # Get holiday list of the company
    holiday_list = frappe.db.get_value('Company', 'CleVision Technologies Private Limited', 'default_holiday_list')

    # Check if today is a holiday in that holiday list
    is_holiday = frappe.db.exists("Holiday", {
        "holiday_date": todaydate,
        "parent": holiday_list
    })
    
    if not is_holiday:
        working_dates = get_previous_working_date()
   
        for working_date in working_dates:
            date = working_date
            shift_types = frappe.get_all("Shift Type", filters={'enable_auto_attendance':1},fields=['name'])
            if shift_types:
                for shifts in shift_types:
                    shift = shifts.name
                    mark_attendance(date, shift)



@frappe.whitelist(allow_guest=True)
def get_previous_working_date():
    buffer_days = frappe.db.get_single_value('HR Settings', 'custom_buffer_days_for_attendance') or 3

    # Generate a list of previous N dates excluding today
    check_dates = [frappe.utils.add_days(today(), -i) for i in range(1, int(buffer_days) + 1)]

    return check_dates





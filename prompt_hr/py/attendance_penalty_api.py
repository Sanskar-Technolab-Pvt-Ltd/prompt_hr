import frappe
from frappe.utils import getdate, today, add_to_date, add_days, get_datetime_str, format_date
from prompt_hr.py.utils import create_notification_log, get_employee_email
from prompt_hr.scheduler_methods import add_leave_ledger_entry
from hrms.hr.utils import get_holiday_dates_for_employee
from datetime import datetime, timedelta, time, date
from prompt_hr.scheduler_methods import send_penalty_warnings
from frappe.model.workflow import apply_workflow
from prompt_hr.py.leave_application import apply_sandwich_rule

def get_active_employees():
    return frappe.db.get_all("Employee", {"status": "Active"}, "name", pluck="name")


def check_if_day_is_valid(employee, date):
    return not frappe.db.exists(
        "Attendance Regularization", {"regularization_date": date, "employee": employee}
    )


@frappe.whitelist()
def prompt_employee_attendance_penalties():
    """
    MAIN METHOD: PROCESS ALL PENALTIES FOR ALL EMPLOYEES.
    """
    try:

        # ? GET ALL ACTIVE EMPLOYEES
        employees = get_active_employees()
        # ? SET TOMORROW DATE TO EMAIL DATE
        email_date = add_days(getdate(), -1)
        # ? GET HR SETTINGS
        hr_settings = frappe.get_single("HR Settings")
        # ? LATE COMING PENALTY CONFIGURATION
        try:
            late_coming_allowed_per_month = (
                hr_settings.custom_late_coming_allowed_per_month_for_prompt or 0
            )
        except Exception as e:
            late_coming_allowed_per_month = 0
            frappe.log_error(
                "Late Coming Allowed For Month", str(e)
            )
        try:
            late_coming_penalty_buffer_days = (
                hr_settings.custom_buffer_days_for_penalty or 0
            )
        except Exception as e:
            late_coming_penalty_buffer_days = 0
            frappe.log_error(
                "Buffer Days (Late Coming Penalty)", str(e)
            )
        
        late_coming_target_date = getdate(
            add_to_date(today(), days=-(int(late_coming_penalty_buffer_days)+1))
        )

        try:
            late_coming_penalty_enable = hr_settings.custom_enable_late_coming_penalty or 0
        except Exception as e:
            late_coming_penalty_enable = 0
            frappe.log_error(
                "Enable Late Coming Penalty", str(e)
            )

        # ? DAILY HOURS PENALTY CONFIGURATION
        try:
            daily_hours_penalty_buffer_days = (
                hr_settings.custom_buffer_days_for_penalty or 0
            )
        except Exception as e:
            daily_hours_penalty_buffer_days = 0
            frappe.log_error(
                "Buffer Days (Daily Hours Penalty)", str(e)
            )
        daily_hours_target_date = getdate(
            add_to_date(today(), days=-(int(daily_hours_penalty_buffer_days)+1))
        )
        try:
            daily_hour_penalty_enable = hr_settings.custom_enable_daily_hours_penalty
        except Exception as e:
            daily_hour_penalty_enable = 0
            frappe.log_error(
                "Enable Daily Hours Penalty", str(e)
            )

        # ? NO ATTENDANCE PENALTY CONFIGURATION
        try:
            no_attendance_penalty_buffer_days = (
                hr_settings.custom_buffer_days_for_penalty or 0
            )
        except Exception as e:
            no_attendance_penalty_buffer_days = 0
            frappe.log_error(
                "Buffer Days (No Attendance Penalty)", str(e)
            )
        no_attendance_target_date = getdate(
            add_to_date(today(), days=-(int(no_attendance_penalty_buffer_days)+1))
        )
        try:
            no_attendance_penalty_enable = hr_settings.custom_enable_no_attendance_penalty
        except Exception as e:
            no_attendance_penalty_enable = 0
            frappe.log_error(
                "Enable No Attendance Penalty", str(e)
            )

        # ? MIS-PUNCH PENALTY CONFIGURATION
        try:
            mispunch_penalty_buffer_days = (
                hr_settings.custom_buffer_days_for_penalty or 0
            )
        except Exception as e:
            mispunch_penalty_buffer_days = 0
            frappe.log_error(
                "Buffer Days (Mispunch Penalty)", str(e)
            )
        mispunch_penalty_target_date = getdate(
            add_to_date(today(), days=-(int(mispunch_penalty_buffer_days)+1))
        )
        try:
            mispunch_penalty_enable = hr_settings.custom_enable_mispunch_penalty
        except Exception as e:
            mispunch_penalty_enable = 0
            frappe.log_error(
                "Enable Mispunch Penalty", str(e)
            )

        # ! FETCH ALL LATE ENTRY PENALTY RECORDS FOR THE LAST BUFFER DAYS IF LATE ENTRY PENALTY ENABLE
        late_penalty = {}
        late_penalty_email_records = {}
        if late_coming_penalty_enable:
            try:
                late_penalty = process_late_entry_penalties_for_prompt(
                    employees,
                    late_coming_allowed_per_month,
                    late_coming_penalty_buffer_days,
                    "custom_late_coming_leave_penalty_configuration",
                    late_coming_target_date,
                    False
                )
            except Exception as e:
                frappe.log_error(
                    "Late Coming Penalty", str(e)
                )
            try:
                late_penalty_email_records = process_late_entry_penalties_for_prompt(
                    employees,
                    late_coming_allowed_per_month,
                    late_coming_penalty_buffer_days,
                    "custom_late_coming_leave_penalty_configuration",
                    email_date,
                    False
                
                )
            except Exception as e:
                frappe.log_error(
                    "Late Coming Penalty Email Records", str(e)
                )

        if late_penalty:
            try:
                create_penalty_records(late_penalty, late_coming_target_date)
            except Exception as e:
                frappe.log_error(
                    "Error in Late Penalty Creation", str(e)
                )

        # ? DAILY HOURS PERCENTAGE FOR PENALTY
        try:
            percentage_for_daily_hour_penalty = (
                hr_settings.custom_daily_hours_criteria_for_penalty_for_prompt
            )
        except Exception as e:
            percentage_for_daily_hour_penalty = 42
            frappe.log_error(
                "Percentage For Daily Hours Penalty", str(e)
            )

        # ! FETCH ALL DAILY HOURS PENALTY RECORDS FOR THE LAST BUFFER DAYS IF IT IS ENABLE
        daily_hour_penalty = {}
        daily_hours_email_records = {}
        if daily_hour_penalty_enable:
            try:
                daily_hour_penalty = process_daily_hours_penalties_for_prompt(
                    employees,
                    daily_hours_penalty_buffer_days,
                    daily_hours_target_date,
                    percentage_for_daily_hour_penalty,
                    "custom_daily_hour_leave_penalty_configuration",
                    False
                )
            except Exception as e:
                frappe.log_error(
                    "Daily Hours Penalty", str(e)
                )
            try:
                daily_hours_email_records = process_daily_hours_penalties_for_prompt(
                    employees,
                    daily_hours_penalty_buffer_days,
                    email_date,
                    percentage_for_daily_hour_penalty,
                    "custom_daily_hour_leave_penalty_configuration",
                    False
                )
            except Exception as e:
                frappe.log_error(
                    "Daily Hours Penalty Email Records", str(e)
                )

        if daily_hour_penalty:
            try:
                create_penalty_records(daily_hour_penalty, daily_hours_target_date)
            except Exception as e:
                frappe.log_error(
                    "Error in Daily Hour Penalty Creation", str(e)
                )

        # ! FETCH ALL NO ATTENDANCE PENALTY RECORDS FOR THE LAST BUFFER DAYS IF IT IS ENABLE
        no_attendance_penalty = {}
        no_attendance_email_records = {}
        if no_attendance_penalty_enable:
            try:
                no_attendance_penalty = process_no_attendance_penalties_for_prompt(
                    employees,
                    no_attendance_penalty_buffer_days,
                    no_attendance_target_date,
                    "custom_no_attendance_leave_penalty_configuration",
                    False
                )
            except Exception as e:
                frappe.log_error(
                    "No Attendance Penalty", str(e)
                )
            try:
                no_attendance_email_records = process_no_attendance_penalties_for_prompt(
                    employees,
                    no_attendance_penalty_buffer_days,
                    email_date,
                    "custom_no_attendance_leave_penalty_configuration",
                    False
                )
            except Exception as e:
                frappe.log_error(
                    "No Attendance Penalty Email Records", str(e)
                )

        if no_attendance_penalty:
            try:
                create_penalty_records(no_attendance_penalty, no_attendance_target_date)
            except Exception as e:
                frappe.log_error(
                    "Error in No Attendance Penalty Creation", str(e)
                )

        # ! FETCH ALL MIS-PUNCH PENALTY RECORDS FOR THE LAST BUFFER DAYS IF IT IS ENABLE
        mispunch_penalty = {}
        mispunch_penalty_email_records = {}
        if mispunch_penalty_enable:
            try:
                mispunch_penalty = process_mispunch_penalties_for_prompt(
                    employees,
                    mispunch_penalty_buffer_days,
                    mispunch_penalty_target_date,
                    "custom_attendance_mispunch_leave_penalty_configuration",
                    False
                )
            except Exception as e:
                frappe.log_error(
                    "Mispunch Penalty", str(e)
                )
            try:
                mispunch_penalty_email_records = process_mispunch_penalties_for_prompt(
                    employees,
                    mispunch_penalty_buffer_days,
                    email_date,
                    "custom_attendance_mispunch_leave_penalty_configuration",
                    False
                )
            except Exception as e:
                frappe.log_error(
                    "Mispunch Penalty Email Records", str(e)
                )

        # ! CREATE OR UPDATE PENALTY RECORDS IN THE DATABASE

        if mispunch_penalty:
            try:
                create_penalty_records(mispunch_penalty, mispunch_penalty_target_date)
            except Exception as e:
                frappe.log_error(
                    "Error in Mispunch Penalty Creation", str(e)
                )

        # ? MAP BUFFER DAYS FOR EMAIL RECORDS
        email_records = {
            "Late Coming": {
                "records": late_penalty_email_records,
                "buffer_days": late_coming_penalty_buffer_days,
            },
            "Daily Hours": {
                "records": daily_hours_email_records,
                "buffer_days": daily_hours_penalty_buffer_days,
            },
            "No Attendance": {
                "records": no_attendance_email_records,
                "buffer_days": no_attendance_penalty_buffer_days,
            },
            "Mispunch": {
                "records": mispunch_penalty_email_records,
                "buffer_days": mispunch_penalty_buffer_days,
            },
        }

        # ! CONSOLIDATE PENALTIES PER EMPLOYEE WITH BUFFER DAYS
        consolidated_email_records = {}
        for penalty_type, data in email_records.items():
            try:
                records = data["records"]
                buffer_days = data["buffer_days"]
            except Exception as e:
                frappe.log_error(
                    "Error in Consolidating Email Records", str(e)
                )
                continue

            if not records:
                continue
            try:
                for emp_id, emp_penalties in records.items():
                    try:
                        if check_employee_penalty_criteria(emp_id, emp_penalties.get("reason")):
                            att_date = emp_penalties.get("attendance_date")
                            attendance = emp_penalties.get("attendance", None)
                            if not att_date:
                                continue
                            # compute buffered email date
                            email_date_with_buffer = add_days(att_date, (int(buffer_days)+1))

                            if emp_id not in consolidated_email_records:
                                consolidated_email_records[emp_id] = {}

                            consolidated_email_records[emp_id][penalty_type] = {
                                "penalty_date": email_date_with_buffer,
                                "attendance": attendance,
                            }
                    except Exception as e:
                        frappe.log_error(
                            "Error in Consolidating Email Records", str(e)
                        )
                        continue
            except Exception as e:
                frappe.log_error(
                    "Error in Consolidating Email Records", str(e)
                )
                continue

        # ! SEND CONSOLIDATED WARNINGS
        all_email_details = []
        add_to_penalty_email = frappe.db.get_single_value("HR Settings", "custom_add_emails_to_penalty_emails_for_prompt")
        
        for emp_id, penalties in consolidated_email_records.items():
            try:
                email_details = send_penalty_warnings(emp_id, penalties, email_date)
                if not add_to_penalty_email:
                    if email_details and email_details.get("email"): 
                        frappe.sendmail(
                            recipients=[email_details.get("email")],
                            subject=email_details.get("subject"),
                            message=email_details.get("message"),
                        )
                        try:
                            create_notification_log(email_details.get("email"), email_details.get("subject"), email_details.get("message"), "Employee", emp_id)
                        except Exception as e:
                            frappe.log_error(
                                "Error in Creating Notification Log", str(e)
                            )
                else:
                    if email_details and email_details.get("email"):
                        clean_penalties = clean_dates(penalties)
                        email_details.update({
                            "data": {
                                "employee": emp_id,
                                "employee_name": frappe.db.get_value("Employee", emp_id, "employee_name"),
                                "email_type": "Attendance Penalty Warning",
                                "penalties": clean_penalties,
                                "attendance_date": clean_dates(email_date),
                            }
                        })
                        all_email_details.append(email_details)
            except Exception as e:
                frappe.log_error(
                    "Error in Sending Penalty Warnings", frappe.get_traceback()
                )
                continue
        
        
        if all_email_details and add_to_penalty_email:
            penalty_emails_doc = frappe.get_doc({  
                        "doctype": "Penalty Emails",
                        "status": "Not Sent",
                        "email_details": all_email_details,
                        "date": getdate(),
                        "remarks": f"Consolidated attendance penalty warnings generated on {format_date(getdate())} for attendance discrepancies dated {format_date(add_to_date(getdate(), days=-1))}. Penalties will be applied on {format_date(email_date_with_buffer)}."
                    })                
            penalty_emails_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
            
    except Exception as e:
        frappe.log_error(
            "Error in Employee Attendance Penalty: ",str(e)
        )

def process_late_entry_penalties_for_prompt(
    employees,
    late_coming_allowed_per_month,
    penalty_buffer_days,
    priority_field,
    target_date,
    custom_buffer_days,
    weekoff_change = False
):
    """
    Process late entry penalties for a given employee based on buffer days and attendance records.
    Returns a list of penalty entries.
    """
    penalty_entries = {}

    # ? GET LEAVE CONFIGURATION FOR LATE ENTRY PENALTY
    try:
        leave_priority = frappe.db.get_all(
            "Leave Penalty Configuration",
            filters={
                "parent": "HR Settings",
                "parenttype": "HR Settings",
                "parentfield": priority_field,
            },
            fields=[
                "penalty_deduction_type",
                "leave_type_for_penalty",
                "deduction_of_leave",
            ],
            order_by="idx asc",
        )
    except Exception as e:
        frappe.log_error(
            "Error in Leave Priority", str(e)
        )
        return penalty_entries

    # ? RETURN IF BUFFER NOT CONFIGURED AND NOT CUSTOM BUFFER DAYS
    if not penalty_buffer_days and not custom_buffer_days:
        return penalty_entries
    if custom_buffer_days:
        penalty_buffer_days = 0

    # ! CHECK TARGET DATE'S ATTENDANCE IS LATE OR NOT
    try:
        late_attendance_records = target_date_attendance_exists(
            employees, target_date, 1, 0, 0, 0
        )
    except Exception as e:
        frappe.log_error(
            "Error in Late Attendance Date Exists", str(e)
        )
    # ! SKIP IF TARGET DATE ATTENDANCE IS NOT LATE
    if not late_attendance_records:
        return []

    # ? EMPLOYEES WHO HAD LATE ENTRY ON TARGET DATE
    try:
        late_employees = list(late_attendance_records.keys())
    except Exception as e:
        frappe.log_error(
            "Error in Late Employees", str(e)
        )
        return penalty_entries

    # ? GET MONTH START DATE
    month_start_date = target_date.replace(day=1)
    prev_target_date = getdate(add_to_date(target_date, days=-1))

    #! SAFETY: HANDLE EMPTY EMPLOYEE LIST
    if not late_employees:
        prev_late_attendance_count = {}
    else:
        #! FETCH ATTENDANCE RECORDS WITH LATE ENTRY FROM MONTH START TO TARGET DATE
        try:
            prev_late_attendance_list = frappe.db.get_all(
                "Attendance",
                filters={
                    "employee": ["in", late_employees],
                    "docstatus": 1,
                    "late_entry": 1,
                    "status": ["not in", ["Absent", "On Leave", "Half Day", "WeekOff"]],
                    "attendance_date": ["between", [month_start_date, prev_target_date]],
                },
                fields=["employee", "name", "attendance_date"],
                order_by="attendance_date asc",
            )
        except Exception as e:
            frappe.log_error(
                "Error in Fetching Previous Late Attendance List", str(e)
            )
            return penalty_entries

        #! INIT COUNT FOR ALL EMPLOYEES TO ZERO (INCLUDES ZERO-RECORD EMPLOYEES)
        try:
            prev_late_attendance_count = {emp: 0 for emp in set(late_employees)}
        except Exception as e:
            prev_late_attendance_count = 0
            frappe.log_error(
                "Error in Initializing Previous Late Attendance Count", str(e)
            )

        #! INCREMENT COUNTS FROM QUERY RESULTS
        for rec in prev_late_attendance_list:
            try:
                emp = rec["employee"]
                prev_late_attendance_count[emp] += 1
            except Exception as e:
                frappe.log_error(
                    "Error in Incrementing Previous Late Attendance Count", str(e)
                )
                continue

    # ? IF PREV LATE ATTENDANCE COUNT IS EMPTY, RETURN EMPTY PENALTY LIST
    if not prev_late_attendance_count:
        return penalty_entries

    # ? PROCESS EACH EMPLOYEE WHO HAD LATE ENTRY
    # ? AND CHECK IF THEY EXCEED THE ALLOWED LATE COMING COUNT
    # ? IF YES, CALCULATE LEAVE DEDUCTIONS BASED ON PRIORITY CONFIGURATION
    # ? AND ADD TO PENALTY ENTRIES
    for employee, count in prev_late_attendance_count.items():
        try:

            attendance_request_exists = frappe.db.exists(
                "Attendance Request",
                {
                    "employee": employee,
                    "from_date": ["<=", target_date],
                    "to_date": [">=", target_date],
                    "custom_status": "Approved",
                    "docstatus": ["!=", 2],
                    "reason": "Partial Day",
                    "custom_partial_day_for": 'Late coming'
                },
            )

            # ? CHECK FOR OTHER ATTENDANCE REQUESTS (WFH, OD) AS EXEMPTION
            other_attendance_request_exists = frappe.db.exists(
                "Attendance Request",
                {
                    "employee": employee,
                    "from_date": ["<=", target_date],
                    "to_date": [">=", target_date],
                    "custom_status": "Approved",
                    "docstatus": ["!=", 2],
                    "reason": ["in",["Work From Home", "On Duty"]],
                },
            )


            if (
                count >= late_coming_allowed_per_month
                and not attendance_request_exists
                and not other_attendance_request_exists
                and not full_day_leave_exists(employee, target_date)
                and not half_day_leave_exist_first_half(employee, target_date)
            ):
                # ? CHECK HOLIDAY
                try:
                    if not weekoff_change:
                        if get_holiday_dates_for_employee(employee, target_date, target_date):
                            continue
                except Exception as e:
                    frappe.log_error(
                        f"Error in Getting Holiday Date",str(e)
                    )
                    continue

                # ? CHECK NO ATTENDANCE AND PENALTY IS CHECK IN EMPLOYEE MASTER
                try:
                    is_no_attendance_and_penalty = frappe.db.get_value("Employee", employee, "custom_no_attendance_and_penalty") or 0
                    if is_no_attendance_and_penalty:
                        continue
                except Exception as e:
                    frappe.log_error(
                        f"Error in Getting No Attendance and Penalty Value From Employee Master",str(e)
                    )
                    continue
                penalty_entries.update(
                    calculate_leave_deductions_based_on_priority(
                        employee=employee,
                        attendance_date=target_date,
                        deduction_amount=1.0,
                        reason="Late Coming",
                        penalizable_attendance=late_attendance_records[employee][
                            "attendance"
                        ],
                        remarks=f"Penalty for Late Entry on {target_date}",
                        leave_priority=leave_priority,
                    )
                )
        except Exception as e:
            frappe.log_error(
                "Error in Processing Late Entry Penalties", str(e)
            )
            continue

    return penalty_entries


# def calculate_late_entry_penalty_list(employee, penalizable_attendance, leave_priority):
#     """
#     Calculate penalty list for late entries using reusable leave deduction logic.
#     """
#     penalty_entries = []

#     deductions = calculate_leave_deductions_based_on_priority(
#             employee=employee,
#             deduction_amount=1.0,
#             reason="Late Coming",
#             penalizable_attendance = penalizable_attendance,
#             leave_priority=leave_priority
#     )
#     penalty_entries.extend(deductions)

#     return penalty_entries


def calculate_leave_deductions_based_on_priority(
    employee,
    attendance_date,
    deduction_amount,
    reason,
    penalizable_attendance,
    remarks,
    leave_priority=None,
):
    """
    CALCULATE LEAVE DEDUCTIONS BASED ON PRIORITY CONFIGURATION.
    RETURNS DICTIONARY WITH ATTENDANCE DATE AS KEY AND DETAILS AS VALUE.
    """
    if not leave_priority:
        return {}

    # ? GET REMAINING LEAVE BALANCES FOR THE EMPLOYEE
    try:
        leave_balances = get_remaining_leaves(employee)
    except Exception as e:
        frappe.log_error(
            "Error in Getting Remaining Leaves", str(e)
        )
        leave_balances = {}

    # ? ENSURE LEAVE BALANCES ARE NOT EMPTY
    for config in leave_priority:
        try:
            deduction_type = config.get("penalty_deduction_type")
            leave_type = config.get("leave_type_for_penalty")
            deduction_of_leave = config.get("deduction_of_leave")

            deduction_unit = 0.5 if deduction_of_leave == "Half Day" else 1.0
                    

            # ! CALCULATE LEAVE AMOUNT TO BE DEDUCTED
            leave_amount = min(deduction_amount, deduction_unit)
            sandwich_rule_applied = 0
            try:
                if reason == "No Attendance":
                    # ? CHECK FOR SANDWICH CRITERIA
                    custom_doc = frappe._dict(
                        employee=employee,
                        leave_type=leave_type,
                        workflow_state="Approved",
                        from_date=attendance_date,
                        to_date=attendance_date,
                    )
                    extra_days, extra_days_prev, extra_days_next = apply_sandwich_rule(
                            custom_doc,
                    )
                    if extra_days:
                        leave_amount += extra_days
                        sandwich_rule_applied = 1
            except:
                frappe.log_error(
                    "Error in Sandwich Rule", str(e)
                )
            if deduction_type == "Deduct Earned Leave":
                balance = leave_balances.get(leave_type, 0.0)
                # ? CHECK IF LEAVE BALANCE IS SUFFICIENT
                if balance >= leave_amount:
                    # ? RETURN PENALTY ENTRY DICTIONARY
                    return {
                        employee: {
                            "attendance": penalizable_attendance,
                            "attendance_date": attendance_date,
                            "leave_type": leave_type,
                            "leave_amount": leave_amount,
                            "reason": reason,
                            "leave_balance_before_application": balance,
                            "leave_ledger_entry": "",
                            "remarks": remarks,
                            "earned_leave": leave_amount,
                            "sandwich_rule_applied":sandwich_rule_applied
                        }
                    }

            elif deduction_type == "Deduct Leave Without Pay":
                # ? RETURN LEAVE WITHOUT PAY ENTRY DICTIONARY
                return {
                    employee: {
                        "attendance": penalizable_attendance,
                        "attendance_date": attendance_date,
                        "leave_type": "Leave Without Pay",
                        "leave_amount": leave_amount,
                        "reason": reason,
                        "leave_balance_before_application": 0,
                        "leave_ledger_entry": "",
                        "remarks": remarks,
                        "leave_without_pay": leave_amount,
                        "sandwich_rule_applied":sandwich_rule_applied
                    }
                }
        except Exception as e:
            frappe.log_error(
                "Error in calculate_leave_deductions_based_on_priority", str(e)
            )
            continue

    return {}


def get_remaining_leaves(employee):
    """
    GET A DICTIONARY OF REMAINING LEAVE BALANCES FOR ALL LEAVE TYPES OF AN EMPLOYEE.

    RETURNS:
        dict: {leave_type: total_leaves}
    """
    leave_ledger_entries = frappe.db.get_all(
        "Leave Ledger Entry",
        filters={"docstatus": 1, "employee": employee, "is_expired": 0},
        fields=["leave_type", "leaves"],
    )

    leave_balance_map = {}

    for entry in leave_ledger_entries:
        try:
            leave_type = entry["leave_type"]
            leaves = entry["leaves"]

            if leave_type in leave_balance_map:
                leave_balance_map[leave_type] += leaves
            else:
                leave_balance_map[leave_type] = leaves
        except Exception as e:
            frappe.log_error(
                "Error in get_remaining_leave", str(e)
            )
            continue

    return leave_balance_map


def target_date_attendance_exists(
    employees, target_date, late_entry=0, no_attendance=0, mispunch=0, daily_hour=0
):
    """
    RETURN A DICTIONARY WHERE KEY = EMPLOYEE ID
    VALUE = { "attendance_date": ..., "attendance": ... }
    FOR LATE ENTRY RECORDS ON THE GIVEN TARGET DATE.
    """
    # ? BUILD FILTERS DYNAMICALLY
    filters = {
        "employee": ["in", employees],
        "docstatus": 1,
        "attendance_date": target_date,
    }
    # ? ADD LATE ENTRY FILTER IF FETCHING LATE ENTRIES
    if late_entry:
        filters.update({"late_entry": 1})

    # ? ADD STATUS FILTERS FOR ALL OTHER CASES EXCEPT NO ATTENDANCE AND MISPUNCH
    if not no_attendance and not mispunch:
        if daily_hour:
            filters.update({"status": ["not in",["Absent","On Leave", "Mispunch", "WeekOff"]]})
        elif late_entry:
            filters.update({"status": ["not in",["Absent","On Leave", "WeekOff"]]})
        else:
            filters.update({"status": ["not in",["Absent","On Leave", "WeekOff"]]})

    # ? ADD MISPUNCH STATUS FILTER IF FETCHING MISPUNCH RECORDS
    if mispunch:
        filters.update({"status": "Mispunch"})

    try:
        # ? FETCH ATTENDANCE RECORDS FOR TARGET DATE FOR GIVEN EMPLOYEES
        attendance_list = frappe.get_all(
            "Attendance",
            filters=filters,
            fields=["employee", "name", "attendance_date", "working_hours"],
            order_by="attendance_date asc",
        )

        # ? BUILD DICTIONARY MAPPING EMPLOYEE → {ATTENDANCE_DATE, ATTENDANCE, WORKING_HOURS}
        attendance_dict = {
            rec["employee"]: {
                "attendance_date": rec["attendance_date"],
                "attendance": rec["name"],
                "working_hours": rec.get("working_hours", 0),
            }
            for rec in attendance_list
        }

        return attendance_dict if attendance_dict else None
    except Exception as e:
        frappe.log_error(
            "Error in Fetching Attendance List", str(e)
        )
        return None


def process_daily_hours_penalties_for_prompt(
    employees,
    penalty_buffer_days,
    target_date,
    percentage_for_daily_hour_penalty,
    priority_field,
    custom_buffer_days,
    weekoff_change = False
):
    """
    Process daily hours penalties for a given employee based on buffer days and attendance records.
    Returns a list of penalty entries.
    """
    penalty_entries = {}

    
    # ? RETURN IF BUFFER NOT CONFIGURED AND NOT CUSTOM BUFFER DAYS
    if not penalty_buffer_days and not custom_buffer_days:
        return penalty_entries
    if custom_buffer_days:
        penalty_buffer_days = 0

    # ! FETCH ATTENDANCE RECORDS FOR TARGET DATE
    try:
        daily_hours_records = target_date_attendance_exists(
            employees, target_date, 0, 0, 0, 1
        )
    except Exception as e:
        frappe.log_error(
            f"Error in Fetching Daily Hours Attendance Records", str(e)
        )
        return penalty_entries

    # ! SKIP IF TARGET DATE ATTENDANCE IS NOT THERE
    if not daily_hours_records:
        return []

    try:
        # ? REMOVE EMPLOYEES WHOSE SHIFT IS NOT ASSIGNED
        daily_hours_records = {
            emp: data
            for emp, data in daily_hours_records.items()
            if check_if_shift_is_assign(emp, target_date)
        }
    except Exception as e:
        frappe.log_error(
            f"Error in Checking Shift Assignment", str(e)
        )
        return penalty_entries

    try:
        # ! FILTER EMPLOYEES WHOSE DAILY HOURS ARE BELOW THRESHOLD
        daily_hours_records = get_below_threshold_daily_hours(
            daily_hours_records, percentage_for_daily_hour_penalty, target_date
        )
    except Exception as e:
        frappe.log_error(
            f"Error in Getting Below Threshold Daily Hours", str(e)
        )
        return penalty_entries

    below_threshold_employees = []
    try:
        # ? EMPLOYEES WHO HAD DAILY HOURS BELOW THRESHOLD ON TARGET DATE
        if daily_hours_records:
            below_threshold_employees = list(daily_hours_records.keys())
    except Exception as e:
        frappe.log_error(
            f"Error in Getting Below Threshold Employees", str(e)
        )
        return penalty_entries

    # ? LEAVE TYPES CONFIGURATION FOR DAILY HOURS PENALTY
    try:
        leave_priority = frappe.db.get_all(
            "Leave Penalty Configuration",
            filters={
                "parent": "HR Settings",
                "parenttype": "HR Settings",
                "parentfield": priority_field,
            },
            fields=[
                "penalty_deduction_type",
                "leave_type_for_penalty",
                "deduction_of_leave",
            ],
            order_by="idx asc",
        )
    except Exception as e:
        frappe.log_error(
            f"Error in Getting Leave Priority", str(e)
        )
        return penalty_entries

    # ? IF NOT BELOW THRESHOLD EMPLOYEES
    if not below_threshold_employees:
        return penalty_entries
    # ? CALCULATE LEAVE DEDUCTIONS BASED ON PRIORITY CONFIGURATION
    # ? AND ADD TO PENALTY ENTRIES
    for employee in below_threshold_employees:
        # ? CHECK FOR ATTENDANCE REQUESTS ON DUTY AS EXEMPTION
        try:
            attendance_request_exists = frappe.db.exists(
                "Attendance Request",
                {
                    "employee": employee,
                    "from_date": ["<=", target_date],
                    "to_date": [">=", target_date],
                    "custom_status": "Approved",
                    "docstatus": ["!=", 2],
                    "reason": "On Duty",
                },
            )
            if attendance_request_exists:
                continue
        except Exception as e:
            frappe.log_error(
                f"Error in Checking Attendance Request Existence", str(e)
            )
            continue
        # ? CHECK HOLIDAY
        try:
            if not weekoff_change:
                if get_holiday_dates_for_employee(employee, target_date, target_date):
                    continue
        except Exception as e:
            frappe.log_error(
                f"Error in Getting Holiday Date",str(e)
            )
            continue
        # ? CHECK LEAVE
        try:
            if full_day_leave_exists(employee, target_date):
                continue
        except Exception as e:
            frappe.log_error(
                f"Error in Checking Full Day Leave Existence",str(e)
            )
            continue

        # ? CHECK NO ATTENDANCE AND PENALTY IS CHECK IN EMPLOYEE MASTER
        try:
            is_no_attendance_and_penalty = frappe.db.get_value("Employee", employee, "custom_no_attendance_and_penalty") or 0
            if is_no_attendance_and_penalty:
                continue
        except Exception as e:
            frappe.log_error(
                f"Error in Getting No Attendance and Penalty Value From Employee Master",str(e)
            )
            continue

        try:
            penalty_entries.update(
                calculate_leave_deductions_based_on_priority(
                    employee=employee,
                    attendance_date=target_date,
                    deduction_amount=1.0,
                    reason="Insufficient Hours",
                    penalizable_attendance=daily_hours_records[employee]["attendance"],
                    remarks=f"Penalty for Insufficient Hours on {target_date}",
                    leave_priority=leave_priority,
                )
            )
        except Exception as e:
            frappe.log_error(
                f"Error in Calculating Leave Deductions", str(e)
            )
            continue

    return penalty_entries


def create_penalty_records(penalty_entries, target_date):
    """
    CREATE OR UPDATE PENALTY RECORDS IN THE DATABASE.

    penalty_entries format:
    {
        "EMP001": {
            "attendance": "HR-ATT-2025-08813",
            "attendance_date": date(2025, 8, 10),
            "leave_type": "Leave Without Pay",
            "leave_amount": 1.0,
            "reason": "Late Coming"
        },
        ...
    }
    """

    # ? GET LIST OF EMPLOYEES FROM THE PENALTY ENTRIES
    try:
        employee_list = list(penalty_entries.keys())
    except Exception as e:
        frappe.log_error("Error in Employee List", str(e))
        return

    if not employee_list:
        return

    # ? FETCH EXISTING PENALTIES FOR THE TARGET DATE
    try:
        existing_penalties = frappe.get_all(
            "Employee Penalty",
            filters={"employee": ["in", employee_list], "penalty_date": target_date, "is_leave_balance_restore":0},
            fields=["name", "employee"],
        )
        existing_penalties_map = {ep["employee"]: ep["name"] for ep in existing_penalties}
    except Exception as e:
        frappe.log_error("Error in Fetching Existing Penalties", str(e))
        existing_penalties_map = {}

    # ? GET LEAVE PERIOD DATA ONCE
    leave_period_data = frappe.db.get_value(
        "Leave Period",
        {
            "is_active": 1,
            "from_date": ["<=", target_date],
            "to_date": [">=", target_date],
        },
        ["name", "from_date", "to_date"],
        as_dict=True,
    )

    changes_made = False

    def handle_leave_ledger(details, employee):
        """CREATE LEAVE LEDGER ENTRY IF EARNED LEAVE IS PRESENT."""
        if details.get("earned_leave", 0) != 0:
            leave_allocation_id = get_leave_allocation_id(
                employee, details["leave_type"], target_date
            )
            ledger_entry_id = add_leave_ledger_entry(
                employee=employee,
                leave_type=details["leave_type"],
                leave_allocation_id=leave_allocation_id,
                leave_period_data=leave_period_data,
                earned_leave=details["leave_amount"],
            )
            details["leave_ledger_entry"] = ledger_entry_id

    # ? LOOP AND PROCESS PENALTIES
    for employee, details in penalty_entries.items():
        # ? SKIP IF ATTENDANCE REQUEST EXIST AND IT IS PENDING
        try:
            if check_employee_penalty_criteria(employee, details["reason"]):
                if employee in existing_penalties_map:
                    penalty_doc = frappe.get_doc(
                        "Employee Penalty", existing_penalties_map[employee]
                    )
                    existing_reasons = {
                        row.reason for row in penalty_doc.leave_penalty_details
                    }
                    if details["reason"] not in existing_reasons:
                        handle_leave_ledger(details, employee)
                        penalty_doc.deduct_earned_leave += details.get("earned_leave", 0)
                        penalty_doc.deduct_leave_without_pay += details.get(
                            "leave_without_pay", 0
                        )
                        if not penalty_doc.sandwich_rule_applied:
                            penalty_doc.sandwich_rule_applied = details.get(
                                "sandwich_rule_applied", 0
                            )
                        penalty_doc.total_leave_penalty = (
                            penalty_doc.deduct_earned_leave
                            + penalty_doc.deduct_leave_without_pay
                        )
                        penalty_doc.append(
                            "leave_penalty_details",
                            {
                                "leave_type": details["leave_type"],
                                "leave_amount": details["leave_amount"],
                                "reason": details["reason"],
                                "leave_balance_before_penalty": details.get(
                                    "leave_balance_before_application", 0
                                ),
                                "leave_ledger_entry": details.get("leave_ledger_entry", ""),
                                "remarks": details.get("remarks"),
                            },
                        )
                        penalty_doc.save(ignore_permissions=True)
                        penalty_id = frappe.db.get_value(
                            "Attendance",
                            details["attendance"],
                            penalty_doc.name,
                            "custom_employee_penalty_id",
                        )
                        if not penalty_id:
                            frappe.db.set_value(
                                "Attendance",
                                details["attendance"],
                                "custom_employee_penalty_id",
                                penalty_doc.name,
                            )
                            frappe.db.set_value("Attendance", details["attendance"], "custom_penalty_applied", "Yes")
                            
                        changes_made = True

                else:
                    if details["attendance"] is None:
                        try:
                            att_doc = frappe.get_doc(
                                {
                                    "doctype": "Attendance",
                                    "employee": employee,
                                    "attendance_date": target_date,
                                    "status": "Absent",
                                    "company": frappe.db.get_value(
                                        "Employee", employee, "company"
                                    ),
                                }
                            )
                            att_doc.insert(ignore_permissions=True)
                            att_doc.submit()
                            frappe.db.commit()
                        except Exception as e:
                            frappe.log_error(
                                f"Error creating attendance for employee on {target_date}:", str(e)
                            )
                            continue
                        details["attendance"] = att_doc.name
                    handle_leave_ledger(details, employee)
                    penalty_doc = frappe.new_doc("Employee Penalty")
                    penalty_doc.update(
                        {
                            "employee": employee,
                            "attendance": details["attendance"],
                            "penalty_date": target_date,
                            "sandwich_rule_applied": details.get("sandwich_rule_applied", 0),
                            "deduct_earned_leave": details.get("earned_leave", 0),
                            "deduct_leave_without_pay": details.get("leave_without_pay", 0),
                            "total_leave_penalty": details.get("earned_leave", 0)
                            + details.get("leave_without_pay", 0),
                        }
                    )
                    penalty_doc.append(
                        "leave_penalty_details",
                        {
                            "leave_type": details["leave_type"],
                            "leave_amount": details["leave_amount"],
                            "reason": details["reason"],
                            "leave_balance_before_penalty": details.get(
                                "leave_balance_before_application", 0
                            ),
                            "leave_ledger_entry": details.get("leave_ledger_entry", ""),
                            "remarks": details.get("remarks"),
                        },
                    )
                    penalty_doc.insert(ignore_permissions=True)
                    frappe.db.set_value(
                        "Attendance",
                        details["attendance"],
                        "custom_employee_penalty_id",
                        penalty_doc.name,
                    )                    
                    frappe.db.set_value("Attendance", details["attendance"], "custom_penalty_applied", "Yes")

                    changes_made = True
        except Exception as e:
            frappe.log_error(
                f"Error in Processing Penalty for Employee {employee}", str(e)
            )
            continue

    if changes_made:
        frappe.db.commit()


# ? FUNCTION TO CHECK IF SHIFT IS ASSIGNED FOR GIVEN EMPLOYEE & DATE
def check_if_shift_is_assign(employee, date):
    """
    CHECK IF THERE IS AN ACTIVE SHIFT ASSIGNMENT FOR THE EMPLOYEE ON THE GIVEN DATE.
    HANDLES CASE WHERE END DATE IS OPTIONAL.
    """
    # CASE 1: WITH END DATE
    if frappe.db.exists(
        "Shift Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "status": "Active",
            "start_date": ["<=", date],
            "end_date": [">=", date],
        },
    ):
        return True

    # CASE 2: WITHOUT END DATE
    if frappe.db.exists(
        "Shift Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "status": "Active",
            "start_date": ["<=", date],
            "end_date": ["is", "not set"],  # no end date
        },
    ):
        return True

    return False


def get_below_threshold_daily_hours(
    daily_hours_records, percentage_for_daily_hour_penalty, target_date
):
    """
    RETURN ONLY EMPLOYEES WHOSE DAILY HOURS ARE BELOW THRESHOLD BASED ON SHIFT DURATION.

    :param daily_hours_records: dict { emp: { 'working_hours': float, ... }, ... }
    :param percentage_for_daily_hour_penalty: int or float (percentage of shift duration)
    :param target_date: datetime.date
    :return: dict -> filtered daily_hours_records
    """
    if not percentage_for_daily_hour_penalty:
        return {}

    try:
        employees = list(daily_hours_records.keys())
    except Exception as e:
        frappe.log_error("Error in Employee List", str(e))
        return {}

    try:
        # ? FETCH SHIFT ASSIGNMENTS FOR TARGET DATE (INCLUDING OPEN-ENDED)
        shift_assignments = frappe.get_all(
            "Shift Assignment",
            filters={
                "employee": ["in", employees],
                "status": "Active",
                "docstatus": 1,
                "start_date": ["<=", target_date],
            },
            or_filters=[{"end_date": [">=", target_date]}, {"end_date": ["is", "not set"]}],
            fields=["employee", "shift_type"],
        )

        emp_shift_map = {sa.employee: sa.shift_type for sa in shift_assignments}
    except Exception as e:
        frappe.log_error("Error in Shift Assignments", str(e))
        emp_shift_map = {}

    try:
        # ? FETCH SHIFT TIMINGS FOR ASSIGNED SHIFT TYPES
        shift_types = list(set(emp_shift_map.values()))
        shift_details = frappe.get_all(
            "Shift Type",
            filters={"name": ["in", shift_types]},
            fields=["name", "start_time", "end_time"],
        )
        # ? MAP SHIFT NAME TO SHIFT DETAILS
        shift_time_map = {s.name: s for s in shift_details}
    except Exception as e:
        frappe.log_error('Error in Shift', str(e))
        shift_time_map = {}
    

    below_threshold_records = {}

    # ? LOOP THROUGH DAILY HOURS RECORDS AND FILTER BASED ON THRESHOLD DURATION
    for emp, data in daily_hours_records.items():
        try:

            working_hours = data.get("working_hours", 0)
            shift_type = emp_shift_map.get(emp)

            # ? SKIP IF NO SHIFT
            if not shift_type or shift_type not in shift_time_map:
                continue

            start_time = shift_time_map[shift_type].start_time
            end_time = shift_time_map[shift_type].end_time

            # ? HANDLE OVERNIGHT SHIFTS
            if end_time < start_time:
                end_time += timedelta(days=1)

            shift_duration_hours = (end_time - start_time).total_seconds() / 3600.0

            # ? CALCULATE THRESHOLD HOURS BASED ON PERCENTAGE
            threshold_hours = (
                float(percentage_for_daily_hour_penalty) / 100
            ) * shift_duration_hours

            # ? ONLY ADD IF BELOW THRESHOLD
            if (working_hours) < threshold_hours:
                below_threshold_records[emp] = data
        except Exception as e:
            frappe.log_error(
                f"Error in get_below_threshold_daily_hours for {emp}", str(e)
            )
            continue

    return below_threshold_records


def get_leave_allocation_id(employee, leave_type, attendance_date):
    """
    RETURN THE LEAVE ALLOCATION ID FOR THE EMPLOYEE, LEAVE TYPE, AND DATE.
    """
    allocation = frappe.get_value(
        "Leave Allocation",
        {
            "employee": employee,
            "leave_type": leave_type,
            "from_date": ["<=", attendance_date],
            "to_date": [">=", attendance_date],
            "docstatus": 1,
        },
        "name",
    )
    return allocation


def process_no_attendance_penalties_for_prompt(
    employees, penalty_buffer_days, target_date, priority_field, custom_buffer_days, weekoff_change = False
):
    """
    PROCESS NO ATTENDANCE PENALTIES FOR EMPLOYEES WHO WERE NOT PRESENT
    AND CREATE 'ABSENT' ATTENDANCE RECORDS IF NOT HOLIDAY OR WEEKOFF.
    """
    penalty_entries = {}

    # ? RETURN IF BUFFER NOT CONFIGURED AND NOT CUSTOM BUFFER DAYS
    if not penalty_buffer_days and not custom_buffer_days:
        return penalty_entries
    if custom_buffer_days:
        penalty_buffer_days = 0
    
    # ! CHECK TARGET DATE'S ATTENDANCE IS EXISTS OR NOT
    try:
        attendance_records = target_date_attendance_exists(
            employees, target_date, 0, 1, 0, 0
        )
    except Exception as e:
        frappe.log_error(
            f"Error in Getting Attendance Records",str(e)
        )
        return penalty_entries
    employees_with_attendance = []
    if attendance_records:
        employees_with_attendance = list(attendance_records.keys())

    # ? FIND EMPLOYEES WITHOUT ATTENDANCE
    employees_without_attendance = list(set(employees) - set(employees_with_attendance))

    if employees_without_attendance:
        filtered_employees = []

        for emp in employees_without_attendance:
            # ? CHECK HOLIDAY
            try:
                if not weekoff_change:
                    if get_holiday_dates_for_employee(emp, target_date, target_date):
                        continue
            except Exception as e:
                frappe.log_error(
                    f"Error in Getting Holiday Date",str(e)
                )
                continue

            # ? CHECK NO ATTENDANCE AND PENALTY IS CHECK IN EMPLOYEE MASTER
            try:
                is_no_attendance_and_penalty = frappe.db.get_value("Employee", emp, "custom_no_attendance_and_penalty") or 0
                if is_no_attendance_and_penalty:
                    continue
            except Exception as e:
                frappe.log_error(
                    f"Error in Getting No Attendance and Penalty Value From Employee Master",str(e)
                )
                continue

            # ? CHECK IF EMPLOYEE HAS LEAVE APPLICATION APPROVED
            # ? FOR THE TARGET DATE
            # ? SKIP IF EMPLOYEE HAS APPROVED LEAVE APPLICATION
            # ? FOR THE TARGET DATE
            try:
                if frappe.db.exists(
                    "Leave Application",
                    {
                        "employee": emp,
                        "workflow_state": "Approved",
                        "from_date": ["<=", target_date],
                        "to_date": [">=", target_date],
                    },
                ):
                    continue
            except Exception as e:
                frappe.log_error(
                    f"Error in Checking Leave Application",str(e)
                )
                continue

            filtered_employees.append(emp)

        if filtered_employees:
            # ! GET LEAVE PENALTY CONFIGURATION FOR NO ATTENDANCE PENALTY
            try:
                leave_priority = frappe.db.get_all(
                    "Leave Penalty Configuration",
                    filters={
                        "parent": "HR Settings",
                        "parenttype": "HR Settings",
                        "parentfield": priority_field,
                    },
                    fields=[
                        "penalty_deduction_type",
                        "leave_type_for_penalty",
                        "deduction_of_leave",
                    ],
                    order_by="idx asc",
                )
            except Exception as e:
                frappe.log_error(
                    f"Error in Getting Leave Penalty Configuration",str(e)
                )
                return penalty_entries

            # ? CALCULATE LEAVE DEDUCTIONS BASED ON PRIORITY CONFIGURATION
            # ? AND ADD TO PENALTY ENTRIES
            # ? FOR EACH EMPLOYEE WITHOUT ATTENDANCE
            for emp in filtered_employees:
                try:
                    penalty_entries.update(
                        calculate_leave_deductions_based_on_priority(
                            employee=emp,
                            attendance_date=target_date,
                            deduction_amount=1.0,
                            reason="No Attendance",
                            penalizable_attendance=None,
                            remarks=f"Penalty for No Attendance Marked on {target_date}",
                            leave_priority=leave_priority,
                        )
                    )
                except Exception as e:
                    frappe.log_error(
                        f"Error in Calculating Leave Deductions Based On Priority",str(e)
                    )
                    continue

    return penalty_entries


def process_mispunch_penalties_for_prompt(
    employees, penalty_buffer_days, target_date, priority_field, custom_buffer_days, weekoff_change = False
):
    """
    PROCESS MIS-PUNCH PENALTIES FOR EMPLOYEES WHO HAD MIS-PUNCHES
    AND CREATE 'MIS-PUNCH' ATTENDANCE RECORDS IF NOT HOLIDAY OR WEEKOFF.
    """
    penalty_entries = {}

    # ! CHECK TARGET DATE'S MISPUNCH ATTENDANCE IS EXISTS OR NOT
    try:
        mispunch_records = target_date_attendance_exists(employees, target_date, 0, 0, 1, 0)
    except Exception as e:
        frappe.log_error(
            f"Error in Getting Attendance Records",str(e)
        )
        return penalty_entries
    # ? RETURN IF BUFFER NOT CONFIGURED AND NOT CUSTOM BUFFER DAYS
    if not penalty_buffer_days and not custom_buffer_days:
        return penalty_entries
    if custom_buffer_days:
        penalty_buffer_days = 0

    # ? GET LEAVE PENALTY CONFIGURATION FOR MIS-PUNCH PENALTY
    try:
        leave_priority = frappe.db.get_all(
            "Leave Penalty Configuration",
            filters={
                "parent": "HR Settings",
                "parenttype": "HR Settings",
                "parentfield": priority_field,
            },
            fields=[
                "penalty_deduction_type",
                "leave_type_for_penalty",
                "deduction_of_leave",
            ],
            order_by="idx asc",
        )
    except Exception as e:
        frappe.log_error(
            f"Error in Getting Leave Penalty Configuration",str(e)
        )
        return penalty_entries

    # ? IF MISPUNCH RECORD FOUND
    if not mispunch_records:
        return penalty_entries

    # ? PROCESS EACH MIS-PUNCH RECORD
    for emp in mispunch_records.keys():
        # ? CHECK HOLIDAY
        try:
            if not weekoff_change:
                if get_holiday_dates_for_employee(emp, target_date, target_date):
                    continue
        except Exception as e:
            frappe.log_error(
                f"Error in Getting Holiday Date",str(e)
            )
            continue
        try:
            if full_day_leave_exists(emp, target_date):
                continue
        except Exception as e:
            frappe.log_error(
                f"Error in Checking Full Day Leave Existence",str(e)
            )
            continue

        # ? CHECK NO ATTENDANCE AND PENALTY IS CHECK IN EMPLOYEE MASTER
        try:
            is_no_attendance_and_penalty = frappe.db.get_value("Employee", emp, "custom_no_attendance_and_penalty") or 0
            if is_no_attendance_and_penalty:
                continue
        except Exception as e:
            frappe.log_error(
                f"Error in Getting No Attendance and Penalty Value From Employee Master",str(e)
            )
            continue

        try:
            penalty_entries.update(
                calculate_leave_deductions_based_on_priority(
                    employee=emp,
                    attendance_date=target_date,
                    deduction_amount=1.0,
                    reason="Mispunch",
                    penalizable_attendance=mispunch_records[emp]["attendance"],
                    remarks=f"Penalty for Mispunch on {target_date}",
                    leave_priority=leave_priority,
                )
            )
        except Exception as e:
            frappe.log_error(
                f"Error in Calculating Leave Deductions Based On Priority",str(e)
            )
            continue

    return penalty_entries


def check_employee_penalty_criteria(employee=None, penalization_type=None):
    try:
        employee = frappe.get_doc("Employee", employee)
        company_abbr = frappe.db.get_value("Company", employee.company, "abbr")
        hr_settings = frappe.get_single("HR Settings")

        # ? PENALIZATION TYPE MAPPING
        penalization_type_mapping = {
            "No Attendance": "For No Attendance",
            "Mispunch": "For Mispunch",
            "Late Coming": "For Late Arrival",
            "Insufficient Hours": "For Work Hours",
        }

        penalization_type = penalization_type_mapping.get(penalization_type, None)

        # Abbreviations
        prompt_abbr = hr_settings.custom_prompt_abbr

        # Determine which table to use based on company
        if company_abbr == prompt_abbr:
            table = hr_settings.custom_penalization_criteria_table_for_prompt
        else:
            return True

        if not table:
            return True  # Allow if table is not configured

        # ? MAP EMPLOYEE FIELD AND ITS DOCTYPE
        criteria = {
            row.select_doctype: row.employee_field_name
            for row in table
            if row.select_doctype and row.employee_field_name
        }

        is_penalisation = False
        for row in table:
            if row.penalization_type != penalization_type:
                continue

            is_penalisation = True
            employee_fieldname = criteria.get(row.select_doctype)
            if (
                employee_fieldname
                and getattr(employee, employee_fieldname, None) == row.value
            ):
                return True

        return not is_penalisation or False
    except Exception as e:
        frappe.log_error(
            f"Error in Checking Employee Penalty Criteria",str(e)
        )
        return False


def auto_approve_scheduler():
    """
    Scheduled task to auto approve or reject attendance requests, leave applications, 
    attendance regularization, shift requests, weekoff change requests
    based on the days configuration in HR Settings.
    """
    try:
        auto_approve_days = frappe.db.get_single_value("HR Settings", "custom_auto_approve_request_after_days") or 0
        buffer_days = frappe.db.get_single_value("HR Settings", "custom_buffer_days_for_penalty") or 0
        final_approval_days = frappe.db.get_single_value("HR Settings", "custom_final_stage_auto_approve_after_days") or 0
    except Exception as e:
        frappe.log_error(f"Error in getting auto_approve_days from HR Settings:", {str(e)})
        return

    if not auto_approve_days and not buffer_days:
        return

    if auto_approve_days:
        auto_mark_date_after_creation = getdate(
                add_to_date(today(), days=-(int(auto_approve_days)+1))
            )
        start_datetime = get_datetime_str(datetime.combine(auto_mark_date_after_creation, time.min))
        end_datetime = get_datetime_str(datetime.combine(auto_mark_date_after_creation, time.max))

    else:
        auto_mark_date_after_creation = None
        
    if buffer_days:
        auto_mark_buffer_date = getdate(
        add_to_date(today(), days=-(int(buffer_days)+1))
    )
    else:
        auto_mark_buffer_date = None


    if (final_approval_days or final_approval_days == 0) and auto_approve_days:
        auto_mark_final_approval_date = getdate(
        add_to_date(today(), days=-(int(final_approval_days) + int(auto_approve_days)+1))
    )
        final_approval_start_time  = get_datetime_str(datetime.combine(auto_mark_final_approval_date, time.min))
        final_approval_end_time = get_datetime_str(datetime.combine(auto_mark_final_approval_date, time.max))
    
    else:
        auto_mark_final_approval_date = None

    try:
        employees = get_active_employees()
    except Exception as e:
        frappe.log_error(f"Error in getting active employees:", {str(e)})
        employees = []

    if not employees:
        return

    # ? Approve only one leave application per employee
    try:
        leave_requests = []
        created_leave_requests = []
        final_approval_created_requests = []
        if auto_mark_buffer_date:
            # Fetch pending leave application filtered properly with commas in filters
            leave_requests = frappe.get_all(
                "Leave Application",
                filters={
                    "workflow_state": ["in",["Pending", "Approved by Reporting Manager"]],
                    "from_date": ["<=", auto_mark_buffer_date],
                    "to_date": [">=", auto_mark_buffer_date],
                    "employee": ["in", employees],
                },
                fields=["name", "employee"],
                order_by="from_date asc"
            )

        if auto_mark_date_after_creation:
            # Fetch pending leave application filtered properly with commas in filters
            created_leave_requests = frappe.get_all(
                "Leave Application",
                filters={
                    "workflow_state": ["in",["Pending"]],
                    "employee": ["in", employees],
                    "creation": ["between", [start_datetime, end_datetime]],
                },
                fields=["name", "employee"],
                order_by="from_date asc"
            )

        if auto_mark_final_approval_date:
            # Fetch pending leave application filtered properly with commas in filters
            final_approval_created_requests = frappe.get_all(
                "Leave Application",
                filters={
                    "workflow_state": ["in",["Pending", "Approved by Reporting Manager"]],
                    "employee": ["in", employees],
                    "creation": ["between", [final_approval_start_time, final_approval_end_time]],
                },
                fields=["name", "employee"],
                order_by="from_date asc"
            )
        
        leave_requests.extend(final_approval_created_requests)
        for request in leave_requests:
            try:
                leave_request = frappe.get_doc("Leave Application", request.name)
            except Exception as e:
                frappe.log_error(f"Error fetching Leave Application {request.name}:", str(e))
                continue
            try:
                try:
                    if leave_request.workflow_state == "Pending":
                        if leave_request.leave_type not in ["Leave Without Pay", "Casual Leave"]:
                            try:
                                leave_request.db_set("custom_auto_approve", 1)
                                apply_workflow(leave_request, "Approve")
                                if leave_request.workflow_state == "Approved by Reporting Manager":
                                    apply_workflow(leave_request, "Approve")
                            except Exception as e:
                                leave_request.db_set("custom_auto_approve", 0)
                                frappe.log_error(f"Error approving leave request:", str(e))
                                continue

                        else:
                            try:
                                leave_request.db_set("custom_auto_approve", 1)
                                apply_workflow(leave_request, "Approve")
                            except Exception as e:
                                leave_request.db_set("custom_auto_approve", 0)
                                frappe.log_error(f"Error approving leave request:", str(e))
                                continue
                    elif leave_request.workflow_state == "Approved by Reporting Manager":
                        try:
                            leave_request.db_set("custom_auto_approve", 1)
                            apply_workflow(leave_request, "Approve")

                        except Exception as e:
                            leave_request.db_set("custom_auto_approve", 0)
                            frappe.log_error(f"Error approving leave request:", str(e))
                            continue

                except Exception as e:
                    frappe.log_error(f"Error approving leave request:", str(e))
                    continue

            except Exception as e:
                frappe.log_error(f"Error approving leave request {request.name}:", str(e))
                continue

        for request in created_leave_requests:
            try:
                leave_request = frappe.get_doc("Leave Application", request.name)
            except Exception as e:
                frappe.log_error(f"Error fetching Leave Application {request.name}:", str(e))
                continue
            try:
                try:
                    if leave_request.workflow_state != "Approved":
                        leave_request.db_set("custom_auto_approve", 1)
                        apply_workflow(leave_request, "Approve")
                except Exception as e:
                    leave_request.db_set("custom_auto_approve", 0)
                    frappe.log_error(f"Error approving leave request:", str(e))
                    continue
            except Exception as e:
                frappe.log_error(f"Error approving leave request {request.name}:", str(e))
                continue

    except Exception as e:
        frappe.log_error(f"Error fetching or processing Leave requests:", str(e))


    # ? Approve only one shift request per employee
    try:
        shift_requests = []
        shift_requests_created = []
        if auto_mark_buffer_date:
            # Fetch pending shift requests filtered properly with commas in filters
            shift_requests = frappe.db.get_all(
                "Shift Request",
                filters={
                    "workflow_state": "Pending",
                    "from_date": ["<=", auto_mark_buffer_date],
                    "employee": ["in", employees],
                },
                or_filters=[{"to_date": [">=", auto_mark_buffer_date]}, {"to_date": ["is", "not set"]}],
                fields=["name", "employee", "from_date"],
                order_by="from_date asc"
            )

        if auto_mark_date_after_creation:
            shift_requests_created = frappe.get_all(
                "Shift Request",
                filters={
                    "workflow_state": "Pending",
                    "employee": ["in", employees],
                    "creation": ["between", [start_datetime, end_datetime]],
                },
                fields=["name", "employee", "from_date"],
                order_by="from_date asc"
            )

        shift_requests.extend(shift_requests_created)
        for request in shift_requests:
            try:
                shift_request = frappe.get_doc("Shift Request", request.name)
            except Exception as e:
                frappe.log_error(f"Error fetching shift request {request.name}:", str(e))
                continue
            try:
                shift_request.db_set("custom_auto_approve", 1)
                apply_workflow(shift_request, "Approve")
            except Exception as e:
                shift_request.db_set("custom_auto_approve", 0)
                frappe.log_error(f"Error approving shift request {request.name}:", str(e))
                continue

    except Exception as e:
        frappe.log_error(f"Error fetching or processing shift request:", str(e))

    # ? Approve only one attendance regularization per employee
    try:
        attendance_regularizations = []
        attendance_regularizations_created = []
        if auto_mark_buffer_date:
            # Fetch pending attendance regularization filtered properly with commas in filters
            attendance_regularizations = frappe.db.get_all(
                "Attendance Regularization",
                filters={
                    "workflow_state": "Pending",
                    "regularization_date": auto_mark_buffer_date,
                    "employee": ["in", employees],
                },
                fields=["name", "employee"],
                order_by="regularization_date asc"
            )

        if auto_mark_date_after_creation:
            attendance_regularizations_created = frappe.get_all(
                "Attendance Regularization",
                filters={
                    "workflow_state": "Pending",
                    "employee": ["in", employees],
                    "creation": ["between", [start_datetime, end_datetime]],
                },
                fields=["name", "employee"],
                order_by="regularization_date asc"
            )

        attendance_regularizations.extend(attendance_regularizations_created)
        for request in attendance_regularizations:
            try:
                attendance_regularization = frappe.get_doc("Attendance Regularization", request.name)
            except Exception as e:
                frappe.log_error(f"Error fetching attendance regularization {request.name}:", str(e))
                continue
            try:
                attendance_regularization.db_set("auto_approve", 1)
                apply_workflow(attendance_regularization, "Approve")
            except Exception as e:
                attendance_regularization.db_set("auto_approve", 0)
                frappe.log_error(f"Error approving attendance regularization {request.name}: ",str(e))
                continue

    except Exception as e:
        frappe.log_error(f"Error fetching or processing attendance regularization:" ,str(e))

    # ? Approve only one attendance request per employee
    try:
        attendance_requests = []
        attendance_requests_created = []
        if auto_mark_buffer_date:
            # Fetch pending attendance requests filtered properly with commas in filters
            attendance_requests = frappe.db.get_all(
                "Attendance Request",
                filters={
                    "workflow_state": "Pending",
                    "from_date": ["<=", auto_mark_buffer_date],
                    "to_date": [">=", auto_mark_buffer_date],
                    "employee": ["in", employees],
                },
                fields=["name", "employee", "from_date"],
                order_by="from_date asc"
            )

        if auto_mark_date_after_creation:
            attendance_requests_created = frappe.get_all(
                "Attendance Request",
                filters={
                    "workflow_state": "Pending",
                    "employee": ["in", employees],
                    "creation": ["between", [start_datetime, end_datetime]],
                },
                fields=["name", "employee", "from_date"],
                order_by="from_date asc"
            )

        attendance_requests.extend(attendance_requests_created)

        for request in attendance_requests:
            try:
                attendance_request = frappe.get_doc("Attendance Request", request.name)
                attendance_request.db_set("custom_auto_approve", 1)
                apply_workflow(attendance_request, "Approve")
            except Exception as e:
                attendance_request.db_set("custom_auto_approve", 0)
                frappe.log_error(f"Error approving attendance request {request.name}:", str(e))
                continue

    except Exception as e:
        frappe.log_error(f"Error fetching or processing attendance requests:", str(e))

    # ? Approve only one weekoff change request
    try:
        weekoff_change_requests = []
        weekoff_change_requests_created = []
        if auto_mark_buffer_date:
            #! FETCH CHILD RECORDS WHERE EITHER existing_weekoff_date OR new_weekoff_date = auto_mark_buffer_date
            weekoff_change_request_child_table = frappe.get_all(
                "WeekOff Request Details",
                or_filters=[
                    ["existing_weekoff_date", "=", auto_mark_buffer_date],
                    ["new_weekoff_date", "=", auto_mark_buffer_date],
                ],
                fields=["parent"]
            )

            #! COLLECT PARENT REQUEST NAMES
            parent_names = [row.parent for row in weekoff_change_request_child_table]

            #! FETCH PENDING WEEKOFF CHANGE REQUESTS WITH OR FILTERS
            weekoff_change_requests = frappe.get_all(
                "WeekOff Change Request",
                filters=[
                    ["workflow_state", "=", "Pending"],
                    ["employee", "in", employees],
                    ["name", "in", parent_names]
                ],
                fields=["name", "employee"],
            )

        if auto_mark_date_after_creation:
            weekoff_change_requests_created = frappe.get_all(
                "WeekOff Change Request",
                filters={
                    "workflow_state": "Pending",
                    "employee": ["in", employees],
                    "creation": ["between", [start_datetime, end_datetime]],
                },
                fields=["name", "employee"],
            )

        weekoff_change_requests.extend(weekoff_change_requests_created)

        for request in weekoff_change_requests:
            try:
                weekoff_change_request = frappe.get_doc("WeekOff Change Request", request.name)
                weekoff_change_request.db_set("auto_approve", 1)
                apply_workflow(weekoff_change_request, "Approve")
            except Exception as e:
                weekoff_change_request.db_set("auto_approve", 0)
                frappe.log_error(f"Error approving weekoff change request {request.name}:", str(e))
                continue

    except Exception as e:
        frappe.log_error(f"Error fetching or processing weekoff change requests:", str(e))

def half_day_leave_exist_first_half(employee, target_date):
    """
    CHECK IF THERE IS ANY FULL-DAY LEAVE (NOT HALF DAY) FOR THE EMPLOYEE ON THE TARGET DATE.
    """
    try:
        results = frappe.get_all(
            "Leave Application",
            filters={
                "employee": employee,
                "workflow_state": "Approved",
                "from_date": ["<=", target_date],
                "to_date": [">=", target_date],
                "half_day": 1,
            },
            or_filters=[
                ["half_day_date", "!=", target_date],
                ["custom_half_day_time", "!=", "Second"]
            ],
            fields=["name", "half_day", "half_day_date"]
        )
        if results:
            return True
        
        else:
            return False

    except Exception as e:
        frappe.log_error(f"Error checking half day leave for {employee} on {target_date}:", frappe.get_traceback())
        return False

def full_day_leave_exists(employee, target_date):
    """
    CHECK IF THERE IS ANY FULL-DAY LEAVE (NOT HALF DAY) FOR THE EMPLOYEE ON THE TARGET DATE.
    """
    try:
        results = frappe.get_all(
            "Leave Application",
            filters={
                "employee": employee,
                "workflow_state": "Approved",
                "from_date": ["<=", target_date],
                "to_date": [">=", target_date],
            },
            or_filters=[
                ["half_day", "=", 0],
                ["half_day_date", "!=", target_date]
            ],
            fields=["name", "half_day", "half_day_date"]
        )

        if results:
            return True
        
        else:
            return False

    except Exception as e:
        frappe.log_error(f"Error checking full day leave for {employee} on {target_date}:", str(e))
        return False


def send_penalty_notification_emails():
    try:
        employees = get_active_employees()
    except Exception as e:
        frappe.log_error("Error in getting active employees", str(e))
        employees = []

    try:
        is_emails_enabled = frappe.db.get_single_value("HR Settings", "custom_enable_penalty_emails") or 0
    except Exception as e:
        frappe.log_error("Error in getting email settings from HR Settings", str(e))
        is_emails_enabled = 0

    if not is_emails_enabled:
        return

    if not employees:
        return
    try:
        today = getdate()
        start_datetime = get_datetime_str(datetime.combine(today, time.min))
        end_datetime = get_datetime_str(datetime.combine(today, time.max))
        all_penalties = frappe.get_all(
            "Employee Penalty",
            filters={
                "employee": ["in", employees],
                "creation": ["between", [start_datetime, end_datetime]],
                "is_leave_balance_restore": 0,
            },
            fields=["name", "employee", "penalty_date", "attendance"]
        )
        try:
            notification_doc = frappe.get_doc("Notification", "Employee Penalty Notification")
        except Exception as e:
            frappe.log_error("Error in fetching Notification Doc", str(e))
            return
        if all_penalties:
            all_emails_details = []
            penalty_attendance_date = None
            for penalty in all_penalties:
                if notification_doc:
                    try:
                        emp_user_id = get_employee_email(penalty.employee)
                        try:
                            no_penalty_for_employee = frappe.db.get_value("Employee", penalty.employee, "custom_no_attendance_and_penalty") or 0
                        except:
                            frappe.log_error("Error in getting no attendance and penalty settings from Employee", str(e))
                            no_penalty_for_employee = 0
                        if no_penalty_for_employee:
                            continue
                        if emp_user_id:
                            subject = frappe.render_template(
                                notification_doc.subject,
                                {"penalty": penalty.name, "employee_name": penalty.employee, "penalty_date": penalty.penalty_date}
                            )
                            message = frappe.render_template(
                                notification_doc.message,
                                {
                                    "penalty": penalty.name,
                                    "employee_name": penalty.employee,
                                    "penalty_date": penalty.penalty_date
                                }
                            )
                            if not penalty_attendance_date:
                                penalty_attendance_date = penalty.penalty_date
                            try:
                                add_to_penalty_email = frappe.db.get_single_value("HR Settings", "custom_add_emails_to_penalty_emails_for_prompt") or 0
                            except Exception as e:
                                frappe.log_error("Error in getting additional email settings from HR Settings", str(e))
                                add_to_penalty_email = 0
                            if add_to_penalty_email:
                                child_table_data = frappe.get_all(
                                    "Employee Leave Penalty Details",
                                    filters={"parent": penalty.name},
                                    fields=["reason"]
                                )
                                penalty_data = {}
                                for row in child_table_data:
                                    penalty_data.setdefault(row.reason, {})
                                    penalty_data[row.reason].update(
                                        {
                                            "penalty_date": "",
                                            "attendance": penalty.attendance,
                                        }
                                    )
                                all_emails_details.append({
                                    "recipients": emp_user_id,
                                    "subject": subject,
                                    "message": message,
                                    "data": {
                                        "employee": penalty.employee,
                                        "employee_name": frappe.db.get_value("Employee", penalty.employee, "employee_name"),
                                        "email_type": "Penalty Notification",
                                        "penalties": penalty_data,
                                        "attendance_date": clean_dates(penalty.penalty_date),
                                    }
                                })
                            else:
                                frappe.sendmail(
                                    recipients=[emp_user_id],
                                    subject=subject,
                                    message=message,
                                    reference_doctype="Employee Penalty",
                                    reference_name=penalty.name,
                                )
                                create_notification_log(emp_user_id, subject, message, "Employee Penalty", penalty.name)
                    except Exception as e:
                        frappe.log_error("Error in sending penalty notification email", str(e))
                        continue

            try:
                child_rows = []
                if all_emails_details:
                    for ed in all_emails_details:
                        try:
                            child_rows.append({
                                "doctype": "Penalty Emails Details",
                                "email": ed["recipients"],
                                "subject": ed["subject"],
                                "message": ed["message"],
                                "data": ed["data"]
                            })
                        except Exception as e:
                            frappe.log_error("Error in appending child rows for penalty email", str(e))
                            continue
                    penalty_emails_doc = frappe.get_doc({
                        "doctype": "Penalty Emails",
                        "status": "Not Sent",
                        "email_details": child_rows,
                        "date": getdate(),
                        "remarks": f"Consolidated penalty notification emails prepared on {format_date(getdate())} for attendance irregularities dated {format_date(penalty_attendance_date)}."
                    })

                    penalty_emails_doc.insert(ignore_permissions=True)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error("Error in creating Penalty Emails Doc", str(e))

    except Exception as e:
        frappe.log_error("Error in fetching Employee Penalties", str(e))


def clean_dates(obj):
    """
    RECURSIVELY CONVERT DATETIME.DATE OR DATETIME.DATETIME
    TO ISO STRING (YYYY-MM-DD).
    """
    if isinstance(obj, dict):
        return {k: clean_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_dates(v) for v in obj]
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj

import frappe
from frappe.utils import getdate, today, add_to_date, add_days
from prompt_hr.scheduler_methods import add_leave_ledger_entry
from hrms.hr.utils import get_holiday_dates_for_employee
from datetime import datetime, timedelta
from prompt_hr.scheduler_methods import send_penalty_warnings

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
        late_coming_allowed_per_month = (
            hr_settings.custom_late_coming_allowed_per_month_for_prompt or 0
        )
        late_coming_penalty_buffer_days = (
            hr_settings.custom_buffer_period_for_leave_penalty_for_prompt or 0
        )
        late_coming_target_date = getdate(
            add_to_date(today(), days=-(int(late_coming_penalty_buffer_days) + 1))
        )
        late_coming_penalty_enable = hr_settings.custom_enable_late_coming_penalty

        # ? DAILY HOURS PENALTY CONFIGURATION
        daily_hours_penalty_buffer_days = (
            hr_settings.custom_buffer_period_for_daily_hours_penalty_for_prompt or 0
        )
        daily_hours_target_date = getdate(
            add_to_date(today(), days=-(int(daily_hours_penalty_buffer_days) + 1))
        )
        daily_hour_penalty_enable = hr_settings.custom_enable_daily_hours_penalty

        # ? NO ATTENDANCE PENALTY CONFIGURATION
        no_attendance_penalty_buffer_days = (
            hr_settings.custom_buffer_period_for_no_attendance_penalty_for_prompt or 0
        )
        no_attendance_target_date = getdate(
            add_to_date(today(), days=-(int(no_attendance_penalty_buffer_days) + 1))
        )
        no_attendance_penalty_enable = hr_settings.custom_enable_no_attendance_penalty

        # ? MIS-PUNCH PENALTY CONFIGURATION
        mispunch_penalty_buffer_days = (
            hr_settings.custom_buffer_days_for_mispunch_penalty or 0
        )
        mispunch_penalty_target_date = getdate(
            add_to_date(today(), days=-(int(mispunch_penalty_buffer_days) + 1))
        )
        mispunch_penalty_enable = hr_settings.custom_enable_mispunch_penalty

        # ! FETCH ALL LATE ENTRY PENALTY RECORDS FOR THE LAST BUFFER DAYS IF LATE ENTRY PENALTY ENABLE
        late_penalty = {}
        late_penalty_email_records = {}
        if late_coming_penalty_enable:
            late_penalty = process_late_entry_penalties_for_prompt(
                employees,
                late_coming_allowed_per_month,
                late_coming_penalty_buffer_days,
                "custom_late_coming_leave_penalty_configuration",
                late_coming_target_date,
                False
            )
            late_penalty_email_records = process_late_entry_penalties_for_prompt(
                employees,
                late_coming_allowed_per_month,
                late_coming_penalty_buffer_days,
                "custom_late_coming_leave_penalty_configuration",
                email_date,
                False
            
            )

        # ? DAILY HOURS PERCENTAGE FOR PENALTY
        percentage_for_daily_hour_penalty = (
            hr_settings.custom_daily_hours_criteria_for_penalty_for_prompt
        )

        # ! FETCH ALL DAILY HOURS PENALTY RECORDS FOR THE LAST BUFFER DAYS IF IT IS ENABLE
        daily_hour_penalty = {}
        daily_hours_email_records = {}
        if daily_hour_penalty_enable:
            daily_hour_penalty = process_daily_hours_penalties_for_prompt(
                employees,
                daily_hours_penalty_buffer_days,
                daily_hours_target_date,
                percentage_for_daily_hour_penalty,
                "custom_daily_hour_leave_penalty_configuration",
                False
            )
            daily_hours_email_records = process_daily_hours_penalties_for_prompt(
                employees,
                daily_hours_penalty_buffer_days,
                email_date,
                percentage_for_daily_hour_penalty,
                "custom_daily_hour_leave_penalty_configuration",
                False
            )

        # ! FETCH ALL NO ATTENDANCE PENALTY RECORDS FOR THE LAST BUFFER DAYS IF IT IS ENABLE
        no_attendance_penalty = {}
        no_attendance_email_records = {}
        if no_attendance_penalty_enable:
            no_attendance_penalty = process_no_attendance_penalties_for_prompt(
                employees,
                no_attendance_penalty_buffer_days,
                no_attendance_target_date,
                "custom_no_attendance_leave_penalty_configuration",
                False
            )
            no_attendance_email_records = process_no_attendance_penalties_for_prompt(
                employees,
                no_attendance_penalty_buffer_days,
                email_date,
                "custom_no_attendance_leave_penalty_configuration",
                False
            )

        # ! FETCH ALL MIS-PUNCH PENALTY RECORDS FOR THE LAST BUFFER DAYS IF IT IS ENABLE
        mispunch_penalty = {}
        mispunch_penalty_email_records = {}
        if mispunch_penalty_enable:
            mispunch_penalty = process_mispunch_penalties_for_prompt(
                employees,
                mispunch_penalty_buffer_days,
                mispunch_penalty_target_date,
                "custom_attendance_mispunch_leave_penalty_configuration",
                False
            )
            mispunch_penalty_email_records = process_mispunch_penalties_for_prompt(
                employees,
                mispunch_penalty_buffer_days,
                email_date,
                "custom_attendance_mispunch_leave_penalty_configuration",
                False
            )

        # ! CREATE OR UPDATE PENALTY RECORDS IN THE DATABASE
        if late_penalty:
            create_penalty_records(late_penalty, late_coming_target_date)

        if daily_hour_penalty:
            create_penalty_records(daily_hour_penalty, daily_hours_target_date)

        if no_attendance_penalty:
            create_penalty_records(no_attendance_penalty, no_attendance_target_date)

        if mispunch_penalty:
            create_penalty_records(mispunch_penalty, mispunch_penalty_target_date)

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
            records = data["records"]
            buffer_days = data["buffer_days"]

            if not records:
                continue

            for emp_id, emp_penalties in records.items():
                att_date = emp_penalties.get("attendance_date")
                attendance = emp_penalties.get("attendance", None)
                if not att_date:
                    continue
                # compute buffered email date
                email_date_with_buffer = add_days(att_date, int(buffer_days))

                if emp_id not in consolidated_email_records:
                    consolidated_email_records[emp_id] = {}

                consolidated_email_records[emp_id][penalty_type] = {
                    "penalty_date": email_date_with_buffer,
                    "attendance": attendance,
                }

        # ! SEND CONSOLIDATED WARNINGS
        for emp_id, penalties in consolidated_email_records.items():
            send_penalty_warnings(emp_id, penalties, email_date)

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
    custom_buffer_days
):
    """
    Process late entry penalties for a given employee based on buffer days and attendance records.
    Returns a list of penalty entries.
    """
    penalty_entries = {}

    # ? GET LEAVE CONFIGURATION FOR LATE ENTRY PENALTY
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

    # ? RETURN IF BUFFER NOT CONFIGURED AND NOT CUSTOM BUFFER DAYS
    if not penalty_buffer_days and not custom_buffer_days:
        return penalty_entries
    if custom_buffer_days:
        penalty_buffer_days = 0

    # ! CHECK TARGET DATE'S ATTENDANCE IS LATE OR NOT
    late_attendance_records = target_date_attendance_exists(
        employees, target_date, 1, 0, 0, 0
    )
    # ! SKIP IF TARGET DATE ATTENDANCE IS NOT LATE
    if not late_attendance_records:
        return []

    # ? EMPLOYEES WHO HAD LATE ENTRY ON TARGET DATE
    late_employees = list(late_attendance_records.keys())

    # ? GET MONTH START DATE
    month_start_date = target_date.replace(day=1)
    prev_target_date = getdate(add_to_date(target_date, days=-1))

    #! SAFETY: HANDLE EMPTY EMPLOYEE LIST
    if not late_employees:
        prev_late_attendance_count = {}
    else:
        #! FETCH ATTENDANCE RECORDS WITH LATE ENTRY FROM MONTH START TO TARGET DATE
        prev_late_attendance_list = frappe.db.get_all(
            "Attendance",
            filters={
                "employee": ["in", late_employees],
                "docstatus": 1,
                "late_entry": 1,
                "attendance_date": ["between", [month_start_date, prev_target_date]],
            },
            fields=["employee", "name", "attendance_date"],
            order_by="attendance_date asc",
        )

        #! INIT COUNT FOR ALL EMPLOYEES TO ZERO (INCLUDES ZERO-RECORD EMPLOYEES)
        prev_late_attendance_count = {emp: 0 for emp in set(late_employees)}

        #! INCREMENT COUNTS FROM QUERY RESULTS
        for rec in prev_late_attendance_list:
            emp = rec["employee"]
            prev_late_attendance_count[emp] += 1

    # ? IF PREV LATE ATTENDANCE COUNT IS EMPTY, RETURN EMPTY PENALTY LIST
    if not prev_late_attendance_count:
        return penalty_entries

    # ? PROCESS EACH EMPLOYEE WHO HAD LATE ENTRY
    # ? AND CHECK IF THEY EXCEED THE ALLOWED LATE COMING COUNT
    # ? IF YES, CALCULATE LEAVE DEDUCTIONS BASED ON PRIORITY CONFIGURATION
    # ? AND ADD TO PENALTY ENTRIES
    for employee, count in prev_late_attendance_count.items():

        leave_application_exists = frappe.db.exists(
            "Leave Application",
            {
                "employee": employee,
                "workflow_state": "Approved",
                "from_date": ["<=", target_date],
                "to_date": [">=", target_date],
            },
        )

        attendance_request_exists = frappe.db.exists(
            "Attendance Request",
            {
                "employee": employee,
                "from_date": ["<=", target_date],
                "to_date": [">=", target_date],
                "custom_status": "Approved",
                "docstatus": ["!=", 2],
                "reason": "Partial Day"
            },
        )

        if (
            count >= late_coming_allowed_per_month
            and not leave_application_exists
            and not attendance_request_exists
        ):
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
    leave_balances = get_remaining_leaves(employee)

    # ? ENSURE LEAVE BALANCES ARE NOT EMPTY
    for config in leave_priority:
        deduction_type = config.get("penalty_deduction_type")
        leave_type = config.get("leave_type_for_penalty")
        deduction_of_leave = config.get("deduction_of_leave")

        deduction_unit = 0.5 if deduction_of_leave == "Half Day" else 1.0

        # ! CALCULATE LEAVE AMOUNT TO BE DEDUCTED
        leave_amount = min(deduction_amount, deduction_unit)
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
                }
            }

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
        leave_type = entry["leave_type"]
        leaves = entry["leaves"]

        if leave_type in leave_balance_map:
            leave_balance_map[leave_type] += leaves
        else:
            leave_balance_map[leave_type] = leaves

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
        else:
            filters.update({"status": ["not in",["Absent","On Leave", "WeekOff"]]})

    # ? ADD MISPUNCH STATUS FILTER IF FETCHING MISPUNCH RECORDS
    if mispunch:
        filters.update({"status": "Mispunch"})

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


def process_daily_hours_penalties_for_prompt(
    employees,
    penalty_buffer_days,
    target_date,
    percentage_for_daily_hour_penalty,
    priority_field,
    custom_buffer_days
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
    daily_hours_records = target_date_attendance_exists(
        employees, target_date, 0, 0, 0, 1
    )

    # ! SKIP IF TARGET DATE ATTENDANCE IS NOT THERE
    if not daily_hours_records:
        return []

    # ? REMOVE EMPLOYEES WHOSE SHIFT IS NOT ASSIGNED
    daily_hours_records = {
        emp: data
        for emp, data in daily_hours_records.items()
        if check_if_shift_is_assign(emp, target_date)
    }

    # ! FILTER EMPLOYEES WHOSE DAILY HOURS ARE BELOW THRESHOLD
    daily_hours_records = get_below_threshold_daily_hours(
        daily_hours_records, percentage_for_daily_hour_penalty, target_date
    )

    # ? EMPLOYEES WHO HAD DAILY HOURS BELOW THRESHOLD ON TARGET DATE
    below_threshold_employees = list(daily_hours_records.keys())

    # ? LEAVE TYPES CONFIGURATION FOR DAILY HOURS PENALTY
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
    # ? IF NOT BELOW THRESHOLD EMPLOYEES
    if not below_threshold_employees:
        return penalty_entries
    # ? CALCULATE LEAVE DEDUCTIONS BASED ON PRIORITY CONFIGURATION
    # ? AND ADD TO PENALTY ENTRIES
    for employee in below_threshold_employees:
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
    employee_list = list(penalty_entries.keys())
    if not employee_list:
        return

    # ? FETCH EXISTING PENALTIES FOR THE TARGET DATE
    existing_penalties = frappe.get_all(
        "Employee Penalty",
        filters={"employee": ["in", employee_list], "penalty_date": target_date},
        fields=["name", "employee"],
    )
    existing_penalties_map = {ep["employee"]: ep["name"] for ep in existing_penalties}

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

    #! FETCH ALL PENDING ATTENDANCE REQUESTS IN ONE QUERY
    pending_requests = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": ["in", employee_list],
            "from_date": ["<=", target_date],
            "to_date": [">=", target_date],
            "custom_status": "Pending"
        },
        fields=["name", "employee"]
    )

    #! BUILD HASH MAP -> {employee: request_name}
    attendance_request_map = {}
    for req in pending_requests:
        attendance_request_map[req.employee] = req.name

    # ? LOOP AND PROCESS PENALTIES
    for employee, details in penalty_entries.items():
        # ? SKIP IF ATTENDANCE REQUEST EXIST AND IT IS PENDING
        if attendance_request_map.get(employee):
            continue
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
                    changes_made = True

            else:
                if details["attendance"] is None:
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
                    details["attendance"] = att_doc.name
                handle_leave_ledger(details, employee)
                penalty_doc = frappe.new_doc("Employee Penalty")
                penalty_doc.update(
                    {
                        "employee": employee,
                        "attendance": details["attendance"],
                        "penalty_date": target_date,
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

                changes_made = True

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

    employees = list(daily_hours_records.keys())

    # ? FETCH SHIFT ASSIGNMENTS FOR TARGET DATE (INCLUDING OPEN-ENDED)
    shift_assignments = frappe.get_all(
        "Shift Assignment",
        filters={
            "employee": ["in", employees],
            "docstatus": 1,
            "start_date": ["<=", target_date],
        },
        or_filters=[{"end_date": [">=", target_date]}, {"end_date": ["is", "not set"]}],
        fields=["employee", "shift_type"],
    )

    emp_shift_map = {sa.employee: sa.shift_type for sa in shift_assignments}

    # ? FETCH SHIFT TIMINGS FOR ASSIGNED SHIFT TYPES
    shift_types = list(set(emp_shift_map.values()))
    shift_details = frappe.get_all(
        "Shift Type",
        filters={"name": ["in", shift_types]},
        fields=["name", "start_time", "end_time"],
    )
    # ? MAP SHIFT NAME TO SHIFT DETAILS
    shift_time_map = {s.name: s for s in shift_details}

    below_threshold_records = {}

    # ? LOOP THROUGH DAILY HOURS RECORDS AND FILTER BASED ON THRESHOLD DURATION
    for emp, data in daily_hours_records.items():

        partial_days_request_minutes = frappe.db.get_value(
            "Attendance Request",
            {
                "employee": emp,
                "from_date": ["<=", target_date],
                "to_date": [">=", target_date],
                "custom_status": "Approved",
                "docstatus": ["!=", 2],
                "reason": "Partial Day"
            },
            "custom_partial_day_request_minutes"
        ) or 0

        working_hours = data.get("working_hours", 0)
        shift_type = emp_shift_map.get(emp)
        # ? SKIP IF WORKING HOUR IS ZERO AND HOLIDAY
        if working_hours == 0:
            if get_holiday_dates_for_employee(emp, target_date, target_date):
                continue

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
        if (working_hours + float(partial_days_request_minutes)/60) < threshold_hours:
            below_threshold_records[emp] = data

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
    employees, penalty_buffer_days, target_date, priority_field, custom_buffer_days
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
    attendance_records = target_date_attendance_exists(
        employees, target_date, 0, 1, 0, 0
    )
    employees_with_attendance = []
    if attendance_records:
        employees_with_attendance = list(attendance_records.keys())

    # ? FIND EMPLOYEES WITHOUT ATTENDANCE
    employees_without_attendance = list(set(employees) - set(employees_with_attendance))

    if employees_without_attendance:
        filtered_employees = []

        for emp in employees_without_attendance:
            # ? CHECK HOLIDAY
            if get_holiday_dates_for_employee(emp, target_date, target_date):
                continue
            # ? CHECK IF EMPLOYEE HAS LEAVE APPLICATION APPROVED
            # ? FOR THE TARGET DATE
            # ? SKIP IF EMPLOYEE HAS APPROVED LEAVE APPLICATION
            # ? FOR THE TARGET DATE
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

            filtered_employees.append(emp)

        if filtered_employees:
            # ! GET LEAVE PENALTY CONFIGURATION FOR NO ATTENDANCE PENALTY
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

            # ? CALCULATE LEAVE DEDUCTIONS BASED ON PRIORITY CONFIGURATION
            # ? AND ADD TO PENALTY ENTRIES
            # ? FOR EACH EMPLOYEE WITHOUT ATTENDANCE
            for emp in filtered_employees:
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

    return penalty_entries


def process_mispunch_penalties_for_prompt(
    employees, penalty_buffer_days, target_date, priority_field, custom_buffer_days
):
    """
    PROCESS MIS-PUNCH PENALTIES FOR EMPLOYEES WHO HAD MIS-PUNCHES
    AND CREATE 'MIS-PUNCH' ATTENDANCE RECORDS IF NOT HOLIDAY OR WEEKOFF.
    """
    penalty_entries = {}

    # ! CHECK TARGET DATE'S MISPUNCH ATTENDANCE IS EXISTS OR NOT
    mispunch_records = target_date_attendance_exists(employees, target_date, 0, 0, 1, 0)
    # ? RETURN IF BUFFER NOT CONFIGURED AND NOT CUSTOM BUFFER DAYS
    if not penalty_buffer_days and not custom_buffer_days:
        return penalty_entries
    if custom_buffer_days:
        penalty_buffer_days = 0

    # ? GET LEAVE PENALTY CONFIGURATION FOR MIS-PUNCH PENALTY
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
    # ? IF MISPUNCH RECORD FOUND
    if not mispunch_records:
        return penalty_entries
    # ? PROCESS EACH MIS-PUNCH RECORD
    for emp in mispunch_records.keys():
        # ? CHECK HOLIDAY
        if get_holiday_dates_for_employee(emp, target_date, target_date):
            continue
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

    return penalty_entries


def check_employee_penalty_criteria(employee=None, penalization_type=None):
    employee = frappe.get_doc("Employee", employee)
    company_abbr = frappe.db.get_value("Company", employee.company, "abbr")
    hr_settings = frappe.get_single("HR Settings")

    # Field mapping
    criteria = {
        "Business Unit": "custom_business_unit",
        "Department": "department",
        "Address": "custom_work_location",
        "Employment Type": "employment_type",
        "Employee Grade": "grade",
        "Designation": "designation",
        "Product Line": "custom_product_line",
    }

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

import frappe
from frappe.utils import getdate, today, add_to_date


def get_active_employees():
    return frappe.db.get_all("Employee", {"status": "Active"}, "name")


def check_if_day_is_valid(employee, date):
    return not frappe.db.exists(
        "Attendance Regularization", {"regularization_date": date, "employee": employee}
    )


@frappe.whitelist()
def prompt_employee_attendance_penalties():
    """
    MAIN METHOD: PROCESS ALL PENALTIES FOR ALL EMPLOYEES.
    RETURNS: List of all penalties with employee names.
    """
    employees = get_active_employees()
    all_penalties = []  # ! COLLECT PENALTIES FOR ALL EMPLOYEES

    for emp in employees:
        employee = emp["name"]
        employee_penalty = []  # ! PENALTIES FOR CURRENT EMPLOYEE

        # ? PROCESS LATE ENTRY PENALTY AND COLLECT RESULTS
        late_penalty = process_late_entry_penalties_for_prompt(employee)

        # ? ADD EMPLOYEE NAME TO EACH PENALTY RECORD
        for penalty in late_penalty:
            penalty["employee"] = employee
            employee_penalty.append(penalty)

        # ? EXTEND MASTER LIST
        all_penalties.extend(employee_penalty)

        # ? ADDITIONAL PENALTY TYPES CAN BE ADDED HERE
        # e.g., mispunch_penalty = process_mispunch(employee)
        # Add employee name and append like above

    return all_penalties  # List of dicts with all penalty info


def process_late_entry_penalties_for_prompt(employee):
    """
    Process late entry penalties for a given employee based on buffer days and attendance records.
    Returns a list of penalty entries.
    """
    penalty_entries = []

    # ? GET BUFFER DAYS FOR LATE ENTRY PENALTY FROM HR SETTINGS
    penalty_buffer_days = frappe.db.get_single_value(
        "HR Settings", "custom_buffer_period_for_leave_penalty_for_prompt"
    )

    # ? RETURN IF BUFFER NOT CONFIGURED
    if not penalty_buffer_days:
        return penalty_entries

    # ? CALCULATE TARGET DATE (attendance to check for penalty)
    target_date = getdate(add_to_date(today(), days=-(int(penalty_buffer_days) + 1)))

    # ? SKIP IF DAY IS REGULARIZED
    if not check_if_day_is_valid(employee, target_date):
        return penalty_entries

    # ? GET MONTH START DATE
    month_start_date = target_date.replace(day=1)

    # ? FETCH ATTENDANCE RECORDS WITH LATE ENTRY FROM MONTH START TO TARGET DATE
    late_attendance_list = frappe.db.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "docstatus": 1,
            "late_entry": 1,
            "attendance_date": ["between", [month_start_date, target_date]],
        },
        fields=["name", "attendance_date"],
        order_by="attendance_date asc",
    )

    monthly_late_entry_limit = frappe.db.get_single_value(
        "HR Settings", "custom_late_coming_allowed_per_month_for_prompt"
    )

    if not monthly_late_entry_limit:
        monthly_late_entry_limit = 0

    if len(late_attendance_list) <= monthly_late_entry_limit:
        return penalty_entries

    penalizable_attendances = late_attendance_list[monthly_late_entry_limit:]

    penalty_entries = calculate_late_entry_penalty_list(
        employee, penalizable_attendances
    )

    return penalty_entries


def calculate_late_entry_penalty_list(employee, penalizable_attendances):
    """
    Calculate penalty list for late entries using reusable leave deduction logic.
    """
    penalty_entries = []

    for _ in penalizable_attendances:
        deductions = calculate_leave_deductions_based_on_priority(
            employee=employee,
            deduction_amount=1.0,
            priority_field="custom_late_coming_leave_penalty_configuration",
            reason="Late Coming",
        )
        penalty_entries.extend(deductions)

    return penalty_entries


def calculate_leave_deductions_based_on_priority(
    employee, deduction_amount, priority_field, reason
):
    penalty_entries = []
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

    if not leave_priority:
        return penalty_entries

    leave_balances = get_remaining_leaves(employee)

    for config in leave_priority:
        deduction_type = config.get("penalty_deduction_type")
        leave_type = config.get("leave_type_for_penalty")
        deduction_of_leave = config.get("deduction_of_leave")

        leave_amount = 0.5 if deduction_of_leave == "Half Day" else 1.0

        # ! ENSURE leave_amount matches deduction_amount
        leave_amount = deduction_amount

        if deduction_type == "Deduct Earned Leave":
            balance = leave_balances.get(leave_type, 0.0)

            if balance >= leave_amount:
                penalty_entries.append(
                    {
                        "leave_type": leave_type,
                        "leave_amount": leave_amount,
                        "reason": reason,
                    }
                )
                return penalty_entries

        elif deduction_type == "Deduct Leave Without Pay":
            penalty_entries.append(
                {
                    "leave_type": "Leave Without Pay",
                    "leave_amount": leave_amount,
                    "reason": reason,
                }
            )
            return penalty_entries

    return penalty_entries  # fallback


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

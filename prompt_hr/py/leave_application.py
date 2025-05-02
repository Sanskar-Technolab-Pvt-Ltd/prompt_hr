import frappe
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import get_leave_type_details
from frappe import _
from frappe.utils import (
	get_datetime,
	get_first_day,
	get_last_day,
    flt,
    add_days,
    formatdate,
    getdate,
    date_diff,
    cint
)
from dateutil import relativedelta
from hrms.hr.utils import create_additional_leave_ledger_entry, get_monthly_earned_leave
import datetime
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import expire_allocation
from hrms.hr.utils import get_holiday_dates_for_employee
from hrms.hr.doctype.leave_application.leave_application import get_holidays


@frappe.whitelist()
def custom_grant_leave_alloc_for_employee(doc):
    if doc.leaves_allocated:
        frappe.throw(_("Leave already have been assigned for this Leave Policy Assignment"))
    else:
        leave_allocations = {}
        leave_type_details = get_leave_type_details()

        leave_policy = frappe.get_doc("Leave Policy", doc.leave_policy)
        date_of_joining = frappe.db.get_value("Employee", doc.employee, "date_of_joining")

        for leave_policy_detail in leave_policy.leave_policy_details:
            leave_details = leave_type_details.get(leave_policy_detail.leave_type)

            if not leave_details.is_lwp:
                leave_allocation, new_leaves_allocated = doc.create_leave_allocation(
                    leave_policy_detail.annual_allocation/4 if leave_details.earned_leave_frequency == 'Quarterly' else leave_policy_detail.annual_allocation,
                    leave_details,
                    date_of_joining,
                )
                leave_allocations[leave_details.name] = {
                    "name": leave_allocation,
                    "leaves": new_leaves_allocated,
                }
        doc.db_set("leaves_allocated", 1)
        return leave_allocations
    
def custom_check_effective_date(from_date, today=None, frequency=None, allocate_on_day=None):
    from_date = get_datetime(from_date)
    today = frappe.flags.current_date or get_datetime(today)
    rd = relativedelta.relativedelta(today, from_date)
    print(rd)
    expected_date = {
        "First Day": get_first_day(today),
        "Last Day": get_last_day(today),
        "Date of Joining": from_date,
    }.get(allocate_on_day)
    if not expected_date:
        return False

    if expected_date.day != today.day:
        return False

    if frequency == "Monthly":
        return True
    elif frequency == "Quarterly" and (rd.months) % 3 == 0:
        return True
    elif frequency == "Half-Yearly" and rd.months % 6:
        return True
    elif frequency == "Yearly" and rd.months % 12:
        return True

    return False

@frappe.whitelist()
def custom_update_previous_leave_allocation(allocation, annual_allocation, e_leave_type, date_of_joining):
    allocation = frappe.get_doc("Leave Allocation", allocation.name)
    annual_allocation = flt(annual_allocation, allocation.precision("total_leaves_allocated"))
    from_date = get_datetime(allocation.from_date)
    today = get_datetime()
    rd = relativedelta.relativedelta(today, from_date)

    expected_date = {
        "First Day": get_first_day(today),
        "Last Day": get_last_day(today),
        "Date of Joining": from_date,
    }[e_leave_type.allocate_on_day]

    earned_leaves = get_monthly_earned_leave(
        date_of_joining,
        annual_allocation,
        e_leave_type.earned_leave_frequency,
        e_leave_type.rounding,
    )

    expired_leaves = 0

    if expected_date.day == today.day and (rd.months % 6 == 0 or rd.months % 9 == 0):
        expired_leave_window_start = today - relativedelta.relativedelta(months=3)

        allocated_in_quarter = flt(annual_allocation) / 4

        used_leave_entries = frappe.db.sql(
            """
            SELECT leaves FROM `tabLeave Ledger Entry`
            WHERE
                employee = %(employee)s
                AND leave_type = %(leave_type)s
                AND docstatus = 1
                AND leaves < 0
                AND from_date BETWEEN %(start_date)s AND %(end_date)s
            """,
            {
                "employee": allocation.employee,
                "leave_type": allocation.leave_type,
                "start_date": add_days(expired_leave_window_start,1),
                "end_date": today
            },
            as_dict=True,
        )

        total_used_in_period = abs(sum(flt(entry.leaves) for entry in used_leave_entries))

        unused_leaves_in_period = allocated_in_quarter - total_used_in_period if total_used_in_period < allocated_in_quarter else 0

        # Make leaves negative to expire them
        expired_leaves = -1 * max(unused_leaves_in_period, 0)

    new_allocation = flt(allocation.total_leaves_allocated) + flt(earned_leaves)
    new_allocation_without_cf = flt(
        flt(allocation.get_existing_leave_count()) + flt(earned_leaves),
        allocation.precision("total_leaves_allocated"),
    )

    if new_allocation > e_leave_type.max_leaves_allowed and e_leave_type.max_leaves_allowed > 0:
        new_allocation = e_leave_type.max_leaves_allowed

    if (
        new_allocation != allocation.total_leaves_allocated
        and new_allocation_without_cf <= annual_allocation
    ):
        today_date = frappe.flags.current_date or getdate()

        allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
        create_additional_leave_ledger_entry(allocation, earned_leaves, today_date)
        if expired_leaves:
            ledger_entry = frappe.get_doc({
                "doctype": "Leave Ledger Entry",
                "employee": allocation.employee,
                "leave_type": allocation.leave_type,
                "company": allocation.company,
                "leaves": flt(expired_leaves),
                "transaction_type": "Leave Allocation",
                "transaction_name": allocation.name,
                "from_date": from_date,
                "to_date": allocation.to_date
            })
            ledger_entry.insert(ignore_permissions=True)
            ledger_entry.submit()
            
        if e_leave_type.allocate_on_day:
            text = _(
                "Allocated {0} leave(s) via scheduler on {1} based on the 'Allocate on Day' option set to {2}"
            ).format(
                frappe.bold(earned_leaves), frappe.bold(formatdate(today_date)), e_leave_type.allocate_on_day
            )
            allocation.add_comment(comment_type="Info", text=text)

@frappe.whitelist()
def custom_get_number_of_leave_days(
    employee: str,
	leave_type: str,
	from_date: datetime.date,
	to_date: datetime.date,
	half_day: int | str | None = None,
	half_day_date: datetime.date | str | None = None,
	holiday_list: str | None = None,
) -> float:
    """Returns number of leave days between 2 dates considering half-day, holidays, and sandwich rules"""
    number_of_days = 0
    if cint(half_day) == 1:
        if getdate(from_date) == getdate(to_date):
            number_of_days = 0.5
        elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
            number_of_days = date_diff(to_date, from_date) + 0.5
        else:
            number_of_days = date_diff(to_date, from_date) + 1
    else:
        number_of_days = date_diff(to_date, from_date) + 1

    if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
        number_of_days = flt(number_of_days) - flt(
            get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
        )
    
    # Sandwich Rule Extension
    leave_type_doc = frappe.get_doc("Leave Type", leave_type)
    if leave_type_doc.custom_is_sandwich_rule_applicable:
        if not holiday_list:
            holiday_list = get_holiday_list_for_employee(employee)
        holiday_list_doc = frappe.get_doc("Holiday List", holiday_list)
        all_holidays = list(get_holiday_dates_for_employee(
            employee,
            holiday_list_doc.from_date,
            holiday_list_doc.to_date
        ))
        additional_days = 0
        if leave_type_doc.custom_adjoins_weekoff:
            additional_days += len(get_all_weekoff_days(from_date, to_date, holiday_list))

        if leave_type_doc.custom_adjoins_holiday:
            additional_days += len(get_all_holidays(from_date, to_date, holiday_list))
        if (
            leave_type_doc.custom_consider_full_day_leave_for_before_day or
            leave_type_doc.custom_consider_full_day_leave_for_after_day
        ):
            additional_days += len(get_all_holidays(from_date, to_date, holiday_list))
            additional_days += len(get_all_weekoff_days(from_date, to_date, holiday_list))
            if not (leave_type_doc.custom_ignore_if_half_day_leave_for_day_before_or_day_after and half_day):
                if leave_type_doc.custom_consider_full_day_leave_for_before_day:
                    for i in range(1, len(all_holidays)):
                        future_day = add_days(to_date, i)
                        if str(future_day) in all_holidays:
                            additional_days += 1
                        else:
                            break

                if leave_type_doc.custom_consider_full_day_leave_for_after_day:
                    for i in range(1, len(all_holidays)):
                        previous_day = add_days(from_date, -i)
                        if str(previous_day) in all_holidays:
                            additional_days += 1
                        else:
                            break
        number_of_days += additional_days
        
    return number_of_days


def get_all_weekoff_days(from_date, to_date, holiday_list_name):
    return [
        d[0] for d in frappe.db.sql(
            """
            SELECT holiday_date 
            FROM `tabHoliday` 
            WHERE holiday_date > %s AND holiday_date < %s
            AND weekly_off = 1 
            AND parent = %s
            """,
            (from_date, to_date, holiday_list_name)
        )
    ]

def get_all_holidays(from_date, to_date, holiday_list_name):
    return [
        d[0] for d in frappe.db.sql(
            """
            SELECT holiday_date 
            FROM `tabHoliday` 
            WHERE holiday_date > %s AND holiday_date < %s
            AND weekly_off = 0 
            AND parent = %s
            """,
            (from_date, to_date, holiday_list_name)
        )
    ]

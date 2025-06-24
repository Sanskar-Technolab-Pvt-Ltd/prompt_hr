import frappe
from frappe.utils import (
    flt,
    add_days,
    getdate,
    date_diff,
    cint,
)
import datetime, json
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.hr.utils import get_holiday_dates_for_employee
from hrms.hr.doctype.leave_application.leave_application import get_holidays

# prompt_hr.api.mobile.total_leaves.get_number_of_leave_days
@frappe.whitelist()
def get(
    employee: str,
    leave_type: str,
    from_date: datetime.date,
    to_date: datetime.date,
    half_day: int | str | None = None,
    half_day_date: datetime.date | str | None = None,
    holiday_list: str | None = None,
    custom_half_day_time: str | None = None,
) -> float:

    try:
        """Returns number of leave days between 2 dates considering half-day, holidays, and sandwich rules"""
        # if not custom_half_day_time:
        #     doc_json = frappe.form_dict.get("doc")
        #     if doc_json:
        #         doc = json.loads(doc_json)
        #         custom_half_day_time = doc.get("custom_half_day_time")
        #         half_day = doc.get("half_day")
        #         half_day_date = doc.get("half_day_date")

        if (half_day or half_day_date) and not custom_half_day_time:
            leave_app = frappe.get_all(
                "Leave Application",
                filters={
                    "employee": employee,
                    "from_date": from_date,
                    "to_date": to_date,
                    "half_day": 1,
                    "docstatus": 1
                },
                fields=["name", "custom_half_day_time", "half_day", "half_day_date"],
                limit=1,
            )
            if leave_app:
                custom_half_day_time = leave_app[0].custom_half_day_time
            else:
                if not custom_half_day_time:
                    doc_json = frappe.form_dict.get("doc")
                    if doc_json:
                        doc = json.loads(doc_json)
                        custom_half_day_time = doc.get("custom_half_day_time")
        else:
            if half_day is None:
                doc_json = frappe.form_dict.get("doc")
                if doc_json:
                    doc = json.loads(doc_json)
                    custom_half_day_time = doc.get("custom_half_day_time")
                    half_day_date = doc.get("half_day_date")
                    half_day = doc.get("half_day")

        if not holiday_list:
            holiday_list = get_holiday_list_for_employee(employee)

        number_of_days = 0
        if cint(half_day) == 1:
            if getdate(from_date) == getdate(to_date):
                number_of_days = 0.5
            elif half_day_date and getdate(from_date) <= getdate(
                half_day_date
            ) <= getdate(to_date):
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

        if any(
            [
                leave_type_doc.custom_sw_applicable_to_business_unit,
                leave_type_doc.custom_sw_applicable_to_department,
                leave_type_doc.custom_sw_applicable_to_location,
                leave_type_doc.custom_sw_applicable_to_employment_type,
                leave_type_doc.custom_sw_applicable_to_grade,
                leave_type_doc.custom_sw_applicable_to_product_line,
            ]
        ):
            employee_doc = frappe.get_doc("Employee", employee)

            # Format: (LeaveType field, Employee field)
            criteria = [
                ("custom_sw_applicable_to_business_unit", "custom_business_unit"),
                ("custom_sw_applicable_to_department", "department"),
                ("custom_sw_applicable_to_location", "custom_work_location"),
                ("custom_sw_applicable_to_employment_type", "employment_type"),
                ("custom_sw_applicable_to_grade", "grade"),
                ("custom_sw_applicable_to_product_line", "custom_product_line"),
            ]

            for leave_field, employee_field in criteria:
                leave_values = getattr(leave_type_doc, leave_field)
                employee_value = getattr(employee_doc, employee_field)

                if not leave_values:
                    continue

                leave_ids = []

                if isinstance(leave_values, list) and isinstance(
                    leave_values[0], frappe.model.document.Document
                ):
                    for d in leave_values:
                        if not d:
                            continue

                        if leave_field == "custom_sw_applicable_to_product_line":
                            leave_ids.append(
                                frappe.get_doc(
                                    "Product Line Multiselect", d.name
                                ).indifoss_product
                            )
                        elif leave_field == "custom_sw_applicable_to_business_unit":
                            leave_ids.append(
                                frappe.get_doc(
                                    "Business Unit Multiselect", d.name
                                ).business_unit
                            )
                        elif leave_field == "custom_sw_applicable_to_department":
                            leave_ids.append(
                                frappe.get_doc(
                                    "Department Multiselect", d.name
                                ).department
                            )
                        elif leave_field == "custom_sw_applicable_to_location":
                            leave_ids.append(
                                frappe.get_doc(
                                    "Work Location Multiselect", d.name
                                ).work_location
                            )
                        elif leave_field == "custom_sw_applicable_to_employment_type":
                            leave_ids.append(
                                frappe.get_doc(
                                    "Employment Type Multiselect", d.name
                                ).employment_type
                            )
                        elif leave_field == "custom_sw_applicable_to_grade":
                            leave_ids.append(
                                frappe.get_doc("Grade Multiselect", d.name).grade
                            )

                if employee_value in leave_ids:
                    frappe.local.response["message"] = {
                        "success": True,
                        "message": "Leaves Days Calculated Successfully!",
                        "data": get_additional_days(
                            leave_type_doc,
                            employee,
                            from_date,
                            to_date,
                            number_of_days,
                            half_day,
                            holiday_list,
                            half_day_date,
                            custom_half_day_time,
                        ),
                    }
            else:
                frappe.local.response["message"] = {
                    "success": True,
                    "message": "Leaves Days Calculated Successfully!",
                    "data": number_of_days,
                }

        
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leaves Days Calculated Successfully!",
            "data": get_additional_days(
                leave_type_doc,
                employee,
                from_date,
                to_date,
                number_of_days,
                half_day,
                holiday_list,
                half_day_date,
                custom_half_day_time,
            ),
        }

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Leaves days", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Leaves days: {str(e)}",
            "data": None,
        }


def get_additional_days(
    leave_type_doc,
    employee,
    from_date,
    to_date,
    number_of_days,
    half_day,
    holiday_list,
    half_day_date,
    custom_half_day_time,
):
    """
    Calculate additional days for leave based on sandwich rule, weekoffs, and holidays.
    """
    try:
        # Convert dates to proper date objects
        from_date = getdate(from_date)
        to_date = getdate(to_date)

        if not leave_type_doc.custom_is_sandwich_rule_applicable:
            return number_of_days

        if not holiday_list:
            holiday_list = get_holiday_list_for_employee(employee)

        holiday_list_doc = frappe.get_doc("Holiday List", holiday_list)
        all_holidays = list(
            get_holiday_dates_for_employee(
                employee, holiday_list_doc.from_date, holiday_list_doc.to_date
            )
        )

        additional_days = 0
        # Ignore Holidays for First and Last Days
        while (
            next_day_is_holiday_or_weekoff(from_date, holiday_list)
            and from_date <= to_date
        ):
            from_date = add_days(from_date, 1)
        while (
            next_day_is_holiday_or_weekoff(to_date, holiday_list)
            and to_date >= from_date
        ):
            to_date = add_days(to_date, -1)
        # Convert half_day_date to date object
        if half_day_date:
            half_day_date = getdate(half_day_date)
        # Process weekoff days
        if leave_type_doc.custom_adjoins_weekoff:
            if (
                leave_type_doc.custom_ignore_if_half_day_leave_for_day_before_or_day_after
                and cint(half_day)
            ):
                if half_day_date:
                    if half_day_date != from_date and half_day_date != to_date:
                        if str(half_day_date) not in all_holidays:
                            # Exclude adjacent days if half-day is not on boundary
                            additional_days += len(
                                get_all_weekoff_days(
                                    from_date, to_date, holiday_list, half_day_date
                                )
                            )
            else:
                # Always include full weekoffs in range
                additional_days += len(
                    get_all_weekoff_days(from_date, to_date, holiday_list)
                )

        # Process holiday days
        if leave_type_doc.custom_adjoins_holiday:
            if (
                leave_type_doc.custom_ignore_if_half_day_leave_for_day_before_or_day_after
                and cint(half_day)
            ):
                if half_day_date:
                    if (
                        half_day_date == from_date
                        or half_day_date == to_date
                        or str(half_day_date) in all_holidays
                    ):
                        additional_days += 0
                    else:
                        # Get holidays between leave dates, excluding days adjacent to half-day
                        additional_days += len(
                            get_all_holidays(
                                from_date, to_date, holiday_list, half_day_date
                            )
                        )
            else:
                # Get all holidays between leave dates which is not weekoff
                additional_days += len(
                    get_all_holidays(from_date, to_date, holiday_list)
                )

        if (
            (
                leave_type_doc.custom_half_day_leave_taken_in_second_half_on_day_before
                or leave_type_doc.custom_half_day_leave_taken_in_first_half_on_day_after
            )
            and not leave_type_doc.custom_ignore_if_half_day_leave_for_day_before_or_day_after
        ):

            # Handle half-day in second half on day before
            if (
                leave_type_doc.custom_half_day_leave_taken_in_second_half_on_day_before
                and str(half_day_date) not in all_holidays
            ):
                if half_day and half_day_date:
                    if custom_half_day_time == "First":
                        next_day = add_days(half_day_date, 1)
                        if (
                            leave_type_doc.custom_adjoins_holiday
                            and leave_type_doc.custom_adjoins_weekoff
                        ):
                            while next_day_is_holiday_or_weekoff(
                                next_day, holiday_list
                            ):
                                additional_days -= 1
                                next_day = add_days(next_day, 1)
                        elif leave_type_doc.custom_adjoins_holiday:
                            while (
                                next_day_is_holiday(next_day, holiday_list)
                                and next_day <= to_date
                            ):
                                additional_days -= 1
                                next_day = add_days(next_day, 1)
                        elif leave_type_doc.custom_adjoins_weekoff:
                            while (
                                next_day_is_weekoff(next_day, holiday_list)
                                and next_day <= to_date
                            ):
                                additional_days -= 1
                                next_day = add_days(next_day, 1)

            # Handle half-day in first half on day after
            if (
                leave_type_doc.custom_half_day_leave_taken_in_first_half_on_day_after
                and str(half_day_date) not in all_holidays
            ):
                if half_day and half_day_date:
                    if custom_half_day_time == "Second":
                        prev_day = add_days(half_day_date, -1)
                        if (
                            leave_type_doc.custom_adjoins_holiday
                            and leave_type_doc.custom_adjoins_weekoff
                        ):
                            while next_day_is_holiday_or_weekoff(
                                prev_day, holiday_list
                            ):
                                additional_days -= 1
                                prev_day = add_days(prev_day, -1)
                        elif leave_type_doc.custom_adjoins_holiday:
                            while (
                                next_day_is_holiday(prev_day, holiday_list)
                                and prev_day >= from_date
                            ):
                                additional_days -= 1
                                prev_day = add_days(prev_day, -1)
                        elif leave_type_doc.custom_adjoins_weekoff:
                            while (
                                next_day_is_weekoff(prev_day, holiday_list)
                                and prev_day >= from_date
                            ):
                                additional_days -= 1
                                prev_day = add_days(prev_day, -1)
        # Add the additional days to the total
        number_of_days += additional_days

        return number_of_days
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Leaves days", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Leaves days: {str(e)}",
            "data": None,
        }


def next_day_is_holiday_or_weekoff(date, holiday_list):
    """Check if the given date is a holiday or weekoff"""
    is_holiday = frappe.db.exists(
        "Holiday", {"parent": holiday_list, "holiday_date": date}
    )
    return bool(is_holiday)


def next_day_is_holiday(date, holiday_list):
    """Check if the given date is a holiday"""
    is_holiday = frappe.db.exists(
        "Holiday", {"parent": holiday_list, "holiday_date": date, "weekly_off": 0}
    )
    return bool(is_holiday)


def next_day_is_weekoff(date, holiday_list):
    """Check if the given date is a weekoff"""
    is_weekoff = frappe.db.exists(
        "Holiday", {"parent": holiday_list, "holiday_date": date, "weekly_off": 1}
    )
    return bool(is_weekoff)


def get_all_weekoff_days(from_date, to_date, holiday_list_name, half_day_date=None):
    """
    Get all weekoff days between from_date and to_date.
    If half_day_date is provided, exclude the day after and before the half day.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    # For proper SQL comparison
    from_date_str = from_date.strftime("%Y-%m-%d")
    to_date_str = to_date.strftime("%Y-%m-%d")
    conditions = """
        holiday_date > %s AND holiday_date < %s
        AND weekly_off = 1 
        AND parent = %s
    """

    params = [from_date_str, to_date_str, holiday_list_name]

    if half_day_date:
        half_day_date = getdate(half_day_date)
        half_day_date_str = half_day_date.strftime("%Y-%m-%d")
        next_day = add_days(half_day_date, 1)
        prev_day = add_days(half_day_date, -1)

        # Skip the day immediately after half day if half day is on Friday
        if half_day_date.weekday() == 4:  # Friday is weekday 4
            conditions += " AND holiday_date != %s"
            params.append(next_day.strftime("%Y-%m-%d"))
        else:
            # Otherwise skip days adjacent to half day
            conditions += " AND holiday_date NOT IN (%s, %s, %s)"
            params.extend(
                [
                    half_day_date_str,
                    prev_day.strftime("%Y-%m-%d"),
                    next_day.strftime("%Y-%m-%d"),
                ]
            )

    return [
        getdate(d[0])
        for d in frappe.db.sql(
            f"""
            SELECT holiday_date 
            FROM `tabHoliday` 
            WHERE {conditions}
            """,
            tuple(params),
        )
    ]


def get_all_holidays(from_date, to_date, holiday_list_name, half_day_date=None):
    """
    Get all holidays (non-weekoffs) between from_date and to_date.
    If half_day_date is provided, exclude the day after and before the half day.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    # For proper SQL comparison
    from_date_str = from_date.strftime("%Y-%m-%d")
    to_date_str = to_date.strftime("%Y-%m-%d")

    conditions = """
        holiday_date > %s AND holiday_date < %s
        AND weekly_off = 0 
        AND parent = %s
    """

    params = [from_date_str, to_date_str, holiday_list_name]

    if half_day_date:
        half_day_date = getdate(half_day_date)
        half_day_date_str = half_day_date.strftime("%Y-%m-%d")
        next_day = add_days(half_day_date, 1)
        prev_day = add_days(half_day_date, -1)

        # Skip the day immediately after half day if half day is on Friday
        if half_day_date.weekday() == 4:  # Friday is weekday 4
            conditions += " AND holiday_date != %s"
            params.append(next_day.strftime("%Y-%m-%d"))
        else:
            # Otherwise skip days adjacent to half day
            conditions += " AND holiday_date NOT IN (%s, %s, %s)"
            params.extend(
                [
                    half_day_date_str,
                    prev_day.strftime("%Y-%m-%d"),
                    next_day.strftime("%Y-%m-%d"),
                ]
            )

    return [
        getdate(d[0])
        for d in frappe.db.sql(
            f"""
            SELECT holiday_date 
            FROM `tabHoliday` 
            WHERE {conditions}
            """,
            tuple(params),
        )
    ]

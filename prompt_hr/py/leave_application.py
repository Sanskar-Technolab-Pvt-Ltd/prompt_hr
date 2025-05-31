import frappe
from dateutil import relativedelta
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
    cint,
)
from dateutil import relativedelta
from hrms.hr.utils import create_additional_leave_ledger_entry, get_monthly_earned_leave
import datetime
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.hr.report.employee_leave_balance.employee_leave_balance import get_leave_ledger_entries
from hrms.hr.utils import get_holiday_dates_for_employee
from hrms.hr.doctype.leave_application.leave_application import (
    get_holidays,
    get_leave_allocation_records,
    get_leave_approver,
    get_leave_balance_on,
    get_leaves_for_period,
    get_leaves_pending_approval_for_period,
)

def on_cancel(doc, method):
    if doc.get("workflow_state"):
        doc.db_set("workflow_state", "Cancelled")
    if doc.get("custom_leave_status"):
        doc.db_set("custom_leave_status", "Cancelled")

def before_save(doc, method):
    if hasattr(doc, '_original_date'):  
        doc.set("from_date", doc._original_date)  
        doc.total_leave_days = custom_get_number_of_leave_days(
				doc.employee,
				doc.leave_type,
				doc.from_date,
				doc.to_date,
				doc.half_day,
				doc.half_day_date,
		)
    employee_doc = frappe.get_doc("Employee", doc.employee)
    reporting_manager = frappe.get_doc("Employee", employee_doc.reports_to)
    leave_type_doc = frappe.get_doc("Leave Type", doc.leave_type)
    if reporting_manager.user_id:
        doc.db_set("leave_approver", reporting_manager.user_id)
    if employee_doc.resignation_letter_date:
        if not leave_type_doc.custom_allow_for_employees_who_are_on_notice_period:
            if frappe.utils.getdate(doc.to_date) >= employee_doc.resignation_letter_date:
                frappe.throw(_("{0} cannot be applied during notice period.").format(leave_type_doc.name))     
    if leave_type_doc.custom_require_attachment:
        if not doc.custom_attachment:
            frappe.throw(_("Please attach a file for {0}").format(leave_type_doc.name))

def before_insert(doc, method):
    leave_type_doc = frappe.get_doc("Leave Type", doc.leave_type)
    if leave_type_doc.custom_prior_days_required_for_applying_leave:
        if doc.from_date:
            if date_diff(doc.from_date, frappe.utils.getdate()) <= leave_type_doc.custom_prior_days_required_for_applying_leave:
                frappe.throw(_("You must apply at least {0} days before the leave date").format(leave_type_doc.custom_prior_days_required_for_applying_leave))

def before_validate(doc, method=None):
    if doc.custom_leave_status == "Confirmed":
        doc._original_date = doc.get("from_date")  
        doc.set("from_date", frappe.utils.add_days(doc.custom_original_to_date,1))  

def before_submit(doc, method):
    if doc.custom_leave_status == "Confirmed":
        if hasattr(doc, '_original_date'):  
            doc.set("from_date", doc._original_date)  
            doc.total_leave_days = custom_get_number_of_leave_days(
                    doc.employee,
                    doc.leave_type,
                    doc.from_date,
                    doc.to_date,
                    doc.half_day,
                    doc.half_day_date,
            )
            entry = frappe.get_all(
                "Leave Ledger Entry",
                filters={"transaction_name": doc.name, "docstatus": 1},
                order_by="creation desc",
                limit=1
            )

            if entry:
                entry_name = entry[0].name
                entry_doc = frappe.get_doc("Leave Ledger Entry", entry_name)
                entry_doc.db_set("docstatus", 2)
                frappe.delete_doc("Leave Ledger Entry", entry_name)


def on_update(doc, method):
    employee = frappe.get_doc("Employee", doc.employee)
    employee_id = employee.get("user_id")
    reporting_manager = frappe.get_doc("Employee", employee.reports_to)
    reporting_manager_name = reporting_manager.get("employee_name")
    reporting_manager_id = reporting_manager.get("user_id")
    hr_manager_email = None
    hr_manager_users = frappe.get_all(
        "Employee",
        filters={"company": employee.company},
        fields=["user_id"]
    )
    other_recipents = []
    if doc.custom_email_cc:
        user_emails = frappe.get_all(
            "User Email CC",
            filters={"parent": doc.name},
            fields=["user"]
        )
        for user_email in user_emails:
            other_recipents.append(user_email.get("user"))
            
    for hr_manager in hr_manager_users:
        hr_manager_user = hr_manager.get("user_id")
        if hr_manager_user:
            # Check if this user has the HR Manager role
            if "HR Manager" in frappe.get_roles(hr_manager_user):
                hr_manager_email = frappe.db.get_value("User", hr_manager_user, "email")
                break

                        
    if doc.workflow_state == "Pending":
        notification = frappe.get_doc("Notification", "Leave Request Notification")
        if notification:
            # Notify the Reporting Manager about the leave request.
            subject = frappe.render_template(notification.subject, {"doc":doc,"request_type":"Leave Application"})
            if reporting_manager_id:
                frappe.sendmail(
                recipients=reporting_manager_id,
                cc = other_recipents,
                message = frappe.render_template(notification.message, {"doc": doc,"role":"Reporting Manager"}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                expose_recipients="header"
            )

    elif doc.workflow_state == "Approved":
        doc.db_set("status", "Approved")
        employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
        hr_notification = frappe.get_doc("Notification", "Leave Request Status Update to HR Manager")
        if employee_notification:
            # Notify the employee regarding the approval of their leave by Reporting Manager.
            subject = frappe.render_template(employee_notification.subject, {"doc":doc,"manager":reporting_manager_name,"request_type":"Leave Application"})
            if employee_id:
                frappe.sendmail(
                recipients=employee_id,
                cc = other_recipents,
                message = frappe.render_template(employee_notification.message, {"doc": doc}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                expose_recipients="header"
            )
        # if hr_notification:
        #     # Notify HR Manager regarding the approval of the leave by Reporting Manager.
        #     frappe.sendmail(
        #         recipients=hr_manager_email,
        #         message = frappe.render_template(hr_notification.message, {"doc": doc, "manager":reporting_manager_name}),
        #         subject = frappe.render_template(hr_notification.subject, {"doc":doc,"manager":reporting_manager_name, "request_type":"Leave Application"}),
        #         reference_doctype=doc.doctype,
        #         reference_name=doc.name,
        #     )

        #     if not hr_manager_email:
        #         frappe.throw("HR Manager email not found.")

    elif doc.workflow_state == "Rejected":
        doc.db_set("status", "Rejected")
        employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
        if employee_notification:
            # Notify the employee regarding the rejection of their leave.
            subject = frappe.render_template(employee_notification.subject, {"doc":doc, "manager":reporting_manager_name,"request_type":"Leave Application"})
            if employee_id:
                frappe.sendmail(
                recipients=employee_id,
                cc = other_recipents,
                message = frappe.render_template(employee_notification.message, {"doc": doc}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                expose_recipients="header"
            )

    elif doc.workflow_state == "Confirmed":
        employee_notification = frappe.get_doc("Notification", "Leave Status Update to Employee")
        if employee_notification:
            # Notify the employee regarding the confirmation of their leave.
            subject = frappe.render_template(employee_notification.subject, {"doc":doc,"request_type":"Leave Application"})
            if employee_id and not doc.flags.skip_workflow_email:
                frappe.sendmail(
                recipients=employee_id,
                message = frappe.render_template(employee_notification.message, {"doc": doc}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )
                
    elif doc.workflow_state == "Extension Requested":
        notification = frappe.get_doc("Notification", "Leave Extension Request Notification")
        if notification:
            # Notify the Reporting Manager about the leave extension request.
            subject = frappe.render_template(notification.subject, {"doc":doc,})
            if reporting_manager_id:
                frappe.sendmail(
                recipients=reporting_manager_id,
                cc = other_recipents,
                message = frappe.render_template(notification.message, {"doc": doc}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                expose_recipients="header"
            )
                
    elif doc.workflow_state == "Extension Approved" or doc.workflow_state == "Extension Rejected":
        employee_notification = frappe.get_doc("Notification", "Leave Extension Request Response By Reporting Manager")
        if doc.workflow_state == "Extension Approved":
            doc.db_set("custom_extension_status", "Approved")
        else:
            doc.db_set("custom_extension_status", "Rejected")
            doc.db_set("to_date", doc.custom_original_to_date)
            total_leaves = custom_get_number_of_leave_days(doc.employee, doc.leave_type, doc.from_date, doc.custom_original_to_date, doc.half_day, doc.half_day_date, doc.custom_half_day_time)
            doc.db_set("total_leave_days", total_leaves)
            doc.db_set("docstatus",0)

        if employee_notification:
            # Notify the employee regarding the approval/rejection of their leave extension.
            subject = frappe.render_template(employee_notification.subject, {"doc":doc})
            if employee_id:
                frappe.sendmail(
                recipients=employee_id,
                cc = other_recipents,
                message = frappe.render_template(employee_notification.message, {"doc": doc}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                expose_recipients="header"
            )
                
    elif doc.workflow_state == "Extension Confirmed":
        employee_notification = frappe.get_doc("Notification", "Leave Extension Confirmation")
        if employee_notification:
            # Notify the employee regarding the confirmation of their leave extension.
            subject = frappe.render_template(employee_notification.subject, {"doc":doc})
            if employee_id:
                frappe.sendmail(
                recipients=employee_id,
                message = frappe.render_template(employee_notification.message, {"doc": doc}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )
            
@frappe.whitelist()
def extend_leave_application(leave_application, extend_to):
    leave_application = frappe.get_doc("Leave Application", leave_application)
    if getdate(extend_to) <= getdate(leave_application.to_date):
        frappe.throw(_("Extended Date must be after previous To Date"))
    cur_docstatus = leave_application.docstatus
    cur_workflow_state = leave_application.workflow_state
    try:
        frappe.db.begin()
        leave_application.db_set("docstatus", 0)
        leave_application.db_set("custom_leave_status", leave_application.workflow_state)
        leave_application.db_set("workflow_state", "Extension Requested")
        leave_application.db_set("custom_original_to_date", leave_application.to_date)
        if leave_application.custom_leave_status == "Confirmed":
            leave_application.from_date = leave_application.to_date
        leave_application.to_date = extend_to
        leave_application.save()
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        leave_application.db_set("docstatus", cur_docstatus)
        leave_application.db_set("workflow_state", cur_workflow_state)
        raise e
    
@frappe.whitelist()
def get_optional_festival_holiday_leave_list(company, employee, leave_type):
    # Validate input
    if not company:
        frappe.throw("Company is required")
    options = []
    festival_holiday_lists = frappe.get_all(
        "Festival Holiday List",
        filters={"company": company},
        fields=["name"]
    )
    if employee:
        leave_application = frappe.get_all(
            "Leave Application",
            filters={"employee": employee, "leave_type": leave_type},
            or_filters = {
                "workflow_state": "Confirmed",
                "custom_leave_status": "Confirmed",
            },
            fields=["from_date"],
            pluck="from_date"
        )
    else:
        leave_application = []

    for festival_holiday_list in festival_holiday_lists:
        holidays = frappe.get_all(
            "Holiday",
            filters={
                "parent": festival_holiday_list.name,
                "custom_is_optional_festival_leave": 1
            },
            fields=["name", "holiday_date", "description"],
            order_by="holiday_date"
        )
        for holiday in holidays:
            if leave_application:
                if holiday.holiday_date in leave_application:
                    continue
            label = f"{holiday.description or holiday.name} ({frappe.utils.format_date(holiday.holiday_date, 'dd-MM-yyyy')})"
            options.append({"label": label, "value": label, "holiday_date": holiday.holiday_date})
    return options


def custom_check_effective_date(from_date, today=None, frequency=None, allocate_on_day=None):
    from_date = get_datetime(from_date)
    today = frappe.flags.current_date or get_datetime(today)
    rd = relativedelta.relativedelta(today, from_date)
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


def get_quarter(date, start_date):
    rd = relativedelta.relativedelta(date, start_date)
    return (rd.months // 3) + 1  # Q1 = 1, Q2 = 2, etc.

def custom_update_previous_leave_allocation(allocation, annual_allocation, e_leave_type, date_of_joining):
    allocation = frappe.get_doc("Leave Allocation", allocation.name)
    annual_allocation = flt(annual_allocation, allocation.precision("total_leaves_allocated"))

    from_date = get_datetime(allocation.from_date)
    today = get_datetime()

    earned_leaves = get_monthly_earned_leave(
        date_of_joining,
        annual_allocation,
        e_leave_type.earned_leave_frequency,
        e_leave_type.rounding,
    )
    expected_date = {
        "First Day": get_first_day(today),
        "Last Day": get_last_day(today),
        "Date of Joining": from_date,
    }[e_leave_type.allocate_on_day]

    expired_leaves = 0
    e_leave_type = frappe.get_doc("Leave Type", allocation.leave_type)
    is_quarterly_carryforward_rule_applied = e_leave_type.custom_is_quarterly_carryforward_rule_applied

    if is_quarterly_carryforward_rule_applied:
        current_quarter = "Q" + str(get_quarter(today, from_date))
        # Match rule where current quarter is the "Expired by Quarter Start"
        mapped_accrual_quarter = None
        for row in e_leave_type.custom_quaterly_expire_rule:
            if row.expired_by_quater_start == current_quarter:
                mapped_accrual_quarter = row.accrued_on_quater
                break

        if (
            mapped_accrual_quarter
            and expected_date.day == today.day
            and (
                (e_leave_type.custom_apply_quarterly_rule_based_on_salary_criteria
                and e_leave_type.custom_minimum_ctc_for_quarterly_lapse_rule
                    < frappe.db.get_value("Employee", allocation.employee, "ctc"))
                or not e_leave_type.custom_apply_quarterly_rule_based_on_salary_criteria
            )
        ):

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

            total_used = abs(sum(flt(entry.leaves) for entry in used_leave_entries))
            unused = allocated_in_quarter - total_used if total_used < allocated_in_quarter else 0
            expired_leaves = -1 * max(unused, 0)

    new_allocation = flt(allocation.total_leaves_allocated) + flt(earned_leaves)
    new_allocation_without_cf = flt(
        flt(allocation.get_existing_leave_count()) + flt(earned_leaves),
        allocation.precision("total_leaves_allocated"),
    )

    if new_allocation > e_leave_type.max_leaves_allowed and e_leave_type.max_leaves_allowed > 0:
        new_allocation = e_leave_type.max_leaves_allowed

    if new_allocation != allocation.total_leaves_allocated and new_allocation_without_cf <= annual_allocation:
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
                "from_date": today_date,
                "to_date": allocation.to_date
            })
            ledger_entry.insert(ignore_permissions=True)
            ledger_entry.submit()

        if e_leave_type.allocate_on_day:
            allocation.add_comment(
                comment_type="Info",
                text=_(
                    "Allocated {0} leave(s) via scheduler on {1} based on the 'Allocate on Day' option set to {2}"
                ).format(
                    frappe.bold(earned_leaves), frappe.bold(formatdate(today_date)), e_leave_type.allocate_on_day
                )
            )

@frappe.whitelist()
def custom_get_number_of_leave_days(
    employee: str,
	leave_type: str,
	from_date: datetime.date,
	to_date: datetime.date,
	half_day: int | str | None = None,
	half_day_date: datetime.date | str | None = None,
	holiday_list: str | None = None,
    custom_half_day_time: str | None = None
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

    if any([
        leave_type_doc.custom_sw_applicable_to_business_unit,
        leave_type_doc.custom_sw_applicable_to_department,
        leave_type_doc.custom_sw_applicable_to_location,
        leave_type_doc.custom_sw_applicable_to_employment_type,
        leave_type_doc.custom_sw_applicable_to_grade,
        leave_type_doc.custom_sw_applicable_to_product_line
    ]):
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

            if isinstance(leave_values, list) and isinstance(leave_values[0], frappe.model.document.Document):
                for d in leave_values:
                    if not d:
                        continue

                    if leave_field == "custom_sw_applicable_to_product_line":
                        leave_ids.append(frappe.get_doc("Product Line Multiselect", d.name).indifoss_product)
                    elif leave_field == "custom_sw_applicable_to_business_unit":
                        leave_ids.append(frappe.get_doc("Business Unit Multiselect", d.name).business_unit)
                    elif leave_field == "custom_sw_applicable_to_department":
                        leave_ids.append(frappe.get_doc("Department Multiselect", d.name).department)
                    elif leave_field == "custom_sw_applicable_to_location":
                        leave_ids.append(frappe.get_doc("Work Location Multiselect", d.name).work_location)
                    elif leave_field == "custom_sw_applicable_to_employment_type":
                        leave_ids.append(frappe.get_doc("Employment Type Multiselect", d.name).employment_type)
                    elif leave_field == "custom_sw_applicable_to_grade":
                        leave_ids.append(frappe.get_doc("Grade Multiselect", d.name).grade)

            if employee_value in leave_ids:
                return get_additional_days(
                    leave_type_doc,
                    employee,
                    from_date,
                    to_date,
                    number_of_days,
                    half_day,
                    holiday_list,
                    half_day_date,
                    custom_half_day_time
                )
        else:
            return number_of_days

    return get_additional_days(
        leave_type_doc,
        employee,
        from_date,
        to_date,
        number_of_days,
        half_day,
        holiday_list,
        half_day_date,
        custom_half_day_time
    )

def get_additional_days(leave_type_doc, employee, from_date, to_date, number_of_days, half_day, holiday_list, half_day_date, custom_half_day_time):
    """
    Calculate additional days for leave based on sandwich rule, weekoffs, and holidays.
    """
    # Convert dates to proper date objects
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    
    if not leave_type_doc.custom_is_sandwich_rule_applicable:
        return number_of_days
        
    if not holiday_list:
        holiday_list = get_holiday_list_for_employee(employee)

    holiday_list_doc = frappe.get_doc("Holiday List", holiday_list)
    all_holidays = list(get_holiday_dates_for_employee(
        employee,
        holiday_list_doc.from_date,
        holiday_list_doc.to_date
    ))

    additional_days = 0
    # Ignore Holidays for First and Last Days
    while next_day_is_holiday_or_weekoff(from_date, holiday_list) and from_date<= to_date:
            from_date = add_days(from_date, 1)
    while next_day_is_holiday_or_weekoff(to_date, holiday_list) and to_date>= from_date:
            to_date = add_days(to_date, -1)
    # Convert half_day_date to date object
    if half_day_date:
        half_day_date = getdate(half_day_date)
    # Process weekoff days
    if leave_type_doc.custom_adjoins_weekoff:
        if leave_type_doc.custom_ignore_if_half_day_leave_for_day_before_or_day_after and cint(half_day):
            if half_day_date:
                if half_day_date != from_date and half_day_date != to_date:
                    if str(half_day_date) not in all_holidays:
                        # Exclude adjacent days if half-day is not on boundary
                        additional_days += len(get_all_weekoff_days(from_date, to_date, holiday_list, half_day_date))
        else:
            # Always include full weekoffs in range
            additional_days += len(get_all_weekoff_days(from_date, to_date, holiday_list))

    
    # Process holiday days
    if leave_type_doc.custom_adjoins_holiday:
        if leave_type_doc.custom_ignore_if_half_day_leave_for_day_before_or_day_after and cint(half_day):
            if half_day_date:
                if half_day_date == from_date or half_day_date == to_date or str(half_day_date) in all_holidays:
                    additional_days += 0
                else:
                    # Get holidays between leave dates, excluding days adjacent to half-day
                    additional_days += len(get_all_holidays(from_date, to_date, holiday_list, half_day_date))
        else:
            # Get all holidays between leave dates which is not weekoff
            additional_days += len(get_all_holidays(from_date, to_date, holiday_list))

    if (leave_type_doc.custom_half_day_leave_taken_in_second_half_on_day_before or leave_type_doc.custom_half_day_leave_taken_in_first_half_on_day_after) and not leave_type_doc.custom_ignore_if_half_day_leave_for_day_before_or_day_after:
        
        # Handle half-day in second half on day before
        if leave_type_doc.custom_half_day_leave_taken_in_second_half_on_day_before and str(half_day_date) not in all_holidays:
            if half_day and half_day_date:
                if custom_half_day_time == "First":
                    next_day = add_days(half_day_date, 1)
                    if leave_type_doc.custom_adjoins_holiday and leave_type_doc.custom_adjoins_weekoff:
                        while next_day_is_holiday_or_weekoff(next_day,holiday_list):
                            additional_days -= 1
                            next_day = add_days(next_day, 1)
                    elif leave_type_doc.custom_adjoins_holiday:
                        while next_day_is_holiday(next_day, holiday_list) and next_day<= to_date:
                            additional_days -= 1
                            next_day = add_days(next_day, 1)
                    elif leave_type_doc.custom_adjoins_weekoff:
                        while next_day_is_weekoff(next_day, holiday_list) and next_day<= to_date:
                            additional_days -= 1
                            next_day = add_days(next_day, 1)

        # Handle half-day in first half on day after
        if leave_type_doc.custom_half_day_leave_taken_in_first_half_on_day_after and str(half_day_date) not in all_holidays:
            if half_day and half_day_date:
                if custom_half_day_time == "Second":
                    prev_day = add_days(half_day_date, -1)
                    if leave_type_doc.custom_adjoins_holiday and leave_type_doc.custom_adjoins_weekoff:
                        while next_day_is_holiday_or_weekoff(prev_day, holiday_list):
                            additional_days -= 1
                            prev_day = add_days(prev_day, -1)
                    elif leave_type_doc.custom_adjoins_holiday:
                        while next_day_is_holiday(prev_day, holiday_list) and prev_day>= from_date:
                            additional_days -= 1
                            prev_day = add_days(prev_day, -1)
                    elif leave_type_doc.custom_adjoins_weekoff:
                        while next_day_is_weekoff(prev_day, holiday_list) and prev_day>= from_date:
                            additional_days -= 1
                            prev_day = add_days(prev_day, -1)
    # Add the additional days to the total
    number_of_days += additional_days

    return number_of_days

def next_day_is_holiday_or_weekoff(date, holiday_list):
    """Check if the given date is a holiday or weekoff"""
    is_holiday = frappe.db.exists("Holiday", {
        "parent": holiday_list,
        "holiday_date": date
    })
    return bool(is_holiday)

def next_day_is_holiday(date, holiday_list):
    """Check if the given date is a holiday"""
    is_holiday = frappe.db.exists("Holiday", {
        "parent": holiday_list,
        "holiday_date": date,
        "weekly_off": 0
    })
    return bool(is_holiday)

def next_day_is_weekoff(date, holiday_list):
    """Check if the given date is a weekoff"""
    is_weekoff = frappe.db.exists("Holiday", {
        "parent": holiday_list,
        "holiday_date": date,
        "weekly_off": 1
    })
    return bool(is_weekoff)

def get_all_weekoff_days(from_date, to_date, holiday_list_name, half_day_date=None):
    """
    Get all weekoff days between from_date and to_date.
    If half_day_date is provided, exclude the day after and before the half day.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    # For proper SQL comparison
    from_date_str = from_date.strftime('%Y-%m-%d')
    to_date_str = to_date.strftime('%Y-%m-%d')
    conditions = """
        holiday_date > %s AND holiday_date < %s
        AND weekly_off = 1 
        AND parent = %s
    """
    
    params = [from_date_str, to_date_str, holiday_list_name]
    
    if half_day_date:
        half_day_date = getdate(half_day_date)
        half_day_date_str = half_day_date.strftime('%Y-%m-%d')
        next_day = add_days(half_day_date, 1)
        prev_day = add_days(half_day_date, -1)
        
        # Skip the day immediately after half day if half day is on Friday
        if half_day_date.weekday() == 4:  # Friday is weekday 4
            conditions += " AND holiday_date != %s"
            params.append(next_day.strftime('%Y-%m-%d'))
        else:
            # Otherwise skip days adjacent to half day
            conditions += " AND holiday_date NOT IN (%s, %s, %s)"
            params.extend([half_day_date_str, prev_day.strftime('%Y-%m-%d'), next_day.strftime('%Y-%m-%d')])
    
    return [
        getdate(d[0]) for d in frappe.db.sql(
            f"""
            SELECT holiday_date 
            FROM `tabHoliday` 
            WHERE {conditions}
            """,
            tuple(params)
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
    from_date_str = from_date.strftime('%Y-%m-%d')
    to_date_str = to_date.strftime('%Y-%m-%d')
    
    conditions = """
        holiday_date > %s AND holiday_date < %s
        AND weekly_off = 0 
        AND parent = %s
    """
    
    params = [from_date_str, to_date_str, holiday_list_name]
    
    if half_day_date:
        half_day_date = getdate(half_day_date)
        half_day_date_str = half_day_date.strftime('%Y-%m-%d')
        next_day = add_days(half_day_date, 1)
        prev_day = add_days(half_day_date, -1)
        
        # Skip the day immediately after half day if half day is on Friday
        if half_day_date.weekday() == 4:  # Friday is weekday 4
            conditions += " AND holiday_date != %s"
            params.append(next_day.strftime('%Y-%m-%d'))
        else:
            # Otherwise skip days adjacent to half day
            conditions += " AND holiday_date NOT IN (%s, %s, %s)"
            params.extend([half_day_date_str, prev_day.strftime('%Y-%m-%d'), next_day.strftime('%Y-%m-%d')])
    
    return [
        getdate(d[0]) for d in frappe.db.sql(
            f"""
            SELECT holiday_date 
            FROM `tabHoliday` 
            WHERE {conditions}
            """,
            tuple(params)
        )
    ]

@frappe.whitelist()
def custom_get_leave_details(employee, date, for_salary_slip=False):
	allocation_records = get_leave_allocation_records(employee, date)
	leave_allocation = {}
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2
	for d in allocation_records:
		allocation = allocation_records.get(d, frappe._dict())

		to_date = date if for_salary_slip else allocation.to_date

		remaining_leaves = get_leave_balance_on(
			employee,
			d,
			date,
			to_date=to_date,
			consider_all_leaves_in_the_allocation_period=False if for_salary_slip else True,
		)

		leave_ledger_entry = frappe.get_all(
			"Leave Ledger Entry",
			filters={
				"employee": employee,
				"leave_type": allocation.leave_type,
				"docstatus": 1,
				"from_date": ["<=", date],
				"leaves": [">", 0],
			},
			fields=["name", "leaves"]
		)

		total_leaves = sum([flt(d.leaves) for d in leave_ledger_entry])
		leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, to_date) * -1
		leaves_pending = get_leaves_pending_approval_for_period(employee, d, allocation.from_date, to_date)
		expired_leaves = total_leaves - (remaining_leaves + leaves_taken)

		leave_allocation[d] = {
			"total_leaves": flt(total_leaves),
			"expired_leaves": flt(expired_leaves, precision) if expired_leaves > 0 else 0,
			"leaves_taken": flt(leaves_taken, precision),
			"leaves_pending_approval": flt(leaves_pending, precision),
			"remaining_leaves": flt(remaining_leaves, precision),
		}

	lwp = frappe.get_list("Leave Type", filters={"is_lwp": 1}, pluck="name")

	return {
		"leave_allocation": leave_allocation,
		"leave_approver": get_leave_approver(employee),
		"lwps": lwp,
	}

def custom_get_allocated_and_expired_leaves(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> tuple[float, float, float]:
	new_allocation = 0
	expired_leaves = 0
	carry_forwarded_leaves = 0
	records = get_leave_ledger_entries(from_date, add_days(to_date,-1), employee, leave_type)

	for record in records:
		# new allocation records with `is_expired=1` are created when leave expires
		# these new records should not be considered, else it leads to negative leave balance
		if record.is_expired:
			continue
		if record.leaves < 0 and record.from_date >= getdate(from_date):
			expired_leaves += abs(record.leaves)
			
		else:
			if record.to_date < getdate(to_date):
				# leave allocations ending before to_date, reduce leaves taken within that period
				# since they are already used, they won't expire
				expired_leaves += record.leaves

				leaves_for_period = get_leaves_for_period(employee, leave_type, record.from_date, record.to_date)
				expired_leaves -= min(abs(leaves_for_period), record.leaves)

			if record.from_date >= getdate(from_date):
				if record.is_carry_forward:
					carry_forwarded_leaves += record.leaves
				else:
					new_allocation += record.leaves

	return new_allocation, expired_leaves, carry_forwarded_leaves

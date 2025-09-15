import frappe
from dateutil import relativedelta
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import get_leave_type_details
from frappe import _
import json
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import (
	get_datetime,
	get_first_day,
	get_last_day,
    flt,
    today,
    add_days,
    formatdate,
    getdate,
    date_diff,
    nowdate,
    cint,
)
from dateutil import relativedelta
from hrms.hr.utils import create_additional_leave_ledger_entry, get_monthly_earned_leave
import datetime
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from hrms.hr.report.employee_leave_balance.employee_leave_balance import get_leave_ledger_entries, get_employees, get_leave_types
from hrms.hr.utils import get_holiday_dates_for_employee
from hrms.hr.doctype.leave_application.leave_application import (
    get_holidays,
    get_leave_allocation_records,
    get_leave_approver,
    get_leaves_for_period,
    get_leaves_pending_approval_for_period,
    get_remaining_leaves,
    get_allocation_expiry_for_cf_leaves
)
from hrms.hr.utils import get_leave_period
from prompt_hr.py.utils import get_reporting_manager_info
from hrms.hr.doctype.leave_allocation.leave_allocation import get_previous_allocation
Filters = frappe._dict


def on_cancel(doc, method):
    if doc.get("workflow_state"):
        doc.db_set("workflow_state", "Cancelled")
    if doc.get("custom_leave_status"):
        doc.db_set("custom_leave_status", "Cancelled")

def before_save(doc, method):
    if hasattr(doc, '_original_date'):  
        doc.set("from_date", doc._original_date)
        if hasattr(doc, '_half_day'):
                doc.set("half_day", 1)
                if hasattr(doc, "_half_day_date"):
                    doc.set("half_day_date", doc._half_day_date) 
    doc.total_leave_days = custom_get_number_of_leave_days(
            doc.employee,
            doc.leave_type,
            doc.from_date,
            doc.to_date,
            doc.half_day,
            doc.half_day_date,
            None,
            doc.custom_half_day_time
    )
    employee_doc = frappe.get_doc("Employee", doc.employee)
    reporting_manager = None
    if employee_doc.reports_to:
        reporting_manager = frappe.get_doc("Employee", employee_doc.reports_to)
    leave_type_doc = frappe.get_doc("Leave Type", doc.leave_type)
    if reporting_manager and reporting_manager.user_id:
        doc.db_set("leave_approver", reporting_manager.user_id)
        doc.db_set("leave_approver_name", reporting_manager.employee_name)
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
    # ? LEAVE DEDUCTED THROUGH SANDWICH LEAVE MUST BE ZERO AT TIME OF INSERT
    doc.custom_leave_deducted_sandwich_rule = 0
    doc.custom_auto_apply_sandwich_rule = 0
    doc.custom_auto_approve = 0

def before_validate(doc, method=None):
    if doc.custom_leave_status == "Approved":
        doc._original_date = doc.get("from_date")
        if doc.half_day:
            doc._half_day = doc.half_day
            if doc.half_day_date:
                doc._half_day_date = doc.half_day_date
        doc.set("from_date", frappe.utils.add_days(doc.custom_original_to_date,1))
        doc.set("half_day", 0)

def validate(doc, method=None):
    if doc.is_new() or (doc.workflow_state == "Pending" and doc.has_value_changed("from_date")):
        # ? ALLOWED DAYS INCLUDE TODAY ALSO (EXAMPLE :- IF TODAY'S IS 18 DATE THEN EMPLOYEE'S APPLY ONLY UPTO 9 DATE (9,10,11,12,13,14,15,16,17,18))
        allowed_days = frappe.db.get_single_value("HR Settings", "custom_maximum_backdated_leave_days_including_today")
        if allowed_days:
            if doc.from_date < add_days(today(), -(allowed_days-1)):
                frappe.throw(_("You cannot apply leave for more than {0} days in the past.").format(allowed_days))

import frappe
from frappe.utils import getdate, add_days


def apply_sandwich_rule(doc):
    """
    Apply sandwich leave rule logic for approved leaves.
    This checks holidays and weekoffs adjoining the leave period
    and extends the leave accordingly.
    """

    #? CHECK ONLY IF LEAVE IS APPROVED
    if doc.workflow_state != "Approved":
        return 0, 0, 0

    #! FETCH RULES FROM LEAVE TYPE
    leave_type = doc.leave_type
    is_sandwich_rule = frappe.db.get_value("Leave Type", leave_type, "custom_is_sandwich_rule_applicable")
    apply_on_holiday = frappe.db.get_value("Leave Type", leave_type, "custom_adjoins_holiday")
    apply_on_weekoff = frappe.db.get_value("Leave Type", leave_type, "custom_adjoins_weekoff")
    ignore_half_day = frappe.db.get_value("Leave Type", leave_type, "custom_ignore_if_half_day_leave_for_day_before_or_day_after")
    allow_half_day_before_second_half = frappe.db.get_value("Leave Type", leave_type, "custom_half_day_leave_taken_in_second_half_on_day_before")
    allow_half_day_after_first_half = frappe.db.get_value("Leave Type", leave_type, "custom_half_day_leave_taken_in_first_half_on_day_after")

    if not is_sandwich_rule:
        return 0, 0, 0

    #! PREPARE DATE VARIABLES
    leave_start = getdate(doc.from_date)
    leave_end = getdate(doc.to_date)
    year_start = leave_start.replace(month=1, day=1)
    year_end = leave_end.replace(month=12, day=31)
    holiday_list = get_holiday_list_for_employee(doc.employee)
    if not holiday_list:
        return 0, 0 ,0
    # ? Sandwich Rule Extension
    leave_type_doc = frappe.get_doc("Leave Type", leave_type)
    sandwich_rule_applicable = 0
    if any([
        leave_type_doc.custom_sw_applicable_to_business_unit,
        leave_type_doc.custom_sw_applicable_to_department,
        leave_type_doc.custom_sw_applicable_to_location,
        leave_type_doc.custom_sw_applicable_to_employment_type,
        leave_type_doc.custom_sw_applicable_to_grade,
        leave_type_doc.custom_sw_applicable_to_product_line
    ]):
        employee_doc = frappe.get_doc("Employee", doc.employee)

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
                sandwich_rule_applicable = 1
                break

    else:
        sandwich_rule_applicable = 1

    if not sandwich_rule_applicable:
        return 0,0,0

    extra_leave_days_prev = 0
    extra_leave_days_next = 0
    extra_leave_days = 0
    final_extra_day_prev = 0
    # -------------------------------------------------------------------
    #? HELPER: CHECK IF DATE IS HOLIDAY/WEEKOFF BASED ON RULES
    def is_non_working_day(date):
        if apply_on_holiday and apply_on_weekoff:
            return next_day_is_holiday_or_weekoff(date, holiday_list)
        if apply_on_holiday:
            return next_day_is_holiday(date, holiday_list)
        if apply_on_weekoff:
            return next_day_is_weekoff(date, holiday_list)
        return False

    # -------------------------------------------------------------------
    #? HELPER: HANDLE HALF DAY RULES
    def should_ignore_half_day(leave_record, is_before):
        if ignore_half_day:
            return True

        if leave_record.get("type") == "Half Day":
            if is_before and leave_record.get("time") == "First" and allow_half_day_before_second_half:
                return True
            if not is_before and leave_record.get("time") == "Second" and allow_half_day_after_first_half:
                return True
        return False

    # -------------------------------------------------------------------
    #? GENERIC LOGIC TO SCAN BEFORE OR AFTER LEAVE
    def scan_adjacent_days(start_date, end_date, step, is_before):
        possible_days = 0
        nonlocal extra_leave_days
        for date in range_loop(start_date, end_date, step):
            if is_non_working_day(date):
                possible_days += 1
            elif possible_days > 0:
                leave_record = get_leave_for_date(doc.employee, date)

                if leave_record:
                    if leave_record.get("type") == "Half Day":
                        if should_ignore_half_day(leave_record, is_before):
                            break
                        else:
                            extra_leave_days += possible_days
                            break
                    else:  # FULL DAY LEAVE
                        extra_leave_days += possible_days
                        break
                else:  # NO LEAVE FOUND
                    possible_days = 0
                    break
            else:
                break

    # -------------------------------------------------------------------
    #? RANGE LOOP HANDLER (FORWARD OR BACKWARD DATE ITERATION)
    def range_loop(start_date, end_date, step):
        current = start_date

        #? MOVE FORWARD (step = +1)
        if step > 0:
            while current <= end_date:
                yield current
                current = add_days(current, step)

        #? MOVE BACKWARD (step = -1)
        elif step < 0:
            while current >= end_date:
                yield current
                current = add_days(current, step)

    # -------------------------------------------------------------------
    #? CHECK BEFORE LEAVE FROM DATE
    extra_leaves = 0
    if not (doc.half_day and doc.half_day_date == doc.from_date and
            ((doc.custom_half_day_time == "Second" and allow_half_day_after_first_half and not is_non_working_day(doc.from_date)) or ignore_half_day)):
        original_leave_start = leave_start
        while leave_start <= leave_end:
            if is_non_working_day(leave_start):
                leave_start = add_days(leave_start, 1)
                extra_leaves += 1
            else:
                if doc.half_day and leave_start == doc.half_day_date and ((doc.custom_half_day_time == "Second" and allow_half_day_after_first_half) or ignore_half_day):
                    extra_leaves = 0
                    leave_start = original_leave_start
                break
        scan_adjacent_days(add_days(leave_start,-1), year_start, -1, is_before=True)
        final_extra_day_prev = extra_leave_days - extra_leaves
        extra_leave_days_prev = extra_leave_days
    #? CHECK AFTER LEAVE FROM DATE
    extra_leaves = 0
    if not (doc.half_day and doc.half_day_date == doc.to_date and
            ((doc.custom_half_day_time == "First" and allow_half_day_before_second_half and not is_non_working_day(doc.to_date)) or ignore_half_day)):
        original_leave_end = leave_end       
        while leave_end >= leave_start:
            if is_non_working_day(leave_end):
                leave_end = add_days(leave_end, -1)
                extra_leaves += 1
            else:
                if doc.half_day and leave_end == doc.half_day_date and ((doc.custom_half_day_time == "First" and allow_half_day_before_second_half) or ignore_half_day):
                    extra_leaves = 0
                    leave_end = original_leave_end
                break
        scan_adjacent_days(add_days(leave_end,1), year_end, 1, is_before=False)
        extra_leave_days_next = extra_leave_days - extra_leave_days_prev - extra_leaves
    return extra_leave_days, final_extra_day_prev, extra_leave_days_next

def before_submit(doc, method):
    extra_leave_days, extra_leave_days_prev, extra_leave_days_next = apply_sandwich_rule(doc)
    if doc.custom_leave_status == "Approved":    
        if hasattr(doc, '_original_date'):
            doc.set("from_date", doc._original_date)
            if hasattr(doc, '_half_day'):
                doc.set("half_day", 1)
                if hasattr(doc, "_half_day_date"):
                    doc.set("half_day_date", doc._half_day_date)
            doc.total_leave_days = custom_get_number_of_leave_days(
                    doc.employee,
                    doc.leave_type,
                    doc.from_date,
                    doc.to_date,
                    doc.half_day,
                    doc.half_day_date,
                    None,
                    doc.custom_half_day_time
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

    if extra_leave_days > 0:
        doc.total_leave_days = (doc.total_leave_days or 0) + extra_leave_days
        doc.custom_leave_deducted_sandwich_rule = extra_leave_days
        doc.custom_auto_apply_sandwich_rule = 1
        if extra_leave_days_prev > 0:
            doc.from_date = add_days(doc.from_date, -extra_leave_days_prev)
        if extra_leave_days_next > 0:
            doc.to_date = add_days(doc.to_date, extra_leave_days_next)
        precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2

        leave_balance = custom_get_leave_balance_on(
                doc.employee,
                doc.leave_type,
                doc.from_date,
                doc.to_date,
                consider_all_leaves_in_the_allocation_period=True,
                for_consumption=True,
            )
        leave_balance_for_consumption = flt(
            leave_balance.get("leave_balance_for_consumption"), precision
        )
        is_lwp = frappe.db.get_value("Leave Type", doc.leave_type,"is_lwp")
        if (not leave_balance_for_consumption or doc.total_leave_days > leave_balance_for_consumption) and not is_lwp:
            frappe.throw(f"Extra {extra_leave_days} Sandwich Leaves will be Added, Hence Total Apply Leave is More Than Leave Balance")
        frappe.msgprint(
            msg=f"{extra_leave_days} additional day(s) have been included as per the Sandwich Rule.",
            title="Leave Adjustment Notice",
            indicator="blue"
        )

def on_submit(doc,method=None):

    # * Get company abbreviation
    company_abbr = frappe.get_value("Company", doc.company, "abbr")

    # * For PROMPT Company Logic
    if company_abbr == frappe.db.get_single_value("HR Settings", "custom_prompt_abbr"):
        leave_type = frappe.get_doc("Leave Type", doc.leave_type)
        if leave_type.custom_is_maternity_leave or leave_type.custom_is_paternity_leave:
            if doc.leave_balance == doc.total_leave_days:
                existing_allocation = frappe.get_all(
                    "Leave Allocation",
                    filters={
                        "employee": doc.employee,
                        "leave_type": doc.leave_type,
                        "docstatus": 1
                    },
                    fields=["name", "to_date"]
                )
                if existing_allocation:
                    if len(existing_allocation) > 1:
                        if int(leave_type.custom_maximum_times_for_applying_leave) > 2:
                            if len(existing_allocation) < int(leave_type.custom_maximum_times_for_applying_leave):
                                if leave_type.custom_leave_allowed_for_third_child:
                                    allocation = frappe.get_doc({
                                        "doctype": "Leave Allocation",
                                        "employee": doc.employee,
                                        "leave_type": doc.leave_type,
                                        "from_date": frappe.utils.add_days(doc.to_date,1),
                                        "to_date": existing_allocation[0].to_date,
                                        "new_leaves_allocated": int(leave_type.custom_leave_allowed_for_third_child),
                                        "company": doc.company,
                                        "docstatus": 1,
                                        "ignore_manual_allocation_check": True
                                    })
                                    prev_allocation = frappe.get_doc("Leave Allocation", existing_allocation[0].name)
                                    prev_allocation.db_set("to_date", doc.to_date)
                                    #! UPDATE RELATED LEAVE LEDGER ENTRIES ALSO  
                                    frappe.db.set_value(
                                        "Leave Ledger Entry",              #? TARGET DOCTYPE  
                                        {"transaction_name": prev_allocation.name, "transaction_type": "Leave Allocation"},  
                                        "to_date", doc.to_date             #! UPDATE END DATE  
                                    )
                                    allocation.insert(ignore_permissions=True)
                                    allocation.submit()
                    else:
                        allocation = frappe.get_doc({
                                    "doctype": "Leave Allocation",
                                    "employee": doc.employee,
                                    "leave_type": doc.leave_type,
                                    "from_date": frappe.utils.add_days(doc.to_date,1),
                                    "to_date": existing_allocation[0].to_date,
                                    "new_leaves_allocated": int(leave_type.custom_leave_allocation_for_each_child),
                                    "company": doc.company,
                                    "docstatus": 1,
                                    "ignore_manual_allocation_check": True
                                    })
                        prev_allocation = frappe.get_doc("Leave Allocation", existing_allocation[0].name)
                        prev_allocation.db_set("to_date", doc.to_date)
                        #! UPDATE RELATED LEAVE LEDGER ENTRIES ALSO  
                        frappe.db.set_value(
                            "Leave Ledger Entry",              #? TARGET DOCTYPE  
                            {"transaction_name": prev_allocation.name, "transaction_type": "Leave Allocation"},  
                            "to_date", doc.to_date             #! UPDATE END DATE  
                        )
                        allocation.insert(ignore_permissions=True)

                        allocation.submit()


def on_update(doc, method):
    employee = frappe.get_doc("Employee", doc.employee)
    employee_id = employee.get("user_id")
    reporting_manager = None
    reporting_manager_name = None
    reporting_manager_id = None
    manager_id = frappe.session.user
    manager_name = None
    if manager_id:
        manager_name = frappe.db.get_value("Employee", {"user_id": manager_id}, "employee_name")
    if employee.reports_to:
        reporting_manager = frappe.get_doc("Employee", employee.reports_to)
        reporting_manager_name = reporting_manager.get("employee_name")
        reporting_manager_id = reporting_manager.get("user_id")
    hr_manager_email = None
    hr_manager_name = None
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
            if "S - HR Director (Global Admin)" in frappe.get_roles(hr_manager_user):
                hr_manager_email = frappe.db.get_value("User", hr_manager_user, "email")
                hr_manager_name = frappe.db.get_value("Employee", {"user_id":hr_manager_user}, "employee_name")

    if not reporting_manager_name:
        reporting_manager_name = hr_manager_name

    if doc.workflow_state == "Pending":
        manager_info = get_reporting_manager_info(doc.employee)
        if manager_info:
            doc.db_set("custom_pending_approval_at", f"{manager_info['name']} - {manager_info['employee_name']}")
        notification = frappe.get_doc("Notification", "Leave Request Notification")
        if notification:
            # Notify the Reporting Manager about the leave request.
            subject = frappe.render_template(notification.subject, {"doc":doc,"request_type":"Leave Application"})
            if reporting_manager_id:
                frappe.sendmail(
                recipients=reporting_manager_id,
                cc = other_recipents,
                message = frappe.render_template(notification.message, {"doc": doc,"manager":reporting_manager_name}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                expose_recipients="header"
            )

    elif doc.workflow_state == "Approved":
        doc.db_set("status", "Approved")
        doc.db_set("custom_pending_approval_at", "")
        is_lwp = is_compensatory = 0
        if doc.leave_type:
            is_lwp = frappe.db.get_value("Leave Type", doc.leave_type, is_lwp)
            is_compensatory = frappe.db.get_value("Leave Type", doc.leave_type, is_compensatory)
        if is_lwp or is_compensatory:
            employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
            if employee_notification:
                # Notify the employee regarding the approval of their leave by Reporting Manager.
                subject = frappe.render_template(employee_notification.subject, {"doc":doc,"manager":manager_name,"request_type":"Leave Application"})
                if employee_id:
                    frappe.sendmail(
                    recipients=employee_id,
                    cc = other_recipents,
                    message = frappe.render_template(employee_notification.message, {"doc": doc, "manager": manager_name}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                    expose_recipients="header"
                )
        else:
            employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
            if employee_notification:
                # Notify the employee regarding the approval of their leave by Reporting Manager.
                subject = frappe.render_template(employee_notification.subject, {"doc":doc,"manager":hr_manager_name,"request_type":"Leave Application"})
                if employee_id:
                    frappe.sendmail(
                    recipients=employee_id,
                    message = frappe.render_template(employee_notification.message, {"doc": doc, "manager": hr_manager_name}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

    elif doc.workflow_state == "Approved by Reporting Manager":
        doc.db_set("custom_pending_approval_at", "HR Team")
        hr_notification = frappe.get_doc("Notification", "Leave Request Status Update to HR Manager")
        if hr_manager_email:
            if hr_notification:
                # Notify the employee regarding the approval of their leave by Reporting Manager.
                subject = frappe.render_template(hr_notification.subject, {"doc":doc,"manager":manager_name,"request_type":"Leave Application", "workflow_state": "Approved"})
                if employee_id:
                    frappe.sendmail(
                    recipients=hr_manager_email,
                    message = frappe.render_template(hr_notification.message, {"doc": doc, "manager": manager_name, "hr_manager": hr_manager_name, "workflow_state": "Approved"}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

    elif doc.workflow_state == "Rejected by Reporting Manager":
        doc.db_set("custom_pending_approval_at", "HR Team")
        hr_notification = frappe.get_doc("Notification", "Leave Request Status Update to HR Manager")
        if hr_manager_email:
            if hr_notification:
                # Notify the employee regarding the approval of their leave by Reporting Manager.
                subject = frappe.render_template(hr_notification.subject, {"doc":doc,"manager":manager_name,"request_type":"Leave Application", "workflow_state": "Approved"})
                if employee_id:
                    frappe.sendmail(
                    recipients=hr_manager_email,
                    message = frappe.render_template(hr_notification.message, {"doc": doc, "manager": manager_name, "hr_manager": hr_manager_name, "workflow_state": "Rejected" }),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )
    elif doc.workflow_state == "Rejected":
        doc.db_set("custom_pending_approval_at", "")
        doc.db_set("status", "Rejected")
        is_lwp = is_compensatory = 0
        if doc.leave_type:
            is_lwp = frappe.db.get_value("Leave Type", doc.leave_type, is_lwp)
            is_compensatory = frappe.db.get_value("Leave Type", doc.leave_type, is_compensatory)
        if is_lwp or is_compensatory:
            employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
            if employee_notification:
                # Notify the employee regarding the rejection of their leave.
                subject = frappe.render_template(employee_notification.subject, {"doc":doc, "manager":manager_name,"request_type":"Leave Application"})
                if employee_id:
                    frappe.sendmail(
                    recipients=employee_id,
                    cc = other_recipents,
                    message = frappe.render_template(employee_notification.message, {"doc": doc, "manager": manager_name}),
                    subject = subject,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                    expose_recipients="header"
                )
        else:
            employee_notification = frappe.get_doc("Notification", "Leave Request Response By Reporting Manager")
            if employee_notification:
                # Notify the employee regarding the rejection of their leave.
                subject = frappe.render_template(employee_notification.subject, {"doc":doc, "manager":hr_manager_name,"request_type":"Leave Application"})
                if employee_id:
                    frappe.sendmail(
                    recipients=employee_id,
                    message = frappe.render_template(employee_notification.message, {"doc": doc, "manager": hr_manager_name}),
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
                message = frappe.render_template(notification.message, {"doc": doc, "manager":reporting_manager_name}),
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
            total_leaves = custom_get_number_of_leave_days(doc.employee, doc.leave_type, doc.from_date, doc.custom_original_to_date, doc.half_day, doc.half_day_date)
            doc.db_set("total_leave_days", total_leaves)

        if employee_notification:
            # Notify the employee regarding the approval/rejection of their leave extension.
            subject = frappe.render_template(employee_notification.subject, {"doc":doc, "manager":reporting_manager_name})
            if employee_id:
                frappe.sendmail(
                recipients=employee_id,
                cc = other_recipents,
                message = frappe.render_template(employee_notification.message, {"doc": doc, "manager":reporting_manager_name}),
                subject = subject,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
                expose_recipients="header"
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
        if leave_application.custom_leave_status == "Approved":
            leave_application.custom_original_to_date = leave_application.to_date
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
                "workflow_state": "Approved",
                "custom_leave_status": "Approved",
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
    new_leaves_added = flt(earned_leaves)
    new_allocation_without_cf = flt(
        flt(allocation.get_existing_leave_count()) + flt(earned_leaves),
        allocation.precision("total_leaves_allocated"),
    )

    # ! REMOVE RESTRICTIONS OF MAX LEAVE ALLOWED
    # if new_allocation > e_leave_type.max_leaves_allowed and e_leave_type.max_leaves_allowed > 0:
    #     new_leaves_added -= (new_allocation - e_leave_type.max_leaves_allowed)
    #     new_allocation = e_leave_type.max_leaves_allowed
    #     if new_leaves_added < 0:
    #         new_leaves_added = 0

    if new_allocation != allocation.total_leaves_allocated: # and new_allocation_without_cf <= annual_allocation:
        today_date = frappe.flags.current_date or getdate()
        is_maternity_leave = 0
        leave_applications = frappe.get_all("Leave Application", filters={"employee":allocation.employee,"company":allocation.company,"docstatus":1},fields=["name", "leave_type", "from_date", "to_date"])
        for leave_application in leave_applications:
            leave_type  = frappe.get_doc("Leave Type", leave_application.leave_type)
            if leave_type.custom_is_maternity_leave:
                if (today_date >= leave_application.from_date) and (today_date <= leave_application.to_date):
                    is_maternity_leave = 1
                    break

        if not is_maternity_leave:
            allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
            allocation.db_set("new_leaves_allocated", new_leaves_added)
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
    if (half_day or half_day_date) and not custom_half_day_time:
        leave_app = frappe.get_all(
            "Leave Application",
            filters={
                "employee": employee,
                "from_date": from_date,
                "to_date": to_date,
                "half_day": 1,
                "docstatus": ["!=", 2]
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
                    leave_app = frappe.get_all(
                        "Leave Application",
                        filters={
                            "employee": employee,
                            "from_date": from_date,
                            "half_day": 1,
                            "docstatus": ["!=", "2"],
                        },
                        fields=["name", "custom_half_day_time", "half_day", "half_day_date"],
                        limit=1,
                    )
                    if leave_app:
                        half_day = leave_app[0].half_day
                        half_day_date = leave_app[0].half_day_date
                        custom_half_day_time = leave_app[0].custom_half_day_time
    else:
        if half_day is None:
            doc_json = frappe.form_dict.get("doc")
            if doc_json:
                doc = json.loads(doc_json)
                custom_half_day_time = doc.get("custom_half_day_time")
                half_day_date = doc.get("half_day_date")
                half_day = doc.get("half_day")
            else:
                leave_app = frappe.get_all(
                    "Leave Application",
                    filters={
                        "employee": employee,
                        "from_date": from_date,
                        "half_day": 1,
                        "docstatus": ["!=", "2"],
                    },
                    fields=["name", "custom_half_day_time", "half_day", "half_day_date"],
                    limit=1,
                )
                if leave_app:
                    half_day = leave_app[0].half_day
                    half_day_date = leave_app[0].half_day_date
                    custom_half_day_time = leave_app[0].custom_half_day_time

    if not holiday_list:
        holiday_list = get_holiday_list_for_employee(employee)

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
            if number_of_days < 0:
                number_of_days = 0
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

    if leave_type_doc.include_holiday:
        return number_of_days

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
    if additional_days > 0:
        number_of_days += additional_days
    if number_of_days < 0:
        number_of_days = 0

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
	#! FETCH ALL ALLOCATION RECORDS FOR THE EMPLOYEE ON THE GIVEN DATE
	allocation_records = get_leave_allocation_records(employee, date)
	leave_allocation = {}

	#! GET SYSTEM FLOAT PRECISION SETTING (DEFAULT TO 2 IF NOT SET)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2

	#! GET CURRENT LEAVE PERIOD BASED ON FILTER RANGE
	company = frappe.db.get_value("Employee", employee, "company")
	leave_periods = get_leave_period(date, date, company)

	#! SAFELY EXTRACT LEAVE PERIOD IF IT EXISTS
	if leave_periods:
		leave_period = leave_periods[0]
		leaves_start_date = leave_period.get("from_date")
		leaves_end_date = leave_period.get("to_date")
	else:
		#! CONSIDER 1ST JANUARY AS LEAVES START DATE IF NOT PRESENT
		from_date = date
		if from_date:
			year = getdate(from_date).year
			leaves_start_date = getdate(f"{year}-01-01")
			leaves_end_date = getdate(f"{year}-12-31")

		else:
			leaves_start_date = getdate(f"{today().year}-01-01")
			leaves_end_date = getdate(f"{today().year}-12-31")

	#! LOOP THROUGH EACH ALLOCATION TYPE
	for d in allocation_records:
		allocation = allocation_records.get(d, frappe._dict())

		#! DETERMINE TO_DATE BASED ON CONTEXT (SALARY SLIP OR NORMAL)
		to_date = date if for_salary_slip else allocation.to_date

		#! CALCULATE REMAINING LEAVES AS OF THE GIVEN DATE
		remaining_leaves = custom_get_leave_balance_on(
			employee,
			d,
			date,
			to_date=to_date,
			consider_all_leaves_in_the_allocation_period=not for_salary_slip,
		)
		#! FETCH LEAVE TYPE DETAILS IF DEFINED
		if allocation.get("leave_type"):
			is_maternity = frappe.db.get_value("Leave Type", allocation.get("leave_type"), "custom_is_maternity_leave")
			is_paternity = frappe.db.get_value("Leave Type", allocation.get("leave_type"), "custom_is_paternity_leave")
			if is_maternity or is_paternity:
				leaves_start_date = min(leaves_start_date, allocation.get("from_date")) if getdate(date) < getdate(allocation.get("from_date")) else allocation.get("from_date")
				leaves_end_date = max(leaves_end_date, allocation.get("to_date"))

		#! FETCH ALL POSITIVE LEAVE ALLOCATIONS FROM LEDGER
		leave_ledger_entry = frappe.get_all(
			"Leave Ledger Entry",
			filters=[
				["employee", "=", employee],
				["leave_type", "=", allocation.leave_type],
				["docstatus", "=", 1],
				["from_date", ">=", leaves_start_date],
				["from_date", "<=", date],
				["transaction_type", "=", "Leave Allocation"],
				["leaves", ">", 0],
			],
			fields=["name", "leaves", "from_date", "to_date"],
			order_by="from_date asc"
		)

		#! GET SUM OF ALL PENALIZED LEAVES
		penalized_leaves = get_total_penalized_leaves_for_period(employee, allocation.leave_type, leaves_start_date, date)

		#! SUM OF ALL ALLOCATED LEAVES FROM LEDGER
		total_leaves = sum([flt(d.leaves) for d in leave_ledger_entry])

		#! CALCULATE LEAVES TAKEN AND PENDING APPROVAL
		leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, to_date) * -1
		extra_sandwich_leaves_taken = get_extra_sandwich_days(employee, d, allocation.from_date, to_date)
		if extra_sandwich_leaves_taken:
			leaves_taken += extra_sandwich_leaves_taken

		leaves_pending = get_leaves_pending_approval_for_period(employee, d, allocation.from_date, to_date)

		#! FETCH LEAVE TYPE DETAILS IF DEFINED
		if allocation.get("leave_type"):
			is_compensatory = frappe.db.get_value("Leave Type", allocation.get("leave_type"), "is_compensatory")
			if is_compensatory:
				#? FETCH ALL COMP OFF ALLOCATIONS
				comp_off_allocations = leave_ledger_entry

				#! FETCH ALL NEGATIVE LEAVE ALLOCATIONS FROM LEDGER
				negative_leave_allocation = frappe.get_all(
					"Leave Ledger Entry",
					filters=[
						["employee", "=", employee],
						["leave_type", "=", allocation.leave_type],
						["docstatus", "=", 1],
						["from_date", ">=", leaves_start_date],
						["from_date", "<=", date],
						["transaction_type", "=", "Leave Allocation"],
						["leaves", "<", 0],
					],
					fields=["name", "leaves", "from_date", "to_date"],
					order_by="from_date asc"
				)

				#? FETCH ALL LEAVE APPLICATIONS (LEAVES TAKEN)
				leaves_taken_ledger_entries = frappe.get_all(
					"Leave Ledger Entry",
					filters=[
						["employee", "=", employee],
						["leave_type", "=", allocation.leave_type],
						["docstatus", "=", 1],
						["leaves", "<", 0],
						["from_date", ">=", leaves_start_date],
						["to_date", "<=", leaves_end_date],
						["transaction_type", "=", "Leave Application"]
					],
					order_by="from_date asc",
					fields=["name", "leaves", "from_date", "to_date"]
				)

				#? BUILD A COPY OF ALLOCATIONS TO TRACK CONSUMPTION
				allocation_pool = []
				for alloc in comp_off_allocations:
					allocation_pool.append({
						"name": alloc.name,
						"from_date": getdate(alloc.from_date),
						"to_date": getdate(alloc.to_date),
						"available": flt(alloc.leaves),
                        "used": 0
					})

				#? ITERATE THROUGH EACH LEAVE TAKEN, AND REDUCE FROM APPROPRIATE ALLOCATION
				for leave in leaves_taken_ledger_entries:
					leave_from = getdate(leave.from_date)
					leave_to = getdate(leave.to_date)

					leave_days = abs(flt(leave.leaves))

					# ? FOR OVERLAPPING LEAVE LEDGER ENTRIES FOR LEAVE APPLICATION
					for alloc in allocation_pool:
						if alloc["available"] <= 0:
							continue

						if (
                                alloc["from_date"] <= leave_from <= alloc["to_date"]
                                or alloc["from_date"] <= leave_to <= alloc["to_date"]
                            ):
							consume = min(leave_days, alloc["available"])
							alloc["available"] -= consume
							alloc["used"] += consume
							leave_days -= consume

						if leave_days <= 0:
							break

				#? ITERATE THROUGH EACH NEGATIVE LEAVE ALLOCATION, AND REDUCE IT FROM APPROPRIATE ALLOCATION
				for leave in negative_leave_allocation:
					leave_from = getdate(leave.from_date)
					leave_to = getdate(leave.to_date)

					leave_days = abs(flt(leave.leaves))

					# ? FOR OVERLAPPING LEAVE LEDGER ENTRIES FOR LEAVE APPLICATION
					for alloc in allocation_pool:
						if alloc["available"] <= 0:
							continue

						if (
                                alloc["from_date"] <= leave_from <= alloc["to_date"]
                                or alloc["from_date"] <= leave_to <= alloc["to_date"]
                            ):
							consume = min(leave_days, alloc["available"])
							alloc["available"] -= consume
							leave_days -= consume

						if leave_days <= 0:
							break

				#? CALCULATE REMAINING LEAVES
				comp_leave_not_used = sum([
					alloc["available"]
					for alloc in allocation_pool
					if alloc["to_date"] >= getdate(date)
				])
				remaining_leaves = comp_leave_not_used                    
				leaves_taken = sum([
					alloc["used"]
					for alloc in allocation_pool
					if alloc["from_date"] <= getdate(date)
				])

		#! DERIVE EXPIRED LEAVES = TOTAL - (REMAINING + TAKEN)
		expired_leaves = total_leaves - (remaining_leaves + leaves_taken) - penalized_leaves

		#! STORE LEAVE DETAILS PER ALLOCATION TYPE
		leave_allocation[d] = {
			"total_leaves": flt(total_leaves),
			"expired_leaves": flt(expired_leaves, precision) if expired_leaves > 0 else 0,
			"leaves_taken": flt(leaves_taken, precision),
			"penalized_leaves": flt(penalized_leaves, precision),
			"leaves_pending_approval": flt(leaves_pending, precision),
			"remaining_leaves": flt(remaining_leaves, precision),
		}

	#! GET ALL LWP (LEAVE WITHOUT PAY) TYPES
	lwp = frappe.get_list("Leave Type", filters={"is_lwp": 1}, pluck="name")

	#! RETURN LEAVE SUMMARY AND APPROVER INFO
	return {
		"leave_allocation": leave_allocation,
		"leave_approver": get_leave_approver(employee),
		"lwps": lwp,
	}

def custom_get_allocated_and_expired_leaves(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> tuple[float, float, float]:
	#! INITIALIZE RETURN VARIABLES
	new_allocation = 0
	expired_leaves = 0
	carry_forwarded_leaves = 0

	#! FETCH ALL LEAVE LEDGER ENTRIES FOR THE GIVEN PERIOD
	records = get_leave_ledger_entries(from_date, add_days(to_date, -1), employee, leave_type)

	#! CHECK IF LEAVE TYPE IS COMPENSATORY
	is_compensatory_leave = frappe.db.get_value("Leave Type", leave_type, "is_compensatory")
    #! GET CURRENT LEAVE PERIOD BASED ON FILTER RANGE
	company = frappe.db.get_value("Employee", employee, "company")
	leave_periods = get_leave_period(from_date, to_date, company)

	#! SAFELY EXTRACT LEAVE PERIOD IF IT EXISTS
	if leave_periods:
		leave_period = leave_periods[0]
		leaves_start_date = leave_period.get("from_date")
	else:
		#! CONSIDER 1ST JANUARY AS LEAVES START DATE IF NOT PRESENT
		from_date = from_date
		if from_date:
			year = getdate(from_date).year
			leaves_start_date = getdate(f"{year}-01-01")
		else:
			leaves_start_date = getdate(f"{today().year}-01-01")
	if is_compensatory_leave:
		#! INITIALIZE COMPENSATORY VARIABLES
		new_allocation = 0
		expired_leaves = 0

		#! FETCH ALL POSITIVE LEAVE ALLOCATIONS FROM LEDGER
		comp_off_allocations = frappe.get_all(
			"Leave Ledger Entry",
			filters=[
				["employee", "=", employee],
				["leave_type", "=", leave_type],
				["docstatus", "=", 1],
				["from_date", ">=", leaves_start_date],
				["from_date", "<=", to_date],
				["transaction_type", "=", "Leave Allocation"],
				["leaves", ">", 0],
			],
			fields=["name", "leaves", "from_date", "to_date"],
			order_by="from_date asc"
		)

		#! FETCH ALL NEGATIVE LEAVE ALLOCATIONS FROM LEDGER
		negative_leave_allocations = frappe.get_all(
			"Leave Ledger Entry",
			filters=[
				["employee", "=", employee],
				["leave_type", "=", leave_type],
				["docstatus", "=", 1],
				["from_date", ">=", leaves_start_date],
				["from_date", "<=", to_date],
				["transaction_type", "=", "Leave Allocation"],
				["leaves", "<", 0],
			],
			fields=["name", "leaves", "from_date", "to_date"],
			order_by="from_date asc"
		)

		#! FETCH ALL LEAVE APPLICATIONS (LEAVES TAKEN)
		leaves_taken_ledger_entries = frappe.get_all(
			"Leave Ledger Entry",
			filters=[
				["employee", "=", employee],
				["leave_type", "=", leave_type],
				["docstatus", "=", 1],
				["leaves", "<", 0],
				["from_date", ">=", leaves_start_date],
				["to_date", "<", to_date],
				["transaction_type", "=", "Leave Application"]
			],
			order_by="from_date asc",
			fields=["name", "leaves", "from_date", "to_date"]
		)

		#! BUILD A COPY OF ALLOCATIONS TO TRACK CONSUMPTION
		allocation_pool = []
		for alloc in comp_off_allocations:
			allocation_pool.append({
				"name": alloc.name,
				"from_date": getdate(alloc.from_date),
				"to_date": getdate(alloc.to_date),
				"available": flt(alloc.leaves),
			})
		expire_through_negative_allocations = 0

		#! ITERATE THROUGH EACH LEAVE TAKEN, AND REDUCE FROM APPROPRIATE ALLOCATION
		for leave in leaves_taken_ledger_entries:
			leave_from = getdate(leave.from_date)
			leave_to = getdate(leave.to_date)
			leave_days = abs(flt(leave.leaves))

			#! FOR OVERLAPPING LEAVE LEDGER ENTRIES FOR LEAVE APPLICATION
			for alloc in allocation_pool:
				if alloc["available"] <= 0:
					continue

				if (
					alloc["from_date"] <= leave_from <= alloc["to_date"]
					or alloc["from_date"] <= leave_to <= alloc["to_date"]
				):
					consume = min(leave_days, alloc["available"])
					alloc["available"] -= consume
					leave_days -= consume

				if leave_days <= 0:
					break

		#! ITERATE THROUGH EACH LEAVE TAKEN, AND REDUCE FROM APPROPRIATE ALLOCATION
		for leave in negative_leave_allocations:
			leave_from = getdate(leave.from_date)
			leave_to = getdate(leave.to_date)
			leave_days = abs(flt(leave.leaves))

			#! FOR OVERLAPPING LEAVE LEDGER ENTRIES FOR LEAVE APPLICATION
			for alloc in allocation_pool:
				if alloc["available"] <= 0:
					continue

				if (
					alloc["from_date"] <= leave_from <= alloc["to_date"]
					or alloc["from_date"] <= leave_to <= alloc["to_date"]
				):
					consume = min(leave_days, alloc["available"])

					alloc["available"] -= consume
					leave_days -= consume
					if getdate(from_date) < getdate(leave_from) < getdate(to_date):
						expire_through_negative_allocations += consume

				if leave_days <= 0:
					break

		#! CALCULATE REMAINING LEAVES
		comp_leave_unused = sum([
			alloc["available"]
			for alloc in allocation_pool
			if getdate(from_date) <= alloc["to_date"] < getdate(to_date)
		])
		expired_leaves = comp_leave_unused + expire_through_negative_allocations

		date_from = getdate(from_date)
		for record in records:
			if record.leaves > 0:
				if record.from_date >= date_from:
					new_allocation += record.leaves

		#! FINAL RETURN FOR COMPENSATORY LEAVE: CARRY FORWARD IS ALWAYS ZERO
		return new_allocation, expired_leaves, 0

	#! IF NOT COMPENSATORY LEAVE TYPE, FOLLOW REGULAR LOGIC
	for record in records:
		#! SKIP SYSTEM-GENERATED EXPIRATION ENTRIES
		if record.is_expired:
			continue

		if record.leaves < 0 and record.from_date >= getdate(from_date):
			#! NEGATIVE LEDGER ENTRY (EXPIRY OR REVERSAL)
			expired_leaves += abs(record.leaves)

		else:
			if record.to_date < getdate(to_date):
				#! ADD ALLOCATION TO EXPIRED IF IT ENDS BEFORE TO_DATE
				expired_leaves += record.leaves

				#! ADJUST BASED ON ACTUAL USAGE
				leaves_for_period = get_leaves_for_period(
					employee, leave_type, record.from_date, record.to_date
				)
				extra_sandwich_leaves = get_extra_sandwich_days(
					employee, leave_type, record.from_date, record.to_date
				)
				if extra_sandwich_leaves:
					leaves_for_period -= extra_sandwich_leaves
				expired_leaves -= min(abs(leaves_for_period), record.leaves)

			#! HANDLE ALLOCATIONS OR CARRY FORWARDS FROM FROM_DATE ONWARD
			if record.from_date >= getdate(from_date):
				if record.is_carry_forward:
					carry_forwarded_leaves += record.leaves
				else:
					new_allocation += record.leaves

	#! RETURN FINAL CALCULATED VALUES
	return new_allocation, expired_leaves, carry_forwarded_leaves


@frappe.whitelist()
def leave_extension_allowed(leave_type, employee):
    """
    Checks whether the current user is allowed to extend the leave for a given Leave Type and Employee.

    Conditions:
    - The Leave Type must have `custom_allow_leave_extension` set to True.
    - The current user must either be:
        - The employee (matched via user_id), OR
        - An Administrator.
    
    Returns:
        True if extension is allowed, otherwise False.
    """

    if not leave_type:
        return False
    if not employee:
        return False
    
    # Fetch the Leave Type document

    leave_type_doc = frappe.get_doc("Leave Type", leave_type)

    # Check if leave extension is allowed in the Leave Type
    if leave_type_doc.custom_allow_leave_extension:
        
        # Get the user ID linked to the given Employee
        employee_user_id = frappe.db.get_value("Employee", employee, "user_id")
        
        # Allow if the current session user is either:
        # - The employee themselves
        # - OR an Administrator
        if employee_user_id == frappe.session.user or frappe.session.user == "Administrator":
            return True

        # Otherwise, not allowed
        return False

    # If leave extension is not enabled for this Leave Type, return False
    return False


# ? MODIFIED GET HOLIDAYS FUNCTION TO EXCLUDE OPTIONAL FESTIVAL LEAVE
@frappe.whitelist()
def get_holidays(employee, from_date, to_date, holiday_list=None):
    """
    Returns the count of non-optional holidays between two dates for a given employee.
    Optional holidays (custom_is_optional_festival_leave = 1) are excluded.
    """
    # * Step 1: Fetch holiday list if not provided
    if not holiday_list:
        holiday_list = get_holiday_list_for_employee(employee)

    # * Step 2: Execute SQL query to count holidays (excluding optional festival leaves)
    holiday_count = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT h1.holiday_date)
        FROM `tabHoliday` h1
        INNER JOIN `tabHoliday List` h2 ON h1.parent = h2.name
        WHERE h1.holiday_date BETWEEN %s AND %s
        AND h2.name = %s
        AND IFNULL(h1.custom_is_optional_festival_leave, 0) = 0
        """,
        (from_date, to_date, holiday_list),
    )[0][0]

    return holiday_count

def custom_get_opening_balance(
    employee: str, leave_type: str, filters: Filters, carry_forwarded_leaves: float
) -> float:
    #? HANDLE SPECIAL CASE FOR COMPENSATORY LEAVE TYPES
    if leave_type:
        is_compensatory = frappe.db.get_value("Leave Type", leave_type, "is_compensatory")

        if is_compensatory:
            #! FETCH EMPLOYEE'S COMPANY
            company = frappe.db.get_value("Employee", employee, "company")
            leave_periods = get_leave_period(filters.from_date, filters.to_date, company)

            #! SAFELY EXTRACT LEAVE PERIOD IF IT EXISTS
            if leave_periods:
                leave_period = leave_periods[0]
                leaves_start_date = leave_period.get("from_date")

            else:            
                #! CONSIDER 1ST JANUARY AS LEAVES START DATE IF NOT PRESENT
                from_date = filters.get("from_date")
                if from_date:
                    year = getdate(from_date).year
                    leaves_start_date = getdate(f"{year}-01-01")
                else:
                    leaves_start_date = getdate(f"{today().year}-01-01")

            LeaveLedgerEntry = DocType("Leave Ledger Entry")

            from_date = filters.get("from_date")
            if not from_date:
                return 0

            # ? COMMON BASE FILTER FOR GRANTED LEAVES (POSITIVE)
            base_granted_filter = (
                (LeaveLedgerEntry.employee == employee)
                & (LeaveLedgerEntry.leave_type == leave_type)
                & (LeaveLedgerEntry.docstatus == 1)
                & (LeaveLedgerEntry.leaves > 0)
                & (LeaveLedgerEntry.from_date >= leaves_start_date)
            )

            #! FETCH ALL POSITIVE LEAVE ALLOCATIONS FROM LEDGER
            leave_ledger_entry = frappe.get_all(
                "Leave Ledger Entry",
                filters=[
                    ["employee", "=", employee],
                    ["leave_type", "=", leave_type],
                    ["docstatus", "=", 1],
                    ["from_date", ">=", leaves_start_date],
                    ["from_date", "<", from_date],
                    ["transaction_type", "=", "Leave Allocation"],
                    ["leaves", ">", 0],
                ],
                fields=["name", "leaves", "from_date", "to_date"],
                order_by="from_date asc"
            )

            #! FETCH ALL NEGATIVE LEAVE ALLOCATIONS FROM LEDGER
            negative_leave_allocation = frappe.get_all(
                "Leave Ledger Entry",
                filters=[
                    ["employee", "=", employee],
                    ["leave_type", "=", leave_type],
                    ["docstatus", "=", 1],
                    ["from_date", ">=", leaves_start_date],
                    ["from_date", "<=", from_date],
                    ["transaction_type", "=", "Leave Allocation"],
                    ["leaves", "<", 0],
                ],
                fields=["name", "leaves", "from_date", "to_date"],
                order_by="from_date asc"
            )

            total_comp_leaves = sum([flt(d.leaves) for d in leave_ledger_entry])
            #? FETCH ALL LEAVE APPLICATIONS (LEAVES TAKEN)
            leaves_taken_ledger_entries = frappe.get_all(
                "Leave Ledger Entry",
                filters=[
                    ["employee", "=", employee],
                    ["leave_type", "=", leave_type],
                    ["docstatus", "=", 1],
                    ["leaves", "<", 0],
                    ["from_date", ">=", leaves_start_date],
                    ["from_date", "<", from_date],
                    ["transaction_type", "=", "Leave Application"]
                ],
                order_by="from_date asc",
                fields=["name", "leaves", "from_date", "to_date"]
            )

            #? BUILD A COPY OF ALLOCATIONS TO TRACK CONSUMPTION
            allocation_pool = []
            for alloc in leave_ledger_entry:
                allocation_pool.append({
                    "name": alloc.name,
                    "from_date": getdate(alloc.from_date),
                    "to_date": getdate(alloc.to_date),
                    "available": flt(alloc.leaves),
                    "used": 0
                })

            #? ITERATE THROUGH EACH LEAVE TAKEN, AND REDUCE FROM APPROPRIATE ALLOCATION
            for leave in leaves_taken_ledger_entries+negative_leave_allocation:
                leave_from = getdate(leave.from_date)
                leave_to = getdate(leave.to_date)

                leave_days = abs(flt(leave.leaves))

                # ? FOR OVERLAPPING LEAVE LEDGER ENTRIES FOR LEAVE APPLICATION
                for alloc in allocation_pool:
                    if alloc["available"] <= 0:
                        continue
                    
                    if (
                            alloc["from_date"] <= leave_from <= alloc["to_date"]
                            or alloc["from_date"] <= leave_to <= alloc["to_date"]
                        ):
                        consume = min(leave_days, alloc["available"])
                        if leave_days > 1:
                            if  leave_from <= getdate(filters.from_date) <= leave_to:
                                #? IF LEAVE TO DATE IS AFTER FILTER TO_DATE, CONSUME ONLY TILL FILTER TO_DATE
                                consume = min(consume, (getdate(filters.to_date) - leave_from).days + 1)
                                alloc["available"] -= consume
                                alloc["used"] += consume
                                leave_days -= consume
                                break

                        alloc["available"] -= consume
                        alloc["used"] += consume
                        leave_days -= consume

                    if leave_days <= 0:
                        break

            # ? CALCULATE LEAVES TAKEN AFTER FILTER FROM_DATE
            leaves_taken = sum([
                alloc["used"]
                for alloc in allocation_pool
                if alloc["to_date"] >= getdate(from_date)
            ])

            expired_leaves = (
                frappe.qb.from_(LeaveLedgerEntry)
                .select(Sum(LeaveLedgerEntry.leaves).as_("total"))
                .where(
                    base_granted_filter &
                    (LeaveLedgerEntry.to_date < from_date)
                )
            ).run(as_dict=True)[0]["total"] or 0
            # ? CALCULATE TOTAL OPENING LEAVES FOR COMPENSATORY TYPE
            total_opening_leaves = total_comp_leaves - (leaves_taken + expired_leaves)

            return total_opening_leaves

    
    #! CALCULATE OPENING BALANCE BASED ON DATE BEFORE FILTER RANGE
    opening_balance_date = add_days(filters.from_date, -1)
    
    #! FETCH PREVIOUS LEAVE ALLOCATION
    allocation = get_previous_allocation(filters.from_date, leave_type, employee)

    #? CHECK IF PREVIOUS ALLOCATION ENDS ON OPENING BALANCE DATE
    if (
        allocation
        and allocation.get("to_date")
        and opening_balance_date
        and getdate(allocation.get("to_date")) == getdate(opening_balance_date)
    ):
        #? IF TRUE: OPENING BALANCE = ONLY CARRY FORWARDED LEAVES
        opening_balance = carry_forwarded_leaves
    else:
        #? OTHERWISE: GET ACTUAL BALANCE ON PREVIOUS DAY
        opening_balance = custom_get_leave_balance_on(employee, leave_type, opening_balance_date)

    #! RETURN DEFAULT OPENING BALANCE FOR NON-COMPENSATORY TYPES
    return opening_balance


def custom_get_data(filters: Filters) -> list:
    leave_types = get_leave_types()
    active_employees = get_employees(filters)

    precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
    consolidate_leave_types = len(active_employees) > 1 and filters.consolidate_leave_types
    row = None

    data = []

    for leave_type in leave_types:
        if consolidate_leave_types:
            data.append({"leave_type": leave_type})
        else:
            row = frappe._dict({"leave_type": leave_type})

        for employee in active_employees:
            if consolidate_leave_types:
                row = frappe._dict()
            else:
                row = frappe._dict({"leave_type": leave_type})

            row.employee = employee.name
            row.employee_name = employee.employee_name

            leaves_taken = (
                get_leaves_for_period(employee.name, leave_type, filters.from_date, filters.to_date) * -1
            )
            extra_sandwich_leaves = get_extra_sandwich_days(
					employee.name, leave_type, filters.from_date, filters.to_date
				)
            if extra_sandwich_leaves:
                leaves_taken += extra_sandwich_leaves

            new_allocation, expired_leaves, carry_forwarded_leaves = custom_get_allocated_and_expired_leaves(
                filters.from_date, filters.to_date, employee.name, leave_type
            )
            opening = custom_get_opening_balance(employee.name, leave_type, filters, carry_forwarded_leaves)
            penalized_leaves = get_total_penalized_leaves_for_period(employee.name, leave_type, filters.from_date, filters.to_date) or 0
            row.penalized_leaves = flt(penalized_leaves, precision)
            row.leaves_allocated = flt(new_allocation, precision)
            row.leaves_expired = flt(expired_leaves - penalized_leaves, precision)
            row.opening_balance = flt(opening, precision)
            row.leaves_taken = flt(leaves_taken, precision)

            is_lwp = frappe.db.get_value("Leave Type", leave_type, "is_lwp")
            if is_lwp:
                row.closing_balance = 0
            else:
                closing = new_allocation + opening - (row.leaves_expired + leaves_taken + row.penalized_leaves)
                row.closing_balance = flt(closing, precision)

            row.indent = 1
            data.append(row)

    return data

def get_leave_for_date(employee, date):
    """
    #! CHECK IF LEAVE APPLICATION EXISTS FOR GIVEN EMPLOYEE AND DATE
    #? RETURNS ('Half Day' | 'Full Day' | None)
    """
    leave = frappe.db.get_value(
        "Leave Application",
        {
            "employee": employee,
            "from_date": ("<=", date),
            "to_date": (">=", date),
            "docstatus": 1  # ONLY SUBMITTED LEAVES
        },
        ["half_day", "half_day_date", "custom_half_day_time"],
        as_dict=True
    )

    if leave:
        if leave.half_day and getdate(leave.half_day_date) == date:
            return {"type":"Half Day", "time":leave.custom_half_day_time}
        return {"type":"Full Day", "time":leave.custom_half_day_time}

    return None

def get_extra_sandwich_days(employee, leave_type, from_date, to_date):
    """
    Returns the total number of sandwich-deducted days
    for an employee in the given period.
    """

    result = frappe.db.sql(
        """
        SELECT SUM(custom_leave_deducted_sandwich_rule) as total_sandwich_days
        FROM `tabLeave Application`
        WHERE employee = %(employee)s
          AND leave_type = %(leave_type)s
          AND docstatus = 1
          AND custom_leave_deducted_sandwich_rule > 0
          AND (from_date between %(from_date)s AND %(to_date)s
				OR to_date between %(from_date)s AND %(to_date)s
				OR (from_date < %(from_date)s AND to_date > %(to_date)s))
        """,
        {"employee": employee, "leave_type": leave_type, "from_date": from_date, "to_date": to_date},
        as_dict=1,
    )

    return result[0].total_sandwich_days or 0

@frappe.whitelist()
def custom_get_leave_balance_on(
	employee: str,
	leave_type: str,
	date: datetime.date,
	to_date: datetime.date | None = None,
	consider_all_leaves_in_the_allocation_period: bool = False,
	for_consumption: bool = False,
):
	"""
	Returns leave balance till date
	:param employee: employee name
	:param leave_type: leave type
	:param date: date to check balance on
	:param to_date: future date to check for allocation expiry
	:param consider_all_leaves_in_the_allocation_period: consider all leaves taken till the allocation end date
	:param for_consumption: flag to check if leave balance is required for consumption or display
	        eg: employee has leave balance = 10 but allocation is expiring in 1 day so employee can only consume 1 leave
	        in this case leave_balance = 10 but leave_balance_for_consumption = 1
	        if True, returns a dict eg: {'leave_balance': 10, 'leave_balance_for_consumption': 1}
	        else, returns leave_balance (in this case 10)
	"""

	if not to_date:
		to_date = nowdate()

	allocation_records = get_leave_allocation_records(employee, date, leave_type)
	allocation = allocation_records.get(leave_type, frappe._dict())

	end_date = allocation.to_date if cint(consider_all_leaves_in_the_allocation_period) else date
	cf_expiry = get_allocation_expiry_for_cf_leaves(employee, leave_type, to_date, allocation.from_date)

	#! GET LEAVES TAKEN
	leaves_taken = get_leaves_for_period(employee, leave_type, allocation.from_date, end_date)

	#! ADD EXTRA SANDWICH LEAVES
	extra_sandwich_leaves_taken = get_extra_sandwich_days(employee, leave_type, allocation.from_date, end_date)

	if extra_sandwich_leaves_taken:
		leaves_taken -= extra_sandwich_leaves_taken

	#! CALCULATE REMAINING LEAVES
	remaining_leaves = get_remaining_leaves(allocation, leaves_taken, date, cf_expiry)

	if for_consumption:
		return remaining_leaves
	else:
		return remaining_leaves.get("leave_balance")


def custom_get_columns():
    return [
		{
			"label": _("Leave Type"),
			"fieldtype": "Link",
			"fieldname": "leave_type",
			"width": 200,
			"options": "Leave Type",
		},
		{
			"label": _("Employee"),
			"fieldtype": "Link",
			"fieldname": "employee",
			"width": 100,
			"options": "Employee",
		},
		{
			"label": _("Employee Name"),
			"fieldtype": "Dynamic Link",
			"fieldname": "employee_name",
			"width": 200,
			"options": "employee",
		},
		{
			"label": _("Opening Balance"),
			"fieldtype": "float",
			"fieldname": "opening_balance",
			"width": 150,
		},
		{
			"label": _("New Leave(s) Allocated"),
			"fieldtype": "float",
			"fieldname": "leaves_allocated",
			"width": 200,
		},
		{
			"label": _("Leave(s) Taken"),
			"fieldtype": "float",
			"fieldname": "leaves_taken",
			"width": 150,
		},
        {
			"label": _("Penalized Leave(s)"),
			"fieldtype": "float",
			"fieldname": "penalized_leaves",
			"width": 150,
		},
		{
			"label": _("Leave(s) Expired"),
			"fieldtype": "float",
			"fieldname": "leaves_expired",
			"width": 150,
		},
		{
			"label": _("Closing Balance"),
			"fieldtype": "float",
			"fieldname": "closing_balance",
			"width": 150,
		},
	]


def get_total_penalized_leaves_for_period(employee, leave_type, from_date, to_date):
    if not leave_type or not employee or not from_date or not to_date:
        return 0

    #! FETCH ALL NEGATIVE LEAVE ALLOCATIONS (PENALIZED) FROM LEDGER
    penalized_leave_ledger_entry = frappe.get_all(
        "Leave Ledger Entry",
        filters=[
            ["employee", "=", employee],
            ["leave_type", "=", leave_type],
            ["docstatus", "=", 1],
            ["from_date", ">=", from_date],
            ["from_date", "<=", to_date],
            ["transaction_type", "=", "Leave Allocation"],
            ["leaves", "<", 0],
        ],
        fields=["name", "leaves", "from_date", "to_date"],
        order_by="from_date asc"
    )

    #! SUM OF ALL PENALIZED LEAVES (ABSOLUTE VALUE)
    penalized_leaves = abs(sum([flt(d.leaves) for d in penalized_leave_ledger_entry]))

    return penalized_leaves

# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import getdate, today, formatdate, add_days, get_year_start, get_year_ending
from frappe.model.document import Document
from prompt_hr.py.utils import (
    send_notification_email,
    is_user_reporting_manager_or_hr,
    get_reporting_manager_info,
)
from erpnext.setup.doctype.employee.employee import is_holiday
from hrms.hr.utils import get_leave_period
from prompt_hr.overrides.attendance_override import modify_employee_penalty
from prompt_hr.prompt_hr.doctype.employee_penalty.employee_penalty import (
    cancel_penalties,
)
from prompt_hr.py.auto_mark_attendance import mark_attendance


class WeekOffChangeRequest(Document):

    def before_save(self):

        # ? CHECK IF ANY LEAVE APPLICATION EXISTS FOR THE DATES ENTERED IN WEEKOFF CHANGE REQUEST
        check_if_leave_application_exists(self)

    def on_update(self):
        if self.workflow_state == "Pending":
            manager_info = get_reporting_manager_info(self.employee)
            if manager_info:
                self.db_set(
                    "pending_approval_at",
                    f"{manager_info['name']} - {manager_info['employee_name']}",
                )
        else:
            self.db_set("pending_approval_at", "")

        current_user = frappe.session.user
        if self.status == "Approved":
            is_rh = is_user_reporting_manager_or_hr(current_user, self.employee)
            #! PROCESS WEEKOFF CHANGES FOR EMPLOYEE
            if not is_rh.get("error"):
                today = getdate()

                def process_weekoff_attendance(date, is_existing):
                    att_list = frappe.get_all(
                        "Attendance",
                        filters={
                            "employee": self.employee,
                            "docstatus": ["!=", 2],
                            "attendance_date": date,
                        },
                        fields=[
                            "name",
                            "attendance_date",
                            "custom_employee_penalty_id",
                        ],
                        limit=1,
                    )

                    if att_list:
                        attendance = att_list[0]

                        # Cancel penalties if any
                        if attendance.custom_employee_penalty_id:
                            cancel_penalties(
                                attendance.custom_employee_penalty_id,
                                "Weekoff change request Approve",
                                1,
                            )

                        # Cancel old attendance
                        frappe.get_doc("Attendance", attendance.name).cancel()
                    # Mark attendance
                    mark_attendance(
                        attendance_date=date,
                        company=self.company,
                        regularize_attendance=0,
                        emp_id=self.employee,
                    )

                    # Update employee penalty
                    modify_employee_penalty(self.employee, date, is_existing)

                for weekoff_detail in self.weekoff_details:
                    existing_date = getdate(weekoff_detail.existing_weekoff_date)
                    if existing_date < today:
                        process_weekoff_attendance(
                            weekoff_detail.existing_weekoff_date, True
                        )

                    new_date = getdate(weekoff_detail.new_weekoff_date)
                    if new_date < today:
                        process_weekoff_attendance(
                            weekoff_detail.new_weekoff_date, False
                        )

    def before_insert(self):

        # * CHECKING IF THE DAY IS ENTERED OR NOT AND IF ENTERED THEN THE DAY IS CORRECT OR NOT ACCORDING TO DATE
        if self.weekoff_details:
            for row in self.weekoff_details:
                if row.existing_weekoff_date:
                    day_name = get_day_name(row.existing_weekoff_date)
                    if not row.existing_weekoff:
                        row.existing_weekoff = day_name
                    elif (
                        row.existing_weekoff
                        and row.existing_weekoff.lower() != day_name.lower()
                    ):
                        throw("Please Set Correct Existing weekoff Day as per the date")

                if row.new_weekoff_date:
                    day_name = get_day_name(row.new_weekoff_date)
                    if not row.new_weekoff:
                        row.new_weekoff = day_name
                    elif (
                        row.new_weekoff and row.new_weekoff.lower() != day_name.lower()
                    ):
                        throw("Please Set Correct New weekoff Day as per the date")

    def validate(self):
        sent_auto_approve_emails = frappe.db.get_single_value("HR Settings", "custom_send_auto_approve_doc_emails") or 0
        # *CHECKING IF THE EXISTING DETAILS IS VALID OR NOT, IF INVALID SHOWING AN ALERT TELLING USER THAT THE EXISTING DATE ENTERED DOES NOT EXISTS IN HOLIDAY LIST
        if self.weekoff_details:
            for row in self.weekoff_details:
                exists = check_existing_date(self.employee, row.existing_weekoff_date)
                if not exists.get("error"):
                    if not exists.get("exists"):
                        throw(
                            f"Date {row.existing_weekoff_date} does not exist in holiday list"
                        )
                    else:
                        if row.existing_weekoff_date:
                            day_name = get_day_name(row.existing_weekoff_date)
                            if not row.existing_weekoff:
                                row.existing_weekoff = day_name
                            elif (
                                row.existing_weekoff
                                and row.existing_weekoff.lower() != day_name.lower()
                            ):
                                throw(
                                    f"The date {formatdate(row.existing_weekoff_date, 'dd-mm-yyyy')} does not exist in the holiday list for this employee."
                                )

                        if row.new_weekoff_date:
                            day_name = get_day_name(row.new_weekoff_date)
                            if not row.new_weekoff:
                                row.new_weekoff = day_name
                            elif (
                                row.new_weekoff
                                and row.new_weekoff.lower() != day_name.lower()
                            ):
                                throw(
                                    "Please Set Correct New weekoff Day as per the date"
                                )
                elif exists.get("error"):
                    throw(
                        f"Error While Verifying Existing Date {exists.get('message')}"
                    )

        # *CHECKING IF THE CURRENT USER IS THE EMPLOYEE USER LINKED TO DOCUMENT THEN WHEN WE SAVES THIS DOCUMENT THEN SENDING AN EMAIL TO THE EMPLOYEE'S REPORTING HEAD ABOUT THE CREATION WEEKOFF CHANGE REQUEST
        current_user = frappe.session.user
        if self.status == "Approved" and (not self.auto_approve or sent_auto_approve_emails):
            is_rh = is_user_reporting_manager_or_hr(current_user, self.employee)
            if not is_rh.get("error") and is_rh.get("is_rh"):
                emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
                if emp_user_id:
                    # if "@" in emp_user_id:
                    # 	emp_mail = emp_user_id
                    # else:
                    # emp_mail = frappe.db.get_value("User", emp_user_id, 'email')
                    send_notification_email(
                        recipients=[emp_user_id],
                        notification_name="WeekOff Change Request Approved",
                        doctype="WeekOff Change Request",
                        docname=self.name,
                        send_link=True,
                        fallback_subject="WeekOff Change Request Approved",
                        fallback_message=f"<p>Dear Employee</p>   <p>Your WeekOff Change Request has been reviewed and approved.<br>Best regards,<br>HR Department</p>",
                    )
            elif is_rh.get("error"):
                throw(f"{is_rh.get('message')}")
        if self.status == "Rejected" and (not self.auto_approve or sent_auto_approve_emails):
            is_rh = is_user_reporting_manager_or_hr(current_user, self.employee)
            if not is_rh.get("error") and is_rh.get("is_rh"):
                emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
                if emp_user_id:
                    send_notification_email(
                        recipients=[emp_user_id],
                        notification_name="WeekOff Change Request Rejected",
                        doctype="WeekOff Change Request",
                        docname=self.name,
                        send_link=True,
                        fallback_subject="WeekOff Change Request Rejected",
                        fallback_message=f"<p>Dear Employee</p>\n\n    <p>We regret to inform you that your WeekOff Change Request has been rejected.</p>",
                    )
            elif is_rh.get("error"):
                throw(f"{is_rh.get('message')}")

        if self.workflow_state == "Approved":

            # ? CREATE AND LINK NEW HOLIDAY LIST IF NOT EXISTS
            holiday_list = frappe.db.get_value(
                "Employee", self.employee, "holiday_list"
            )
            if not holiday_list:
                frappe.throw(
                    _("Please set Holiday List for Employee {0}").format(self.employee)
                )

            weekoff_details = self.weekoff_details

            # ? CREATE NEW HOLIDAY LIST IF NOT EXISTS
            new_list = create_new_holiday_list_for_employee(self.employee, holiday_list, weekoff_details)
            if new_list:
                frappe.db.set_value("Employee", self.employee, "holiday_list", new_list)

        validate_for_sandwich_policy(self)

    def after_insert(self):

        current_user = frappe.session.user
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")

        # * NOTIFY REPORTING MANAGER IF THE CURRENT USER IS THE EMPLOYEE WHOSE WEEKOFF CHANGE REQUEST IS RAISED FOR
        notify_reporting_manager(self.employee, self.name, emp_user, current_user)

    def before_validate(self):
        if not self.is_new():
            if self.workflow_state == "Rejected":
                self.status = "Rejected"
            elif self.workflow_state == "Approved":
                self.status = "Approved"


def notify_reporting_manager(employee_id, docname, emp_user, current_user):
    """Method to check if the current user is the employee whose weekoff change request is, if it is the same user then, sending an email to  employee's reporting manager"""
    rh_emp = frappe.db.get_value("Employee", employee_id, "reports_to")
    if rh_emp:
        rh_user = frappe.db.get_value("Employee", rh_emp, "user_id")
        if rh_user:
            if current_user == emp_user:
                send_notification_email(
                    recipients=[rh_user],
                    notification_name="Request to RH to Approve WeekOff Change",
                    doctype="WeekOff Change Request",
                    docname=docname,
                    send_link=True,
                    fallback_subject=" Request for Approval – WeekOff Change Request",
                    fallback_message=f"Dear Reporting Head,\n\n     I am writing to formally request your approval for my WeekOff Change Request.\n Kindly review and approve the request at your earliest convenience.",
                )
        else:
            throw(f"No user found for reporting head {rh_emp}")
    else:
        throw(f"NO Reporting Head Found for Employee {employee_id}")


@frappe.whitelist()
def check_existing_date(employee_id, existing_date):
    """Method to check of the existing date entered exists in holiday list's holiday child table or not"""
    try:
        holiday_list_id = (
            frappe.db.get_value("Employee", employee_id, "holiday_list") or None
        )

        if holiday_list_id:
            is_existing = frappe.db.get_all(
                "Holiday",
                {
                    "parenttype": "Holiday List",
                    "parent": holiday_list_id,
                    "holiday_date": existing_date,
                },
                "name",
                limit=1,
            )

            if is_existing:
                return {"error": 0, "exists": 1}
            else:
                return {"error": 0, "exists": 0}
        else:
            return {"error": 1, "message": f"No Holiday List found for {employee_id}"}
    except Exception as e:
        frappe.log_error("Error While Verifying Existing Date", frappe.get_traceback())
        return {"error": 1, "message": f"{str(e)}"}


def get_day_name(date_value):
    try:
        date_value = getdate(date_value)
        day_name = date_value.strftime("%A")
        return day_name
    except Exception as e:
        throw("Error while Getting Date Day name")


# ? FUNCTION TO CHECK IF ANY LEAVE APPLICATION EXISTS FOR THE DATES ENTERED IN WEEKOFF CHANGE REQUEST
def check_if_leave_application_exists(doc):
    weekoff_details = doc.weekoff_details

    # ? ALLOW REJECTION WITHOUT BLOCKING
    if doc.workflow_state == "Rejected":
        print("Rejected State - No Check Needed")
        return

    if weekoff_details:
        for row in weekoff_details:
            if row.existing_weekoff_date:
                leave_app = frappe.db.get_all(
                    "Leave Application",
                    {
                        "employee": doc.employee,
                        "from_date": row.existing_weekoff_date,
                        "to_date": row.existing_weekoff_date,
                        "docstatus": ["!=", 2],
                    },
                    ["name"],
                    limit=1,
                )
                if leave_app:
                    link = f"/app/leave-application/{leave_app[0].name}"
                    frappe.throw(
                        msg=f"""Leave Application <a href="{link}" style="font-weight: bold;">
                                {leave_app[0].name}</a> exists for Existing WeekOff Date {formatdate(row.existing_weekoff_date, 'dd-mm-yyyy')}""",
                        title="Leave Application Exists",
                    )

            if row.new_weekoff_date:
                leave_app = frappe.db.get_all(
                    "Leave Application",
                    {
                        "employee": doc.employee,
                        "from_date": row.new_weekoff_date,
                        "to_date": row.new_weekoff_date,
                        "status": ["!=", "Cancelled"],
                    },
                    ["name"],
                    limit=1,
                )
                if leave_app:
                    link = f"/app/leave-application/{leave_app[0].name}"
                    frappe.throw(
                        msg=f"""Leave Application <a href="{link}" style="font-weight: bold;">
                                {leave_app[0].name}</a> exists for New WeekOff Date {formatdate(row.new_weekoff_date, 'dd-mm-yyyy')}""",
                        title="Leave Application Exists",
                    )


# ? FUNCTION TO CREATE A NEW HOLIDAY LIST FOR AN EMPLOYEE WITH UPDATED WEEK-OFF DATES
def create_new_holiday_list_for_employee(employee, base_holiday_list, weekoff_details):
    """
    CREATE A NEW HOLIDAY LIST FOR THE GIVEN EMPLOYEE.
    - COPIES HOLIDAYS FROM THE BASE HOLIDAY LIST.
    - REPLACES/ADDS NEW WEEK-OFF DATES FROM weekoff_details.
    - CREATES NEW LIST ONLY IF ALL NEW WEEK-OFF DATES ARE NOT ALREADY IN BASE LIST.
    """

    if not weekoff_details:
        return

    #! FETCH BASE HOLIDAY LIST DOC
    base_holiday_list_doc = frappe.get_doc("Holiday List", base_holiday_list)

    #! COLLECT ALL HOLIDAY DATES IN BASE LIST
    base_holiday_dates = {row.holiday_date for row in base_holiday_list_doc.holidays}

    #! COLLECT ALL NEW WEEK-OFF DATES
    new_weekoff_dates = {row.get("new_weekoff_date") for row in weekoff_details if row.get("new_weekoff_date")}

    #! CHECK: IF ANY NEW DATE ALREADY EXISTS IN BASE HOLIDAY LIST, THEN DO NOT CREATE NEW LIST
    if any(new_date in base_holiday_dates for new_date in new_weekoff_dates):
        frappe.logger().info(f"Skipping holiday list creation for {employee}: some new dates already in base list")
        return None

    #! CREATE NEW HOLIDAY LIST DOC FOR EMPLOYEE
    new_holiday_list_doc = frappe.new_doc("Holiday List")
    new_holiday_list_doc.holiday_list_name = f"{employee} - {frappe.utils.nowdate()}"
    new_holiday_list_doc.is_default = 0
    new_holiday_list_doc.from_date  = get_year_start(getdate(), as_str=False)
    new_holiday_list_doc.to_date = get_year_ending(getdate())

    #! COLLECT OLD WEEK-OFF DATES FROM weekoff_details
    old_weekoff_dates = [row.get("existing_weekoff_date") for row in weekoff_details if row.get("existing_weekoff_date")]

    #! COPY EXISTING HOLIDAYS, BUT SKIP ONLY OLD WEEK-OFF DATES
    for row in base_holiday_list_doc.holidays:
        if row.holiday_date not in old_weekoff_dates:
            new_holiday_list_doc.append(
                "holidays",
                {
                    "holiday_date": row.holiday_date,
                    "description": row.description or "Holiday",
                },
            )

    #! ADD NEW WEEK-OFF HOLIDAYS
    for row in weekoff_details:
        old_date = row.get("existing_weekoff_date")
        new_date = row.get("new_weekoff_date")
        if old_date and new_date:
            new_holiday_list_doc.append(
                "holidays",
                {
                    "holiday_date": new_date,
                    "description": f"WeekOff Changed from {frappe.utils.formatdate(old_date, 'dd-mm-yyyy')} "
                                    f"to {frappe.utils.formatdate(new_date, 'dd-mm-yyyy')}",
                },
            )

    #! SAVE NEW HOLIDAY LIST
    new_holiday_list_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return new_holiday_list_doc.name


def validate_for_sandwich_policy(doc):
    """
    VALIDATES WHETHER A WEEKOFF CHANGE REQUEST VIOLATES THE SANDWICH LEAVE POLICY.

    IF AN APPROVED LEAVE IS FOUND EITHER BEFORE OR AFTER THE REQUESTED WEEKOFF DATE,
    IT WILL RAISE AN ERROR TO PREVENT WEEKOFF CHANGE.
    """

    #! EXIT EARLY IF NO WEEKOFF DETAILS
    if not doc.weekoff_details:
        return

    for weekoff_detail in doc.weekoff_details:
        #! FLAGS TO TRACK SANDWICH LEAVE DETECTION
        leave_before_weekoff = 0
        leave_after_weekoff = 0

        if weekoff_detail.existing_weekoff_date and weekoff_detail.new_weekoff_date:
            #! GET LEAVE PERIOD RANGE FOR THE COMPANY
            leave_period = get_leave_period(
                weekoff_detail.new_weekoff_date,
                weekoff_detail.new_weekoff_date,
                doc.company
            )

            if leave_period:
                leave_period = leave_period[0]

            year = getdate(weekoff_detail.new_weekoff_date).year
            leave_period_start = leave_period.get("from_date") if leave_period else getdate(f"{year}-01-01")
            leave_period_end = leave_period.get("to_date") if leave_period else getdate(f"{year}-12-31")

            #! FETCH APPROVED LEAVE APPLICATIONS FOR THIS EMPLOYEE WITHIN THE PERIOD
            leave_applications = frappe.get_all(
                "Leave Application",
                filters={
                    "employee": doc.employee,
                    "from_date": ["<=", leave_period_end],
                    "to_date": [">=", leave_period_start],
                    "workflow_state": "Approved",
                    "docstatus": 1
                },
                fields=["name", "from_date", "to_date", "leave_type"]
            )

            #! HELPER FUNCTION TO CHECK IF A DATE FALLS IN AN APPROVED LEAVE
            def get_leave_application_on_date(date):
                """
                RETURNS THE LEAVE APPLICATION NAME IF THE GIVEN DATE IS WITHIN AN APPROVED LEAVE.
                OTHERWISE RETURNS None.
                """
                for app in leave_applications:
                    if getdate(app.from_date) <= date <= getdate(app.to_date):
                        return {"name":app.name, "leave_type":app.leave_type}
                return {}

            # --------------------------------------------------------------------
            #! CHECK FORWARD DIRECTION (AFTER NEW WEEKOFF DATE)
            # --------------------------------------------------------------------
            check_date = getdate(weekoff_detail.new_weekoff_date)

            while add_days(check_date, 1) <= leave_period_end:
                check_date = add_days(check_date, 1)
                leave_app = get_leave_application_on_date(check_date)

                #? IF DATE IS HOLIDAY → CONTINUE LOOP
                if is_holiday(doc.employee, check_date, False):
                    continue

                #? IF DATE IS IN LEAVE → MARK SANDWICH
                elif leave_app:
                    if sandwich_rule_applicable_to_employee(doc.employee, leave_app["leave_type"]):
                        leave_after_weekoff = 1
                    break

                #? OTHERWISE → BREAK LOOP
                else:
                    break

            # --------------------------------------------------------------------
            #! CHECK BACKWARD DIRECTION (BEFORE NEW WEEKOFF DATE)
            # --------------------------------------------------------------------
            check_date = getdate(weekoff_detail.new_weekoff_date)

            while add_days(check_date, -1) >= leave_period_start:
                check_date = add_days(check_date, -1)
                leave_app = get_leave_application_on_date(check_date)

                #? IF DATE IS HOLIDAY → CONTINUE LOOP
                if is_holiday(doc.employee, check_date, False):
                    continue

                #? IF DATE IS IN LEAVE → MARK SANDWICH
                elif leave_app:
                    if sandwich_rule_applicable_to_employee(doc.employee, leave_app["leave_type"]):
                        leave_before_weekoff = 1
                    break

                #? OTHERWISE → BREAK LOOP
                else:
                    break

        # ------------------------------------------------------------------------
        #! FINAL VALIDATION → IF LEAVE FOUND EITHER SIDE, BLOCK WEEKOFF CHANGE
        # ------------------------------------------------------------------------
        if leave_before_weekoff or leave_after_weekoff:
            frappe.throw("Weekoff change denied due to Sandwich Leave Policy.")


def sandwich_rule_applicable_to_employee(employee, leave_type):
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
        employee_doc = frappe.get_doc("Employee", employee)

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
        return False
    
    return True

import frappe
from frappe import throw
from frappe.utils import getdate, nowdate
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_format
from prompt_hr.api.main import notify_signatory_on_email
import traceback
from prompt_hr.py.utils import send_notification_email, get_hr_managers_by_company
import calendar
from datetime import timedelta, datetime, date
from dateutil import relativedelta
from frappe import _
import re
from prompt_hr.py.utils import get_prompt_company_name, get_indifoss_company_name


# ? FUNCTION TO CREATE WELCOME PAGE RECORD FOR GIVEN USER
def create_welcome_status(user_id, company):
    try:
        # ? CHECK IF WELCOME PAGE ALREADY EXISTS
        if frappe.db.exists("Welcome Page", {"user": user_id}):
            return

        if company == get_prompt_company_name().get("company_name"):
            permission = frappe.db.get_value(
                "HR Settings", None, "custom_enable_welcome_page_for_prompt"
            )
            if permission != 1:
                return
        elif company == get_indifoss_company_name().get("company_name"):
            permission = frappe.db.get_value(
                "HR Settings", None, "custom_enable_welcome_page_for_indifoss"
            )
            if permission != 1:
                return

        # ? CREATE NEW WELCOME PAGE DOCUMENT
        welcome_status = frappe.new_doc("Welcome Page")
        welcome_status.user = user_id
        welcome_status.is_completed = 0
        welcome_status.insert(ignore_permissions=True)

        # ? SHARE DOCUMENT WITH THE USER
        frappe.share.add(
            doctype="Welcome Page",
            name=welcome_status.name,
            user=user_id,
            read=1,
            write=1,
            share=0,
        )

        frappe.db.commit()

        frappe.log_error(
            title="Welcome Page Creation",
            message=f"Welcome Page created and shared with user {user_id}.",
        )

    except Exception as e:
        frappe.log_error(
            title="Welcome Page Creation Error",
            message=f"Error creating Welcome Page for user {user_id}: {str(e)}\n{traceback.format_exc()}",
        )


# ? EMPLOYEE BEFORE INSERT HOOK
def before_insert(doc, method):
    custom_autoname_employee(doc)
    # ? SET IMPREST ALLOCATION AMOUNT FROM EMPLOYEE ONBOARDING FORM
    set_imprest_allocation_amount(doc)


# ? FUNCTION TO SET IMPREST ALLOCATION AMOUNT FROM EMPLOYEE ONBOARDING FORM
def set_imprest_allocation_amount(doc):
    try:

        # ? STEP 1: TRY TO FETCH BASED ON EMPLOYEE LINK
        amount = frappe.db.get_value(
            "Employee Onboarding", {"employee": doc.name}, "custom_imprest_amount"
        )

        # ? STEP 2: IF NO MATCH FOUND, TRY USING PHONE NUMBERS
        if not amount:
            phone_number = doc.get("cell_number") or doc.get("custom_work_mobile_no")

            if phone_number:
                amount = frappe.db.get_value(
                    "Employee Onboarding",
                    {"custom_phone_number": phone_number},
                    "custom_imprest_amount",
                )

        # ? STEP 3: SET IF AMOUNT FOUND
        if amount:
            doc.custom_imprest_allocation_amount = amount

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "Error in set_imprest_allocation_amount"
        )
        frappe.throw(
            _(
                "An error occurred while setting the imprest allocation amount. Please contact the system administrator."
            )
        )


# ? CALLED ON EMPLOYEE UPDATE
def on_update(doc, method):

    handle_sales_person_operations_on_update(doc, method)

    # ? CREATE WELCOME PAGE IF NOT EXISTS
    if doc.user_id:
        if not frappe.db.exists("Welcome Page", {"user": doc.user_id}):
            create_welcome_status(doc.user_id, doc.company)

    # ? ASSIGN LEAVE POLICY TO EMPLOYEE ON CHANGE OF LEAVE POLICY ON EMPLOYEE
    if doc.custom_leave_policy and doc.has_value_changed("custom_leave_policy"):

        # ? IF POLICY ASSIGNMENT IS BASED ON JOINING DATE
        if doc.custom_leave_policy_assignment_based_on_joining:
            # ? CREATE ASSIGNMENT BASED ON JOINING DATE (NO LEAVE PERIOD REQUIRED)
            create_leave_policy_assignment(doc, 1)

        else:
            # ? FIND CURRENT ACTIVE LEAVE PERIOD (CONTAINING TODAY)
            active_leave_period = frappe.get_all(
                "Leave Period",
                filters={
                    "from_date": ["<=", getdate()],
                    "to_date": [">=", getdate()],
                    "is_active": 1
                },
                fields=["name", "to_date"],
                order_by="to_date desc",  # ? PRIORITIZE THE MOST RECENT END DATE
                limit=1
            )

            # ? ASSIGN POLICY IF ACTIVE LEAVE PERIOD IS FOUND
            if active_leave_period:
                create_leave_policy_assignment(doc, 0, active_leave_period[0].get("name"))
            else:
                # ! THROW ERROR IF NO VALID ACTIVE LEAVE PERIOD EXISTS
                frappe.throw(_("Cannot assign leave policy as there is no active Leave Period for the current date."))


def validate(doc, method):

    # ? * CHECKING IF HOLIDAY LIST EXISTS IF NOT THEN CREATING A NEW HOLIDAY LIST BASED ON THE WEEKLYOFF TYPE AND FESTIVAL HOLIDAY LIST
    if doc.custom_weeklyoff and doc.custom_festival_holiday_list:
        holiday_list = frappe.db.exists(
            "Holiday List",
            {
                "custom_weeklyoff_type": doc.custom_weeklyoff,
                "custom_festival_holiday_list": doc.custom_festival_holiday_list,
            },
            "name",
        )

        if holiday_list:
            if doc.holiday_list != holiday_list:
                doc.holiday_list = holiday_list
        else:
            holiday_list = create_holiday_list(doc)

            if holiday_list:
                doc.holiday_list = holiday_list


# def create_holiday_list(doc):
#     """Creating Holiday list by Fetching Dates from the festival holiday list and calculating date based on days mentioned in weeklyoff type between from date to date in festival holiday list"""
#     try:

#         final_date_list = []

#         # ? * FETCHING FESTIVAL HOLIDAYS DATES
#         festival_holiday_list_doc = frappe.get_doc(
#             "Festival Holiday List", doc.custom_festival_holiday_list
#         )

#         if not festival_holiday_list_doc:
#             throw("No Festival Holiday List Found")

#         final_date_list = [
#             {
#                 "date": getdate(row.holiday_date),
#                 "description": row.description,
#                 "weekly_off": row.weekly_off,
#                 "custom_is_optional_festival_leave": row.custom_is_optional_festival_leave,
#             }
#             for row in festival_holiday_list_doc.get("holidays")
#         ]

#         # ?* CALCULATING WEEKLYOFF DATES
#         start_date = getdate(festival_holiday_list_doc.from_date)
#         end_date = getdate(festival_holiday_list_doc.to_date)

#         weeklyoff_days = frappe.get_all(
#             "WeekOff Multiselect",
#             {"parenttype": "WeeklyOff Type", "parent": doc.custom_weeklyoff},
#             "weekoff",
#             order_by="weekoff asc",
#             pluck="weekoff",
#         )

#         if not weeklyoff_days:
#             throw(f"No WeeklyOff days found for WeeklyOff Type {doc.custom_weeklyoff}")

#         for weeklyoff_day in weeklyoff_days:
#             weekday = getattr(calendar, (weeklyoff_day).upper())
#             reference_date = start_date + relativedelta.relativedelta(weekday=weekday)

#             while reference_date <= end_date:
#                 if not any(
#                     holiday_date.get("date") == reference_date
#                     for holiday_date in final_date_list
#                 ):
#                     final_date_list.append(
#                         {
#                             "date": reference_date,
#                             "description": weeklyoff_day,
#                             "weekly_off": 1,
#                         }
#                     )
#                 reference_date += timedelta(days=7)

#         if final_date_list:
#             holiday_list_doc = frappe.new_doc("Holiday List")
#             holiday_list_doc.holiday_list_name = (
#                 f"{festival_holiday_list_doc.name}-{doc.custom_weeklyoff}"
#             )
#             holiday_list_doc.from_date = festival_holiday_list_doc.from_date
#             holiday_list_doc.to_date = festival_holiday_list_doc.to_date
#             holiday_list_doc.custom_weeklyoff_type = doc.custom_weeklyoff
#             holiday_list_doc.custom_festival_holiday_list = (
#                 doc.custom_festival_holiday_list
#             )

#             for holiday in final_date_list:
#                 holiday_list_doc.append(
#                     "holidays",
#                     {
#                         "description": holiday.get("description"),
#                         "holiday_date": holiday.get("date"),
#                         "weekly_off": holiday.get("weekly_off"),
#                         "custom_is_optional_festival_leave": holiday.get(
#                             "custom_is_optional_festival_leave"
#                         ),
#                     },
#                 )

#             holiday_list_doc.save(ignore_permissions=True)
#             return holiday_list_doc.name
#         else:
#             return None

#     except Exception as e:
#         frappe.log_error("Error while creating holiday list", frappe.get_traceback())
#         throw(
#             f"Error while creating Holiday List {str(e)}\n for more info please check error log"
#         )

def create_holiday_list(doc):
    """Creating Holiday list by fetching dates from festival holiday list and calculating date based on weeklyoff days (simple weekdays or Nth weekday of month) within the given date range"""
    try:
        final_date_list = []

        festival_holiday_list_doc = frappe.get_doc(
            "Festival Holiday List", doc.custom_festival_holiday_list
        )
        if not festival_holiday_list_doc:
            throw("No Festival Holiday List Found")

        final_date_list = [
            {
                "date": getdate(row.holiday_date),
                "description": row.description,
                "weekly_off": row.weekly_off,
                "custom_is_optional_festival_leave": row.custom_is_optional_festival_leave,
            }
            for row in festival_holiday_list_doc.get("holidays")
        ]

        start_date = getdate(festival_holiday_list_doc.from_date)
        end_date = getdate(festival_holiday_list_doc.to_date)

        weeklyoff_days = frappe.get_all(
            "WeekOff Multiselect",
            {"parenttype": "WeeklyOff Type", "parent": doc.custom_weeklyoff},
            "weekoff",
            order_by="weekoff asc",
            pluck="weekoff",
        )

        if not weeklyoff_days:
            throw(f"No WeeklyOff days found for WeeklyOff Type {doc.custom_weeklyoff}")

        for weeklyoff_day in weeklyoff_days:
            parts = weeklyoff_day.split()
            if len(parts) == 1:
                weekday = getattr(calendar, parts[0].upper())
                reference_date = start_date + relativedelta.relativedelta(weekday=weekday)

                while reference_date <= end_date:
                    if not any(hd.get("date") == reference_date for hd in final_date_list):
                        final_date_list.append({
                            "date": reference_date,
                            "description": weeklyoff_day,
                            "weekly_off": 1,
                        })
                    reference_date += timedelta(days=7)

            else:
                nth = int(parts[0])
                day_name = parts[1]                                
                weekday = getattr(calendar, day_name.upper())

                current = start_date.replace(day=1)
                while current <= end_date:
                    nth_weekday_date = get_nth_weekday_of_month(current.year, current.month, weekday, nth)
                    if nth_weekday_date and start_date <= nth_weekday_date <= end_date:
                        if not any(hd.get("date") == nth_weekday_date for hd in final_date_list):
                            final_date_list.append({
                                "date": nth_weekday_date,
                                "description": weeklyoff_day,
                                "weekly_off": 1,
                            })
                    current += relativedelta.relativedelta(months=1)

        if final_date_list:
            holiday_list_doc = frappe.new_doc("Holiday List")
            holiday_list_doc.holiday_list_name = f"{festival_holiday_list_doc.name}-{doc.custom_weeklyoff}"
            holiday_list_doc.from_date = festival_holiday_list_doc.from_date
            holiday_list_doc.to_date = festival_holiday_list_doc.to_date
            holiday_list_doc.custom_weeklyoff_type = doc.custom_weeklyoff
            holiday_list_doc.custom_festival_holiday_list = doc.custom_festival_holiday_list

            for holiday in final_date_list:
                holiday_list_doc.append(
                    "holidays",
                    {
                        "description": holiday.get("description"),
                        "holiday_date": holiday.get("date"),
                        "weekly_off": holiday.get("weekly_off"),
                        "custom_is_optional_festival_leave": holiday.get("custom_is_optional_festival_leave"),
                    },
                )

            holiday_list_doc.save(ignore_permissions=True)
            return holiday_list_doc.name
        else:
            return None

    except Exception as e:
        frappe.log_error("Error while creating holiday list", frappe.get_traceback())
        throw(f"Error while creating Holiday List {str(e)}\n for more info please check error log")


def get_nth_weekday_of_month(year, month, weekday, nth):
            month_cal = calendar.monthcalendar(year, month)
            day_count = 0
            for week in month_cal:
                if week[weekday] != 0:
                    day_count += 1
                    if day_count == nth:
                        return date(year, month, week[weekday])
            return None








@frappe.whitelist()
def send_service_agreement(name):
    doc = frappe.get_doc("Employee", name)
    notification = frappe.get_doc("Notification", "Service Agreement Letter")
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})
    email = None
    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    if company_abbr == frappe.db.get_single_value("HR Settings", "custom_prompt_abbr"):
        letter_name = "Prompt Equipments _ Service Agreement"
    else:
        letter_name = "Indifoss _ Service Agreement"
    if doc.prefered_contact_email:
        if doc.prefered_contact_email == "Company Email":
            email = doc.company_email
        elif doc.prefered_contact_email == "Personal Email":
            email = doc.personal_email
        elif doc.prefered_contact_email == "User ID":
            email = doc.prefered_email
    else:
        email = doc.personal_email
    attachment = None

    pdf_content = frappe.get_print(
        "Employee", doc.name, print_format=letter_name, as_pdf=True
    )

    attachment = {
        "fname": f"{letter_name}.pdf",
        "fcontent": pdf_content,
    }

    if email:
        frappe.sendmail(
            recipients=email,
            subject=subject,
            content=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            attachments=[attachment] if attachment else None,
        )
        notify_signatory_on_email(
            doc.company, "HR Manager", doc.name, "Service Agreement Letter"
        )
        notify_signatory_on_email(
            doc.company, "Employee", doc.name, "Service Agreement Letter", email
        )
    else:
        frappe.throw("No Email found for Employee")
    return "Service Agreement sent Successfully"


@frappe.whitelist()
def send_confirmation_letter(name):
    doc = frappe.get_doc("Employee", name)
    notification = frappe.get_doc("Notification", "Confirmation Letter Notification")
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})

    email = None
    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    if company_abbr == frappe.db.get_single_value("HR Settings", "custom_prompt_abbr"):
        letter_name = "Confirmation Letter - Prompt"
    else:
        letter_name = "Confirmation Letter - IndiFOSS"
    if doc.prefered_contact_email:
        if doc.prefered_contact_email == "Company Email":
            email = doc.company_email
        elif doc.prefered_contact_email == "Personal Email":
            email = doc.personal_email
        elif doc.prefered_contact_email == "User ID":
            email = doc.prefered_email
    else:
        email = doc.personal_email

    attachment = None

    pdf_content = frappe.get_print(
        "Employee", doc.name, print_format=letter_name, as_pdf=True
    )

    attachment = {
        "fname": f"{letter_name}.pdf",
        "fcontent": pdf_content,
    }

    # ? SEND THE EMAIL
    if email:
        frappe.sendmail(
            recipients=email,
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            attachments=[attachment] if attachment else None,
        )
        notify_signatory_on_email(doc.company, "HR Manager", doc.name, letter_name)
    else:
        frappe.throw("No Email found for Employee")

    return "Confirmation Letter sent Successfully"


@frappe.whitelist()
def send_probation_extension_letter(name):
    doc = frappe.get_doc("Employee", name)
    notification = frappe.get_doc(
        "Notification", "Probation Extension Letter Notification"
    )
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})
    email = None
    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    if company_abbr == frappe.db.get_single_value("HR Settings", "custom_prompt_abbr"):
        letter_name = "Probation Extension Letter - Prompt"
    else:
        letter_name = "Probation Extension Letter - Indifoss"
    if doc.prefered_contact_email:
        if doc.prefered_contact_email == "Company Email":
            email = doc.company_email
        elif doc.prefered_contact_email == "Personal Email":
            email = doc.personal_email
        elif doc.prefered_contact_email == "User ID":
            email = doc.prefered_email
    else:
        email = doc.personal_email

    attachment = None

    pdf_content = frappe.get_print(
        "Employee", doc.name, print_format=letter_name, as_pdf=True
    )

    attachment = {
        "fname": f"{letter_name}.pdf",
        "fcontent": pdf_content,
    }
    if email:

        frappe.sendmail(
            recipients=email,
            subject=subject,
            content=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            attachments=[attachment] if attachment else None,
        )
        notify_signatory_on_email(doc.company, "HR Manager", doc.name, letter_name)
    else:
        frappe.throw("No Email found for Employee")
    return "Probation Extension Letter sent Successfully"


# ! prompt_hr.py.employee.get_raise_resignation_questions
@frappe.whitelist()
def get_raise_resignation_questions(company):
    try:

        if company == get_prompt_company_name().get("company_name"):
            # ? FETCH QUIZ NAME FROM HR SETTINGS FOR PROMPT
            quiz_name = frappe.db.get_value(
                "HR Settings", None, "custom_exit_quiz_at_employee_form_for_prompt"
            )
        elif company == get_indifoss_company_name().get("company_name"):
            # ? FETCH QUIZ NAME FROM HR SETTINGS FOR INDIFOSS
            quiz_name = frappe.db.get_value(
                "HR Settings", None, "custom_exit_quiz_at_employee_form_for_indifoss"
            )
        else:
            # ? DEFAULT QUIZ NAME IF COMPANY NOT FOUND
            frappe.throw(_("Company not recognized or quiz not configured."))

        if quiz_name is None:
            frappe.throw(_("Exit quiz not configured for this company."))

        questions = frappe.get_all(
            "LMS Quiz Question",
            filters={"parent": quiz_name},
            fields=["question", "question_detail"],
        )
        return questions

    except Exception as e:
        frappe.log_error(f"Error fetching resignation questions: {str(e)}")
        return []


from lms.lms.doctype.lms_quiz.lms_quiz import quiz_summary

import json


@frappe.whitelist()
def create_resignation_quiz_submission(
    user_response, employee, notice_number_of_days=None
):
    try:
        # ? PARSE USER RESPONSE FROM JSON STRING
        if isinstance(user_response, str):
            user_response = json.loads(user_response)

        exit_approval = create_exit_approval_process(
            user_response, employee, notice_number_of_days
        )
        return exit_approval

    except Exception as e:
        frappe.log_error(f"Error creating resignation quiz submission: {str(e)}")
        return {"error": 1, "message": str(e)}


def create_exit_approval_process(user_response, employee, notice_number_of_days=None):
    try:
        # ? CHECK IF EXIT APPROVAL PROCESS ALREADY EXISTS
        if frappe.db.exists(
            "Exit Approval Process",
            {"employee": employee, "resignation_approval": ["!=", "Rejected"]},
        ):
            return "Resignation already in process or approved."

        if not employee:
            raise Exception("Employee not found")

        exit_approval_process = frappe.new_doc("Exit Approval Process")
        exit_approval_process.employee = employee
        exit_approval_process.resignation_approval = ""
        exit_approval_process.posting_date = getdate()
        exit_approval_process.notice_period_days = notice_number_of_days
        exit_approval_process.last_date_of_working = getdate() + timedelta(
            days=int(notice_number_of_days)
        )

        # ? MAKE SURE USER_RESPONSE IS A LIST (WRAP SINGLE DICT IN A LIST IF NEEDED)
        if isinstance(user_response, dict):
            user_response = [user_response]

        # ? ADD EACH RESPONSE TO THE CHILD TABLE PROPERLY
        for response in user_response:
            exit_approval_process.append(
                "user_response",
                {
                    "question_name": response.get("question_name"),
                    "question": response.get("question"),
                    "answer": response.get("answer"),
                },
            )

        exit_approval_process.save(ignore_permissions=True)
        frappe.db.commit()

        hr_managers = get_hr_managers_by_company(exit_approval_process.company)
        send_notification_email(
            doctype="Exit Approval Process",
            docname=exit_approval_process.name,
            recipients=hr_managers,
            notification_name="Employee Exit Process Creation Notification",
        )
        return "Resignation process initiated successfully."

    except Exception as e:
        frappe.log_error(
            title="Exit Approval Process Creation Error",
            message=f"Error creating Exit Approval Process: {str(e)}\n{traceback.format_exc()}",
        )
        return None


def create_employee_changes_approval(changes):
    change_doc = frappe.get_doc(
        {"doctype": "Employee Profile Changes Approval Interface", **changes}
    )
    change_doc.insert(ignore_permissions=True)
    return change_doc.name


@frappe.whitelist()
def create_employee_details_change_request(
    employee_id, field_name, field_label, new_value, old_value=None
):
    try:
        existing_value = frappe.db.get_value(
            "Employee", {"name": employee_id, "status": "Active"}, field_name
        )

        if len(new_value) < 1:
            return {
                "status": 0,
                "message": "New value cannot be empty.",
                "data": None,
            }

        if existing_value == new_value:
            return {"status": 0, "message": "No changes detected.", "data": None}
        elif str(existing_value).strip() != str(old_value).strip():
            return {
                "status": 0,
                "message": f"Mismatch in your old value and existing value. Kindly try again and if issue persists contact System Manager. Current: {existing_value}, Provided: {old_value}",
                "data": None,
            }

        # Check for existing pending requests
        if frappe.db.exists(
            "Employee Profile Changes Approval Interface",
            {
                "employee": employee_id,
                "field_name": field_name,
                "approval_status": "Pending",
            },
        ):
            return {
                "status": 0,
                "message": "A change request for this field is already pending.",
                "data": None,
            }

        # Get company information
        company = frappe.db.get_value("Employee", employee_id, "company")
        if not company:
            return {
                "status": 0,
                "message": "No company associated with this employee.",
                "data": None,
            }

        company_abbr = frappe.db.get_value("Company", company, "abbr")

        prompt_abbr, indifoss_abbr = frappe.db.get_value(
            "HR Settings", None, ["custom_prompt_abbr", "custom_indifoss_abbr"]
        )

        if company_abbr not in [prompt_abbr, indifoss_abbr]:
            return {
                "status": 0,
                "message": "This feature is not available for the current company.",
                "data": None,
            }

        # ? DETERMINE PARENTFIELD BASED ON COMPANY
        parentfield = "custom_employee_changes_allowed_fields_for_prompt"
        if company_abbr == indifoss_abbr:
            parentfield = "custom_employee_changes_allowed_fields_for_indifoss"

        # ? CHECK IF FIELD IS ALLOWED TO BE CHANGED
        allowed_fields = frappe.db.get_value(
            "Employee Changes Allowed Fields",
            filters={"parentfield": parentfield, "field_label": field_label},
            fieldname=["field_label", "permission_required"],
        )

        if not allowed_fields:
            return {
                "status": 0,
                "message": f"The field '{field_label}' is not allowed to be changed.",
                "data": None,
            }

        # ?GET USER ASSOCIATED WITH EMPLOYEE
        user = frappe.db.get_value("Employee", employee_id, "user_id")
        if not user:
            return {
                "status": 0,
                "message": "No user associated with this employee.",
                "data": None,
            }

        # ? HANDLE BASED ON PERMISSION REQUIREMENT
        if allowed_fields[1] == 1:  # ? PERMISSION_REQUIRED = 1
            # ? CREATE APPROVAL REQUEST
            changes = {
                "field_name": field_name,
                "old_value": old_value,
                "new_value": new_value,
                "employee": employee_id,
                "approval_status": "Pending",
                "date_of_changes_made": frappe.utils.nowdate(),
            }

            changes_approval = create_employee_changes_approval(changes)

            if not changes_approval:
                return {
                    "status": 0,
                    "message": "Failed to create approval request.",
                    "data": None,
                }

            return {
                "status": 1,
                "message": "Change request submitted for approval successfully.",
                "data": changes_approval,
            }

        elif allowed_fields[1] == 0:  # ? PERMISSION_REQUIRED = 0
            # ? APPLY CHANGE DIRECTLY
            frappe.db.set_value("Employee", employee_id, field_name, new_value)
            frappe.db.commit()

            return {
                "status": 1,
                "message": "Employee details updated successfully.",
                "data": {
                    "field_name": field_name,
                    "field_label": field_label,
                    "old_value": old_value,
                    "new_value": new_value,
                    "employee": employee_id,
                    "applied_directly": True,
                },
            }
        else:
            return {
                "status": 0,
                "message": "Invalid permission configuration for this field.",
                "data": None,
            }

    except Exception as e:
        frappe.log_error(
            title="Employee Details Change Request Error",
            message=f"Error creating change request for Employee {employee_id}: {str(e)}\n{frappe.get_traceback()}",
        )
        return {
            "status": 0,
            "message": f"An error occurred while processing your request: {str(e)}",
            "data": None,
        }


# ? FUNCTION TO FETCH EDITABLE FIELDS FOR AN EMPLOYEE BASED ON THEIR COMPANY
@frappe.whitelist()
def get_employee_changable_fields(emp_id):

    # ? FETCH THE COMPANY OF THE GIVEN EMPLOYEE
    company = frappe.db.get_value("Employee", emp_id, "company")
    if not company:
        return []

    # ? FETCH CUSTOM ABBREVIATIONS FOR BOTH COMPANIES FROM HR SETTINGS
    prompt_abbr, indifoss_abbr = frappe.db.get_value(
        "HR Settings", None, ["custom_prompt_abbr", "custom_indifoss_abbr"]
    )

    # ? GET THE FULL COMPANY NAMES BASED ON ABBREVIATIONS
    abbr_to_name = {
        "prompt": frappe.db.get_value("Company", {"abbr": prompt_abbr}, "name"),
        "indifoss": frappe.db.get_value("Company", {"abbr": indifoss_abbr}, "name"),
    }

    # ? MAP COMPANY NAME TO CORRESPONDING CHILD TABLE FIELD
    company_map = {
        abbr_to_name["prompt"]: "custom_employee_changes_allowed_fields_for_prompt",
        abbr_to_name["indifoss"]: "custom_employee_changes_allowed_fields_for_indifoss",
    }

    # ? IF THE EMPLOYEE'S COMPANY IS NOT AMONG THE EXPECTED, RETURN EMPTY LIST
    parentfield = company_map.get(company)
    if not parentfield:
        return []

    # ? GET ALLOWED FIELD LABELS FOR THE COMPANY
    allowed_fields = frappe.get_all(
        "Employee Changes Allowed Fields",
        filters={"parentfield": parentfield},
        fields=["field_label"],
    )

    field_labels = [f.field_label for f in allowed_fields]
    if not field_labels:
        return []

    # ? FETCH ACTUAL DOCFIELD METADATA USING FIELD LABELS AS FIELDNAME
    fields = frappe.get_all(
        "DocField",
        filters={"parent": "Employee", "label": ["in", field_labels]},
        fields=["fieldname", "label", "fieldtype"],
        ignore_permissions=True,
    )

    return fields


# ? FUNCTION TO GET EMPLOYEE DOCTYPE FIELDS
@frappe.whitelist()
def get_employee_doctype_fields():

    try:
        # ? GET ALL FIELDS FROM EMPLOYEE DOCTYPE
        fields = frappe.get_list(
            "DocField",
            filters={"parent": "Employee", "hidden": 0},
            fields=["label", "fieldname", "fieldtype"],
            order_by="idx asc",
            ignore_permissions=True,
        )

        # ? ADD CUSTOM FIELDS FROM Employee DocType
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Employee", "hidden": 0},
            fields=["label", "fieldname", "fieldtype"],
            order_by="idx asc",
            ignore_permissions=True,
        )

        # ? APPEND CUSTOM FIELDS TO THE FIELDS LIST
        fields.extend(custom_fields)

        # ? FILTER OUT FIELDS WITHOUT LABELS AND SYSTEM FIELDS
        filtered_fields = []
        excluded_fieldtypes = [
            "Section Break",
            "Column Break",
            "Tab Break",
            "HTML",
            "Heading",
        ]

        # ? EXCLUDE FIELDS THAT ARE NOT RELEVANT FOR EMPLOYEE
        for field in fields:
            if (
                field.get("label")
                and field.get("label").strip()
                and field.get("fieldtype") not in excluded_fieldtypes
                and not field.get("fieldname", "").startswith("__")
            ):

                filtered_fields.append(
                    {
                        "label": field.get("label"),
                        "fieldname": field.get("fieldname"),
                        "fieldtype": field.get("fieldtype"),
                    }
                )

        return filtered_fields

    except Exception as e:
        frappe.log_error(
            title="Get Employee Fields Error",
            message=f"Error fetching Employee DocType fields: {str(e)}\n{frappe.get_traceback()}",
        )
        return []


# ? FUNCTION TO CREATE SALES PERSON IF IS_SALES_PERSON CHECKBOX IS TICKED AND SALES PERSON DOES NOT EXIST
def create_sales_person_if_needed(doc):
    try:
        old_doc = doc.get_doc_before_save()

        # ? CHECK IF IS_SALES_PERSON CHANGED FROM 0 TO 1 OR NEW EMPLOYEE WITH IS_SALES_PERSON = 1
        is_new_employee = not old_doc
        is_sales_person_toggled = (
            old_doc
            and str(old_doc.custom_is_sales_person) == "0"
            and str(doc.custom_is_sales_person) == "1"
        )
        is_new_sales_person = is_new_employee and str(doc.custom_is_sales_person) == "1"

        if is_sales_person_toggled or is_new_sales_person:
            # ? CHECK IF SALES PERSON ALREADY EXISTS
            if not frappe.db.exists("Sales Person", {"employee": doc.name}):
                try:
                    sales_person = frappe.new_doc("Sales Person")
                    sales_person.employee = doc.name
                    sales_person.sales_person_name = doc.employee_name
                    doc.user_id = sales_person.custom_employee_user_id

                    # ? SET PARENT SALES PERSON ONLY IF REPORTS_TO IS SALES PERSON AND HAS SALES PERSON RECORD
                    if doc.get("reports_to"):
                        # ? VALIDATE THAT THE PARENT EMPLOYEE EXISTS
                        if frappe.db.exists("Employee", doc.reports_to):
                            # ? CHECK IF PARENT IS ALSO A SALES PERSON
                            parent_is_sales_person = frappe.db.get_value(
                                "Employee", doc.reports_to, "custom_is_sales_person"
                            )
                            if parent_is_sales_person == 1:
                                # ? GET PARENT'S SALES PERSON RECORD
                                parent_sales_person = frappe.db.get_value(
                                    "Sales Person", {"employee": doc.reports_to}, "name"
                                )
                                if parent_sales_person:
                                    sales_person.parent_sales_person = (
                                        parent_sales_person
                                    )
                                    # ? SET PARENT AS GROUP SINCE IT HAS SUBORDINATES
                                    frappe.db.set_value(
                                        "Sales Person",
                                        parent_sales_person,
                                        "is_group",
                                        1,
                                    )
                                # ? IF PARENT IS SALES PERSON BUT NO SALES PERSON RECORD, DON'T LINK
                        else:
                            frappe.throw(
                                _("Invalid reports_to employee: {0}").format(
                                    doc.reports_to
                                )
                            )

                    # ? CHECK IF THIS EMPLOYEE HAS SUBORDINATES TO SET IS_GROUP
                    subordinates_count = frappe.db.count(
                        "Employee", {"reports_to": doc.name}
                    )
                    if subordinates_count > 0:
                        sales_person.is_group = 1

                    sales_person.enabled = 1
                    sales_person.insert(ignore_permissions=True)

                    # ? UPDATE DESCENDANT EMPLOYEES' SALES PERSONS
                    update_descendant_sales_persons(doc.name, sales_person.name)

                    frappe.db.commit()

                    if is_new_employee:
                        frappe.msgprint(
                            _("Sales Person created successfully for new employee.")
                        )
                    else:
                        frappe.msgprint(_("Sales Person created successfully."))

                except Exception as e:
                    frappe.db.rollback()
                    frappe.log_error(
                        f"Error creating Sales Person for employee {doc.name}: {str(e)}"
                    )
                    frappe.throw(
                        _("Failed to create Sales Person. Error: {0}").format(str(e))
                    )
            else:
                frappe.msgprint(_("Sales Person already exists for this employee."))

    except Exception as e:
        frappe.log_error(
            f"Error in create_sales_person_if_needed for employee {doc.name}: {str(e)}"
        )
        frappe.throw(
            _("An error occurred while processing Sales Person creation: {0}").format(
                str(e)
            )
        )


# ? FUNCTION TO UPDATE DESCENDANT EMPLOYEES' SALES PERSONS WHEN NEW SALES PERSON IS CREATED
def update_descendant_sales_persons(employee_name, new_sales_person_name):
    """
    UPDATES THE PARENT_SALES_PERSON FIELD FOR ALL DESCENDANT EMPLOYEES' SALES PERSONS
    WHEN A NEW SALES PERSON IS CREATED IN THE HIERARCHY
    """
    try:
        # ? GET ALL DIRECT SUBORDINATES OF THIS EMPLOYEE
        direct_subordinates = frappe.get_all(
            "Employee",
            filters={"reports_to": employee_name},
            fields=["name", "custom_is_sales_person"],
        )

        for subordinate in direct_subordinates:
            try:
                # ? CHECK IF SUBORDINATE IS SALES PERSON AND HAS SALES PERSON RECORD
                if subordinate.custom_is_sales_person == 1:
                    subordinate_sales_person = frappe.db.get_value(
                        "Sales Person", {"employee": subordinate.name}, "name"
                    )

                    if subordinate_sales_person:
                        # ? UPDATE THE PARENT_SALES_PERSON FIELD
                        frappe.db.set_value(
                            "Sales Person",
                            subordinate_sales_person,
                            "parent_sales_person",
                            new_sales_person_name,
                        )

                        frappe.msgprint(
                            _(
                                "Updated Sales Person hierarchy for employee: {0}"
                            ).format(subordinate.name)
                        )

                # ? RECURSIVELY UPDATE DESCENDANTS
                update_descendant_sales_persons(subordinate.name, new_sales_person_name)

            except Exception as e:
                frappe.log_error(
                    f"Error updating sales person for subordinate {subordinate.name}: {str(e)}"
                )
                # ? CONTINUE WITH OTHER SUBORDINATES INSTEAD OF FAILING COMPLETELY
                continue

    except Exception as e:
        frappe.log_error(
            f"Error in update_descendant_sales_persons for employee {employee_name}: {str(e)}"
        )
        # ? DON'T THROW HERE AS THIS IS CALLED DURING SALES PERSON CREATION
        frappe.msgprint(
            _("Warning: Some descendant Sales Person records may not have been updated")
        )


# ? FUNCTION TO UPDATE PARENT SALES PERSON WHEN REPORTS_TO IS CHANGED
def update_parent_sales_person_on_reports_to_change(doc):
    try:
        old_doc = doc.get_doc_before_save()

        # ? CHECK IF REPORTS_TO FIELD HAS BEEN UPDATED
        if old_doc and old_doc.reports_to != doc.reports_to:

            # ? HANDLE OLD PARENT - REMOVE IS_GROUP IF NO MORE SUBORDINATES
            if old_doc.reports_to:
                try:
                    old_parent_sales_person = frappe.db.get_value(
                        "Sales Person", {"employee": old_doc.reports_to}, "name"
                    )
                    if old_parent_sales_person:
                        # ? CHECK IF OLD PARENT STILL HAS OTHER SUBORDINATES
                        remaining_subordinates = frappe.db.count(
                            "Employee",
                            {
                                "reports_to": old_doc.reports_to,
                                "name": ["!=", doc.name],
                            },
                        )

                        if remaining_subordinates == 0:
                            frappe.db.set_value(
                                "Sales Person", old_parent_sales_person, "is_group", 0
                            )

                        # ? REMOVE PARENT LINK FROM CURRENT EMPLOYEE'S SALES PERSON IF EXISTS
                        if doc.custom_is_sales_person == 1:
                            current_employee_sales_person = frappe.db.get_value(
                                "Sales Person", {"employee": doc.name}, "name"
                            )
                            if current_employee_sales_person:
                                frappe.db.set_value(
                                    "Sales Person",
                                    current_employee_sales_person,
                                    "parent_sales_person",
                                    "Sales Team",
                                )

                except Exception as e:
                    frappe.log_error(
                        f"Error updating old parent sales person for employee {old_doc.reports_to}: {str(e)}"
                    )
                    # ? DON'T THROW HERE, CONTINUE WITH NEW PARENT PROCESSING

            # ? HANDLE NEW PARENT - SET IS_GROUP = 1 AND UPDATE CURRENT EMPLOYEE'S SALES PERSON PARENT
            if doc.reports_to:
                try:
                    # ? CHECK IF NEW PARENT EMPLOYEE EXISTS
                    if frappe.db.exists("Employee", doc.reports_to):
                        # ? CHECK IF NEW PARENT IS SALES PERSON
                        parent_is_sales_person = frappe.db.get_value(
                            "Employee", doc.reports_to, "custom_is_sales_person"
                        )
                        if parent_is_sales_person == 1:
                            new_parent_sales_person = frappe.db.get_value(
                                "Sales Person", {"employee": doc.reports_to}, "name"
                            )
                            if new_parent_sales_person:
                                # ? SET IS_GROUP = 1 FOR NEW PARENT
                                frappe.db.set_value(
                                    "Sales Person",
                                    new_parent_sales_person,
                                    "is_group",
                                    1,
                                )

                                # ? UPDATE THIS EMPLOYEE'S SALES PERSON PARENT IF THEY ARE SALES PERSON
                                if doc.custom_is_sales_person == 1:
                                    current_employee_sales_person = frappe.db.get_value(
                                        "Sales Person", {"employee": doc.name}, "name"
                                    )
                                    if current_employee_sales_person:
                                        frappe.db.set_value(
                                            "Sales Person",
                                            current_employee_sales_person,
                                            "parent_sales_person",
                                            new_parent_sales_person,
                                        )

                                frappe.db.commit()
                                frappe.msgprint(
                                    _(
                                        "Updated Sales Person hierarchy due to Parent Employee change"
                                    )
                                )
                    else:
                        frappe.throw(
                            _("Invalid new reports_to employee: {0}").format(
                                doc.reports_to
                            )
                        )

                except Exception as e:
                    frappe.db.rollback()
                    frappe.log_error(
                        f"Error updating new parent sales person for employee {doc.reports_to}: {str(e)}"
                    )
                    frappe.throw(
                        _("Failed to update parent Sales Person. Error: {0}").format(
                            str(e)
                        )
                    )

        # ? HANDLE CASE WHERE REPORTS_TO IS SET FOR NEW EMPLOYEE
        elif not old_doc and doc.reports_to and doc.custom_is_sales_person == 1:
            try:
                # ? CHECK IF PARENT IS SALES PERSON AND HAS SALES PERSON RECORD
                parent_is_sales_person = frappe.db.get_value(
                    "Employee", doc.reports_to, "custom_is_sales_person"
                )
                if parent_is_sales_person == 1:
                    parent_sales_person = frappe.db.get_value(
                        "Sales Person", {"employee": doc.reports_to}, "name"
                    )
                    if parent_sales_person:
                        # ? SET PARENT AS GROUP
                        frappe.db.set_value(
                            "Sales Person", parent_sales_person, "is_group", 1
                        )
                        frappe.db.commit()

            except Exception as e:
                frappe.log_error(
                    f"Error setting parent as group for new employee {doc.name}: {str(e)}"
                )

    except Exception as e:
        frappe.log_error(
            f"Error in update_parent_sales_person_on_reports_to_change for employee {doc.name}: {str(e)}"
        )
        frappe.throw(
            _("An error occurred while updating parent Sales Person: {0}").format(
                str(e)
            )
        )


# ? MAIN FUNCTION TO HANDLE ALL SALES PERSON OPERATIONS ON UPDATE
def handle_sales_person_operations_on_update(doc, method):
    """
    MAIN FUNCTION TO HANDLE ALL SALES PERSON OPERATIONS DURING ON_UPDATE EVENT.
    THIS HANDLES BOTH NEW EMPLOYEES AND EXISTING EMPLOYEE UPDATES.
    """
    try:

        # ? 1. CREATE SALES PERSON IF NEEDED (HANDLES BOTH NEW AND EXISTING EMPLOYEES)
        create_sales_person_if_needed(doc)

        # ? 2. UPDATE PARENT SALES PERSON RELATIONSHIPS WHEN REPORTS_TO CHANGES
        update_parent_sales_person_on_reports_to_change(doc)

        # ? 3. UPDATE GROUP FLAGS FOR EXISTING SALES PERSONS IF SUBORDINATES EXIST
        if frappe.db.exists("Sales Person", {"employee": doc.name}):
            subordinates_count = frappe.db.count("Employee", {"reports_to": doc.name})
            sales_person_name = frappe.db.get_value(
                "Sales Person", {"employee": doc.name}, "name"
            )

            if subordinates_count > 0:
                frappe.db.set_value("Sales Person", sales_person_name, "is_group", 1)
            else:
                frappe.db.set_value("Sales Person", sales_person_name, "is_group", 0)

    except Exception as e:
        frappe.log_error(
            f"Error in handle_sales_person_operations_on_update for employee {doc.name}: {str(e)}"
        )
        # ? RE-RAISE THE EXCEPTION TO ENSURE THE TRANSACTION IS ROLLED BACK
        raise


def update_employee_status_for_company(company_abbr: str):
    # Fetch employees with a set relieving date and matching company
    company_name = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")

    if company_name:
        employees = frappe.get_all(
            "Employee",
            filters={"relieving_date": ["is", "set"], "company": company_name},
            fields=["name", "relieving_date"],
        )
        today = getdate()

        for employee in employees:
            relieving_date = getdate(employee.relieving_date)

            # Update status if relieving date is today
            if today == relieving_date:
                employee_doc = frappe.get_doc("Employee", employee.name)
                employee_doc.db_set("status", "Left")

                # Disable associated user account if exists
                if employee_doc.user_id:
                    user = frappe.get_doc("User", employee_doc.user_id)
                    user.db_set("enabled", 0)


# For PROMPT company
def update_employee_status_for_prompt_company():
    prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
    update_employee_status_for_company(prompt_abbr)


# For Indifoss company
def update_employee_status_for_indifoss_company():
    indifoss_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
    update_employee_status_for_company(indifoss_abbr)

def after_insert(doc, method=None):
    
    create_shift_assignment(doc)
    
    # ! FIND CANDIDATE PORTAL RECORD FOR GIVEN JOB APPLICANT AND COMPANY
    candidate_portal = frappe.get_all("Candidate Portal", filters={
        "applicant_email": doc.job_applicant,
        "company": doc.company
    }, fields=["name"], order_by="creation desc")

    # ? EXIT IF NO CANDIDATE PORTAL FOUND
    if not candidate_portal:
        frappe.msgprint("No Candidate Portal found")
        return

    # ! FETCH DOCUMENT COLLECTION LINKED TO THE CANDIDATE PORTAL
    documents_list = frappe.get_all(
        "Document Collection",
        filters={"parent": candidate_portal[0].name},
        fields=[
            "type_of_document",
            "required_document",
            "attachment",
            "consent",
            "collection_stage",
            "upload_date",
            "upload_time",
            "ip_address_on_document_upload"
        ],
    )

    # ? EXIT IF DOCUMENT COLLECTION IS EMPTY
    if not documents_list:
        frappe.msgprint("No Document Collection records exist")
        return


    # ! REMOVE DUPLICATES BASED ON (TYPE_OF_DOCUMENT, REQUIRED_DOCUMENT)
    seen = set()
    final_doc_list = []
    for d in documents_list:
        key = (
            (d.type_of_document or "").strip().lower(),
            (d.required_document or "").strip().lower()
        )
        if key not in seen:
            final_doc_list.append(d)
            seen.add(key)

    # ! SORT DOCUMENTS: VALID TYPE_OF_DOCUMENT FIRST, NULL OR EMPTY LAST
    final_doc_list.sort(key=lambda x: (x.type_of_document is None or x.type_of_document == "", x.type_of_document or ""))

    # ! APPEND EACH DOCUMENT ENTRY TO CUSTOM_DOCUMENTS CHILD TABLE
    for document in final_doc_list:
        doc.append("custom_documents", {
            "type_of_document": document.type_of_document,
            "required_document": document.required_document,
            "attachment": document.attachment,
            "consent": document.consent,
            "collection_stage": document.collection_stage,
            "upload_date": document.upload_date,
            "upload_time": document.upload_time,
            "ip_address_on_document_upload": document.ip_address_on_document_upload
        })

    # ! SAVE CHANGES TO PARENT DOC AFTER APPENDING DOCUMENTS
    doc.save(ignore_permissions=True)

def create_shift_assignment(doc):

    if doc.default_shift and not frappe.db.exists("Shift Assignment", {"employee": doc.name, "shift_type": doc.default_shift}):
        shift_assignment_doc = frappe.new_doc("Shift Assignment")
        shift_assignment_doc.employee = doc.name
        shift_assignment_doc.shift_type = doc.default_shift
        shift_assignment_doc.start_date = getdate()
        shift_assignment_doc.insert(ignore_permissions=True)
        shift_assignment_doc.submit()

# ? METHOD TO CREATE LEAVE POLICY ASSIGNMENT
def create_leave_policy_assignment(employee_doc, based_on_joining_date, leave_period=None):
	assignment_based_on = "Joining Date" if based_on_joining_date else "Leave Period"
	print(assignment_based_on)  # ? DEBUGGING: PRINT ASSIGNMENT TYPE

	# ? CREATE DOCUMENT
	doc = frappe.new_doc("Leave Policy Assignment")
	doc.employee = employee_doc.name
	doc.assignment_based_on = assignment_based_on
	doc.leave_policy = employee_doc.custom_leave_policy

	# ? SET EFFECTIVE DATES BASED ON JOINING DATE
	if doc.assignment_based_on == "Joining Date" and doc.employee:
		employee_joining_date = frappe.db.get_value("Employee", doc.employee, "date_of_joining")
		if employee_joining_date:
			doc.effective_from = employee_joining_date

			# ? TRY TO FIND A MATCHING ACTIVE LEAVE PERIOD
			leave_period = frappe.db.get_value(
				"Leave Period",
				{
					"from_date": ("<=", employee_joining_date),
					"to_date": (">=", employee_joining_date),
					"is_active": 1
				},
				"to_date"
			)

			if leave_period:
				doc.effective_to = leave_period
			else:
				# ? SET TO 31ST DECEMBER OF THE JOINING YEAR
				joining_dt = getdate(employee_joining_date)
				dec_31 = datetime(joining_dt.year, 12, 31)
				doc.effective_to = dec_31.date()

	# ? SET LEAVE PERIOD IF AVAILABLE
	if leave_period:
		doc.leave_period = leave_period

	doc.save()
	doc.submit()

	return doc.name


def before_save(doc, method=None):
    validate_create_checkin_role(doc)


def validate_create_checkin_role(doc):
    """
    Adds or removes 'Create Checkin' role from the user based on the attendance capture scheme.
    """
    #! CONTINUE ONLY IF USER IS SET
    if not doc.user_id:
        if not doc.is_new():
            doc_before_save = frappe.get_doc(doc.doctype, doc.name)
            if doc_before_save.custom_attendance_capture_scheme != doc.custom_attendance_capture_scheme:
                frappe.msgprint("No User ID Found")
        return

    user_doc = frappe.get_doc("User", doc.user_id)

    #? ROLE TO TOGGLE
    target_role = "Create Checkin"

    #? REMOVE IF SCHEME IS BIOMETRIC
    if doc.custom_attendance_capture_scheme == "Biometric":
        user_doc.roles = [r for r in user_doc.roles if r.role != target_role]

    #? ENSURE IT EXISTS IF SCHEME IS MOBILE OR WEB
    elif doc.custom_attendance_capture_scheme in ["Mobile Clockin-Clockout", "Web Checkin-Checkout"]:
        if target_role not in [r.role for r in user_doc.roles]:
            user_doc.append("roles", {"role": target_role})

    #? SAVE CHANGES
    user_doc.save(ignore_permissions=True)


#? CUSTOM AUTONAME HANDLER FOR EMPLOYEE
def custom_autoname_employee(doc, method=None):
    #? IF 'employer_number' IS SELECTED, USE THAT
    if doc.naming_series == "Employee Number":
        if not doc.employee_number:
            frappe.throw("Employer Number is required when using 'employer_number' as naming series.")
        doc.name = doc.employee_number
        return

    #? MANUAL HANDLING FOR PE.####, PI.####, PC.####
    if doc.naming_series in ["PE.####", "PI.####", "PC.####"]:
        prefix = doc.naming_series.split(".")[0]  # PE, PI, PC
        #? REGEX TO EXTRACT LAST NUMBER FOR PREFIX
        existing_ids = frappe.db.get_all(
            "Employee",
            filters = {"name": ["like", f"{prefix}%"]},
            pluck="name"
        )

        #? EXTRACT NUMERIC PARTS AND FIND MAX
        last_number = 0
        pattern = re.compile(rf"{prefix}(\d+)")
        for eid in existing_ids:
            match = pattern.match(eid)
            if match:
                num = int(match.group(1))
                last_number = max(last_number, num)
        #? GENERATE NEXT NAME
        next_number = last_number + 1
        doc.name = f"{prefix}{str(next_number).zfill(4)}"

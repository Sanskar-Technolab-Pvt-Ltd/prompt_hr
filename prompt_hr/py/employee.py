import frappe
from frappe import throw
from frappe.utils import getdate, nowdate
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_format
from prompt_hr.api.main import notify_signatory_on_email
import traceback
from prompt_hr.py.utils import send_notification_email, get_hr_managers_by_company
import calendar
from datetime import timedelta
from dateutil import relativedelta
from frappe import _
from prompt_hr.py.utils import get_prompt_company_name, get_indifoss_company_name

# ? COMMON FIELDS THAT EXIST IN BOTH EMPLOYEE & EMPLOYEE PROFILE
common_fields = [
    "employee",
    "naming_series",
    "first_name",
    "middle_name",
    "last_name",
    "employee_name",
    "gender",
    "date_of_birth",
    "salutation",
    "date_of_joining",
    "image",
    "status",
    "erpnext_user",
    "user_id",
    "company",
    "department",
    "sub_department",
    "employee_number",
    "designation",
    "business_unit",
    "reports_to",
    "dotted_line_manager",
    "employment_type",
    "product_line",
    "grade",
    "work_location",
    "country",
    "territoty",
    "zone",
    "state",
    "district",
    "sub_district",
    "village",
    "scheduled_confirmation_date",
    "final_confirmation_date",
    "contract_end_date",
    "notice_number_of_days",
    "date_of_retirement",
    "verification_stat",
    "cell_number",
    "work_mobile_no",
    "preferred_mobile",
    "preferred_mobile_no",
    "personal_email",
    "company_email",
    "prefered_contact_email",
    "prefered_email",
    "unsubscribed",
    "current_address",
    "current_accommodation_type",
    "permanent_address",
    "permanent_accommodation_type",
    "person_to_be_contacted",
    "emergency_phone_number",
    "relation",
    "attendance_device_id",
    "weekoff",
    "attendance_capture_scheme",
    "holiday_list",
    "default_shift",
    "pf_consent",
    "eps_consent",
    "esi_consent",
    "nps_consent",
    "mealcard_consent",
    "provident_fund_account",
    "esi_number",
    "uan_number",
    "pan_number",
    "aadhaar_number",
    "name_as_per_aadhaar",
    "pran_number",
    "mealcard_number",
    "bank_name",
    "bank_ac_no",
    "iban",
    "marital_status",
    "blood_group",
    "physically_handicaped",
    "bio",
    "nominee_details",
    "family_background",
    "passport_number",
    "valid_upto",
    "date_of_issue",
    "place_of_issue",
    "educational_qualification",
    "education",
    "external_work_history",
    "internal_work_history",
    "resignation_letter_date",
    "relieving_date",
    "is_notice_period_served",
    "held_on",
    "new_workplace",
    "is_fit_to_be_rehired",
    "leave_encashed",
    "encashment_date",
    "ff_settlement_date",
    "reason_for_leaving",
    "feedback",
]

# ? MAPPING FOR CUSTOM FIELDS FROM EMPLOYEE → EMPLOYEE PROFILE
field_mapping = {
    "pf_consent": "custom_pf_consent",
    "eps_consent": "custom_eps_consent",
    "esi_consent": "custom_esi_consent",
    "nps_consent": "custom_nps_consent",
    "mealcard_consent": "custom_mealcard_consent",
    "physically_handicaped": "custom_physically_handicaped",
    "is_notice_period_served": "custom_is_notice_period_served",
    "is_fit_to_be_rehired": "custom_is_fit_to_be_rehired",
    "nominee_details": "custom_nominee_details",
    "attendance_capture_scheme": "custom_attendance_capture_scheme",
    "weekoff": "custom_weekoff",
    # ? ADD MORE IF NEEDED
}


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


# ? HELPER FUNCTION TO LOG ERROR WITH 140-CHAR LIMIT
def log(msg):
    if len(msg) > 140:
        msg = msg[:137] + "..."
    frappe.log_error(title="Employee Profile Sync", message=msg)


# ? FUNCTION TO CREATE/UPDATE EMPLOYEE PROFILE FROM EMPLOYEE DOC
def create_or_update_employee_profile(doc):
    employee_id = doc.name
    log(f"Syncing Employee Profile for Employee ID: {employee_id}")

    # ? FETCH OR CREATE EMPLOYEE PROFILE
    if frappe.db.exists("Employee Profile", {"employee": employee_id}):
        log(f"Employee Profile exists for {employee_id}, fetching...")
        employee_profile = frappe.get_doc("Employee Profile", {"employee": employee_id})
    else:
        log(f"No Employee Profile found for {employee_id}, creating new...")
        employee_profile = frappe.new_doc("Employee Profile")
        employee_profile.employee = employee_id

    # ? SYNC COMMON FIELDS
    log("Syncing common fields...")
    for field in common_fields:
        value = doc.get(field)
        if value not in [None, "", [], {}]:
            log(f"Setting common field '{field}' = {value}")
            employee_profile.set(field, value)

    # ? SYNC CUSTOM FIELDS
    log("Syncing custom mapped fields...")
    for source_field, target_field in field_mapping.items():
        value = doc.get(source_field)
        if value not in [None, "", [], {}]:
            log(f"Mapping field '{source_field}' -> '{target_field}' = {value}")
            employee_profile.set(target_field, value)

    log(f"Saving Employee Profile for {employee_id}")
    employee_profile.save()
    log(f"Employee Profile synced successfully for {employee_id}")


# ? CALLED ON EMPLOYEE UPDATE
def on_update(doc, method):
    log(f"on_update triggered for Employee: {doc.name}")

    # # ? SYNC EMPLOYEE PROFILE
    # create_or_update_employee_profile(doc)

    handle_sales_person_operations_on_update(doc, method)

    # ? CREATE WELCOME PAGE IF NOT EXISTS
    if doc.user_id:
        log(f"Employee has user_id: {doc.user_id}")
        if not frappe.db.exists("Welcome Page", {"user": doc.user_id}):
            log(f"Welcome Page does not exist for {doc.user_id}, creating...")
            create_welcome_status(doc.user_id, doc.company)
        else:
            log(f"Welcome Page already exists for {doc.user_id}")
    else:
        log("No user_id set on Employee, skipping Welcome Page creation")


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


def create_holiday_list(doc):
    """Creating Holiday list by Fetching Dates from the festival holiday list and calculating date based on days mentioned in weeklyoff type between from date to date in festival holiday list"""
    try:

        final_date_list = []

        # ? * FETCHING FESTIVAL HOLIDAYS DATES
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
            }
            for row in festival_holiday_list_doc.get("holidays")
        ]

        # ?* CALCULATING WEEKLYOFF DATES
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
            weekday = getattr(calendar, (weeklyoff_day).upper())
            reference_date = start_date + relativedelta.relativedelta(weekday=weekday)

            while reference_date <= end_date:
                if not any(
                    holiday_date.get("date") == reference_date
                    for holiday_date in final_date_list
                ):
                    final_date_list.append(
                        {
                            "date": reference_date,
                            "description": weeklyoff_day,
                            "weekly_off": 1,
                        }
                    )
                reference_date += timedelta(days=7)

        if final_date_list:
            holiday_list_doc = frappe.new_doc("Holiday List")
            holiday_list_doc.holiday_list_name = (
                f"{festival_holiday_list_doc.name}-{doc.custom_weeklyoff}"
            )
            holiday_list_doc.from_date = festival_holiday_list_doc.from_date
            holiday_list_doc.to_date = festival_holiday_list_doc.to_date
            holiday_list_doc.custom_weeklyoff_type = doc.custom_weeklyoff
            holiday_list_doc.custom_festival_holiday_list = (
                doc.custom_festival_holiday_list
            )

            for holiday in final_date_list:
                holiday_list_doc.append(
                    "holidays",
                    {
                        "description": holiday.get("description"),
                        "holiday_date": holiday.get("date"),
                        "weekly_off": holiday.get("weekly_off"),
                    },
                )

            holiday_list_doc.save(ignore_permissions=True)
            return holiday_list_doc.name
        else:
            return None

    except Exception as e:
        frappe.log_error("Error while creating holiday list", frappe.get_traceback())
        throw(
            f"Error while creating Holiday List {str(e)}\n for more info please check error log"
        )


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

    # ? Send the email
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
            return

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
        return exit_approval_process.name

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
        ignore_permissions = True
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
            ignore_permissions = True
        )

        # ? ADD CUSTOM FIELDS FROM Employee DocType
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Employee", "hidden": 0},
            fields=["label", "fieldname", "fieldtype"],
            order_by="idx asc",
            ignore_permissions = True
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

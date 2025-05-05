import frappe
from frappe import throw
from frappe.utils import getdate
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_format
from prompt_hr.api.main import notify_signatory_on_email
import traceback
from prompt_hr.py.utils import send_notification_email

# ? COMMON FIELDS THAT EXIST IN BOTH EMPLOYEE & EMPLOYEE PROFILE
common_fields = [
    "employee", "naming_series", "first_name", "middle_name", "last_name", "employee_name",
    "gender", "date_of_birth", "salutation", "date_of_joining", "image", "status",
    "erpnext_user", "user_id", "company", "department", "sub_department", "employee_number",
    "designation", "business_unit", "reports_to", "dotted_line_manager", "employment_type", "product_line",
    "grade", "work_location", "country", "territoty", "zone", "state",
    "district", "sub_district", "village", "scheduled_confirmation_date", "final_confirmation_date", "contract_end_date",
    "notice_number_of_days", "date_of_retirement", "verification_stat", "cell_number", "work_mobile_no", "preferred_mobile",
    "preferred_mobile_no", "personal_email", "company_email", "prefered_contact_email", "prefered_email", "unsubscribed",
    "current_address", "current_accommodation_type", "permanent_address", "permanent_accommodation_type", "person_to_be_contacted", "emergency_phone_number",
    "relation", "attendance_device_id", "weekoff", "attendance_capture_scheme", "holiday_list", "default_shift",
    "pf_consent", "eps_consent", "esi_consent", "nps_consent", "mealcard_consent", "provident_fund_account",
    "esi_number", "uan_number", "pan_number", "aadhaar_number", "name_as_per_aadhaar", "pran_number",
    "mealcard_number", "bank_name", "bank_ac_no", "iban", "marital_status", "blood_group",
    "physically_handicaped", "bio", "nominee_details", "family_background", "passport_number", "valid_upto",
    "date_of_issue", "place_of_issue", "educational_qualification", "education", "external_work_history", "internal_work_history",
    "resignation_letter_date", "relieving_date", "is_notice_period_served", "held_on", "new_workplace", "is_fit_to_be_rehired",
    "leave_encashed", "encashment_date", "ff_settlement_date", "reason_for_leaving", "feedback"
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
def create_welcome_status(user_id):
    try:
        # ? CHECK IF WELCOME PAGE ALREADY EXISTS
        if frappe.db.exists("Welcome Page", {"user": user_id}):
            frappe.log_error(
                title="Welcome Page Already Exists",
                message=f"Welcome Page for user {user_id} already exists. Skipping creation."
            )
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
            share=0
        )

        frappe.db.commit()

        frappe.log_error(
            title="Welcome Page Creation",
            message=f"Welcome Page created and shared with user {user_id}."
        )

    except Exception as e:
        frappe.log_error(
            title="Welcome Page Creation Error",
            message=f"Error creating Welcome Page for user {user_id}: {str(e)}\n{traceback.format_exc()}"
        )

# ? FUNCTION TO CREATE/UPDATE EMPLOYEE PROFILE FROM EMPLOYEE DOC
def create_or_update_employee_profile(doc):
    employee_id = doc.name

    # ? FETCH OR CREATE EMPLOYEE PROFILE
    if frappe.db.exists('Employee Profile', {'employee': employee_id}):
        employee_profile = frappe.get_doc('Employee Profile', {'employee': employee_id})
    else:
        employee_profile = frappe.new_doc('Employee Profile')
        employee_profile.employee = employee_id

    # ? SYNC COMMON FIELDS
    for field in common_fields:
        value = doc.get(field)
        if value not in [None, "", [], {}]:
            employee_profile.set(field, value)

    # ? SYNC CUSTOM FIELDS
    for source_field, target_field in field_mapping.items():
        value = doc.get(source_field)
        if value not in [None, "", [], {}]:
            employee_profile.set(target_field, value)

    employee_profile.save()

# ? CALLED ON EMPLOYEE UPDATE
def on_update(doc, method):
    # ? SYNC EMPLOYEE PROFILE
    create_or_update_employee_profile(doc)

    # ? CREATE WELCOME PAGE IF IT DOESN’T EXIST AND USER ID IS SET
    if doc.user_id and not frappe.db.exists("Welcome Page", {"user": doc.user_id}):
        create_welcome_status(doc.user_id)


def validate(doc, method):
    
    # ? * CHECKING IF HOLIDAY LIST EXISTS IF NOT THEN CREATING A NEW HOLIDAY LIST BASED ON THE WEEKLYOFF TYPE AND FESTIVAL HOLIDAY LIST
    if doc.custom_weeklyoff and doc.custom_festival_holiday_list:
        holiday_list = frappe.db.exists("Holiday List", {"custom_weeklyoff_type": doc.custom_weeklyoff, "custom_festival_holiday_list": doc.custom_festival_holiday_list}, "name")
        
        if holiday_list:
            doc.holiday_list = holiday_list
        else:
            holiday_list = create_holiday_list(doc)

            if holiday_list:
                doc.holiday_list = holiday_list
            

def create_holiday_list(doc):
    """Creating Holiday list by Fetching Dates from the festival holiday list and calculating date based on days mentioned in weeklyoff type between from date to date in festival holiday list
    """
    try:
        import calendar
        from datetime import timedelta
        from dateutil import relativedelta
        
        final_date_list = []
        
        # ? * FETCHING FESTIVAL HOLIDAYS DATES
        festival_holiday_list_doc = frappe.get_doc("Festival Holiday List", doc.custom_festival_holiday_list)
        
        if not festival_holiday_list_doc:
            throw("No Festival Holiday List Found")
        
        final_date_list = [{"date":getdate(row.holiday_date), "description": row.description, "weekly_off": row.weekly_off} for row in festival_holiday_list_doc.get("holidays")]

        # ?* CALCULATING WEEKLYOFF DATES
        start_date = getdate(festival_holiday_list_doc.from_date)
        end_date = getdate(festival_holiday_list_doc.to_date)
        
        weeklyoff_days = frappe.get_all("WeekOff Multiselect", {"parenttype": "WeeklyOff Type", "parent": doc.custom_weeklyoff}, "weekoff", order_by="weekoff asc", pluck="weekoff")
        
        if not weeklyoff_days:
            throw(f"No WeeklyOff days found for WeeklyOff Type {doc.custom_weeklyoff}")
        
        for weeklyoff_day in weeklyoff_days:
            weekday = getattr(calendar, (weeklyoff_day).upper())
            reference_date = start_date + relativedelta.relativedelta(weekday=weekday)
            
            while reference_date <= end_date:
                if not any(holiday_date.get("date") == reference_date for holiday_date in final_date_list):
                    final_date_list.append({
                        "date": reference_date,
                        "description": weeklyoff_day,
                        "weekly_off": 1
                    })
                reference_date += timedelta(days=7)
        
        if final_date_list:
            holiday_list_doc = frappe.new_doc("Holiday List")
            holiday_list_doc.holiday_list_name = "Testing1"
            holiday_list_doc.from_date = festival_holiday_list_doc.from_date
            holiday_list_doc.to_date = festival_holiday_list_doc.to_date
            holiday_list_doc.custom_weeklyoff_type = doc.custom_weeklyoff
            holiday_list_doc.custom_festival_holiday_list = doc.custom_festival_holiday_list
                
            for holiday in final_date_list:
                holiday_list_doc.append("holidays", {"description": holiday.get("description"),"holiday_date": holiday.get("date"), "weekly_off": holiday.get("weekly_off")})
        
            holiday_list_doc.save(ignore_permissions=True)
            return holiday_list_doc.name
        else:
            return None

    except Exception as e:
        frappe.log_error("Error while creating holiday list", frappe.get_traceback())
        throw(f"Error while creating Holiday List {str(e)}\n for more info please check error log")
    
@frappe.whitelist()
def send_service_agreement(name):
    doc = frappe.get_doc("Employee", name)
    notification = frappe.get_doc("Notification", "Service Agreement Letter")
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})
    email = None
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
    if notification.attach_print and notification.print_format:
        pdf_content = frappe.get_print(
            "Employee", 
            doc.name, 
            print_format=notification.print_format, 
            as_pdf=True
        )
        
        attachment = {
            "fname": f"{notification.print_format}.pdf",
            "fcontent": pdf_content
        }

    if email:
        frappe.sendmail(
            recipients=email,
            subject=subject,
            content=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            attachments=[attachment] if attachment else None
        )
        notify_signatory_on_email(doc.company, "HR Manager",doc.name,"Service Agreement Letter")
        notify_signatory_on_email(doc.company, "Employee",doc.name,"Service Agreement Letter",email)
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
    if notification.attach_print and notification.print_format:
        pdf_content = frappe.get_print(
            "Employee", 
            doc.name, 
            print_format=notification.print_format, 
            as_pdf=True
        )
        
        attachment = {
            "fname": f"{notification.print_format}.pdf",
            "fcontent": pdf_content
        }

    # ? Send the email
    if email:
        frappe.sendmail(
            recipients=email,
            subject=subject,
            message=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            attachments=[attachment] if attachment else None
        )
        notify_signatory_on_email(doc.company, "HR Manager",doc.name,"Confirmation Letter")
    else:
        frappe.throw("No Email found for Employee")
        
    return "Confirmation Letter sent Successfully"

@frappe.whitelist()
def send_probation_extension_letter(name):
    doc = frappe.get_doc("Employee", name)
    notification = frappe.get_doc("Notification", "Probation Extension Letter Notification")
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})
    email = None
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
    if notification.attach_print and notification.print_format:
        pdf_content = frappe.get_print(
            "Employee", 
            doc.name, 
            print_format=notification.print_format, 
            as_pdf=True
        )
        
        attachment = {
            "fname": f"{notification.print_format}.pdf",
            "fcontent": pdf_content
        }

    if email:
        frappe.sendmail(
            recipients=email,
            subject=subject,
            content=message,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            attachments=[attachment] if attachment else None
        )
        notify_signatory_on_email(doc.company, "HR Manager",doc.name,"Probation Extension Letter")
    else:
        frappe.throw("No Email found for Employee")
    return "Probation Extension Letter sent Successfully"

# ! prompt_hr.py.employee.get_raise_resignation_questions
@frappe.whitelist()
def get_raise_resignation_questions():
    try:
        # ? FETCH QUIZ NAME FROM HR SETTINGS
        quiz_name = "prompt-resignation-questionnaire"
        
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
def create_resignation_quiz_submission(user_response, employee):
    try:
        # ? PARSE USER RESPONSE FROM JSON STRING
        if isinstance(user_response, str):
            user_response = json.loads(user_response)

        exit_approval = create_exit_approval_process(user_response,employee)
        return exit_approval

    except Exception as e:
        frappe.log_error(f"Error creating resignation quiz submission: {str(e)}")
        return {"error": 1, "message": str(e)}

        
def create_exit_approval_process(user_response, employee):
    try:
        # ? CHECK IF EXIT APPROVAL PROCESS ALREADY EXISTS
        if frappe.db.exists("Exit Approval Process", {"employee": employee, "resignation_approval": ["!=", "Rejected"]}):
            return
            
        if not employee:
            raise Exception("Employee not found")
            
        exit_approval_process = frappe.new_doc("Exit Approval Process")
        exit_approval_process.employee = employee
        exit_approval_process.resignation_approval = ""
        exit_approval_process.posting_date = getdate()
        
        # ? MAKE SURE USER_RESPONSE IS A LIST (WRAP SINGLE DICT IN A LIST IF NEEDED)
        if isinstance(user_response, dict):
            user_response = [user_response]
            
        # ? ADD EACH RESPONSE TO THE CHILD TABLE PROPERLY
        for response in user_response:
            exit_approval_process.append("user_response", {
                "question_name": response.get("question_name"),
                "question": response.get("question"),
                "answer": response.get("answer")
            })
                
        exit_approval_process.save(ignore_permissions=True)
        frappe.db.commit()
        return exit_approval_process.name
        
    except Exception as e:
        frappe.log_error(
            title="Exit Approval Process Creation Error",
            message=f"Error creating Exit Approval Process: {str(e)}\n{traceback.format_exc()}"
        )
        return None
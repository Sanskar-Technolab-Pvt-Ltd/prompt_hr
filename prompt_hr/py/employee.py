import frappe
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_format

import traceback

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
            attachments=[attachment] if attachment else None
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

    # Send the email
    if email:
        frappe.sendmail(
            recipients=email,
            subject=subject,
            message=message,
            attachments=[attachment] if attachment else None
        )
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
            attachments=[attachment] if attachment else None
        )
    else:
        frappe.throw("No Email found for Employee")
    return "Probation Extension Letter sent Successfully"
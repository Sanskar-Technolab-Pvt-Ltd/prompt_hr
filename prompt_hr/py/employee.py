import frappe

# List of common fields where field names are the same in both doctypes
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

# Mapping for custom field names in Employee → matching field in Employee Profile
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
            # Add more if needed
        }

# Triggered on Employee update
@frappe.whitelist()
def on_update(doc, method):
    create_or_update_employee_profile(doc)

# Sync fields from Employee to Employee Profile
@frappe.whitelist()
def create_or_update_employee_profile(doc):
    employee_id = doc.name

    if frappe.db.exists('Employee Profile', {'employee': employee_id}):
        employee_profile = frappe.get_doc('Employee Profile', {'employee': employee_id})
    else:
        employee_profile = frappe.new_doc('Employee Profile')
        employee_profile.employee = employee_id

    # ? SYNC STANDARD/COMMON FIELDS
    for field in common_fields:
        value = doc.get(field)
        if value not in [None, "", [], {}]:
            employee_profile.set(field, value)

    # Sync custom field mappings
    for source_field, target_field in field_mapping.items():
        value = doc.get(source_field)
        if value not in [None, "", [], {}]:
            employee_profile.set(target_field, value)

    employee_profile.save()

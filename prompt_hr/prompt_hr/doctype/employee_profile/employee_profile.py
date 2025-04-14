# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
import datetime


class EmployeeProfile(Document):

    # ? ON UPDATE EVENT CONTROLLER METHOD
    def on_update(self):
        # ? ENSURES IT RUNS ONLY ON UPDATES, NOT CREATION
        if not self.is_new() and self.employee:
            changes = self.get_employee_changes()

            # ? ONLY CREATE EMPLOYEE CHANGES APPROVAL IF THERE ARE CHANGES
            if changes:
                # ? CREATE EMPLOYEE CHANGES APPROVAL DOCUMENTS
                self.create_employee_changes_approval(changes)

    # ? COMPARE EMPLOYEE PROFILE WITH EMPLOYEE MASTER AND RETURN CHANGED FIELDS
    def get_employee_changes(self):
        employee_data = frappe.get_doc("Employee", self.employee)

        # logical_field_name: actual_fieldname_in_employee_doctype
        field_map = {
             "pf_consent": "custom_pf_consent",
            "eps_consent": "custom_eps_contribution",
            "esi_consent": "custom_esi_consent",
            "nps_consent": "custom_nps_consent",
            "mealcard_consent": "custom_meal_card_consent",
            "physically_handicaped": "custom_physically_handicaped",
            "is_notice_period_served": "custom_is_notice_period_served",
            "is_fit_to_be_rehired": "custom_is_fit_to_be_rehired",
            "nominee_details": "custom_nominee_details_table",
            "attendance_capture_scheme": "custom_attendance_capture_scheme",
            "weekoff": "custom_weekoff",
            "preferred_mobile": "custom_preferred_mobile",
            "preferred_mobile_no": "custom_preferred_mobile_no"
        }

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

        changes = []
        for field in common_fields:
            employee_field = field_map.get(field, field)  # use mapped name if exists
            old_value = self.format_value(employee_data.get(employee_field)) or ""
            new_value = self.format_value(self.get(field)) or ""

            if old_value != new_value:
                changes.append({
                    "field_name": field,
                    "old_value": old_value,
                    "new_value": new_value,
                    "employee": self.employee,
                    "employee_profile_id": self.name,
                    "approval_status": "Pending",
                    "date_of_changes_made": nowdate()
                })

        return changes


    # ? FUNCTION TO CREATE EMPLOYEE CHANGES APPROVAL DOCUMENTS FOR DETECTED CHANGES
    def create_employee_changes_approval(self, changes):
        for change in changes:
            change_doc = frappe.get_doc({
                "doctype": "Employee Profile Changes Approval Interface",
                **change
            })
            change_doc.insert(ignore_permissions=True)

    # ? FUNCTION TO CONVERT DATE VALUES TO STRING FORMAT FOR PROPER COMPARISON
    def format_value(self, value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.strftime('%Y-%m-%d')
        return str(value) if value is not None else ""

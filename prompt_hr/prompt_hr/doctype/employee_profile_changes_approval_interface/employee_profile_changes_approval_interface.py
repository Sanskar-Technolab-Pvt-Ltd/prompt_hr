# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class EmployeeProfileChangesApprovalInterface(Document):

    # ? ON UPDATE EVENT CONTROLLER METHOD
    def on_update(self):
        # ? HANDLE APPROVAL LOGIC
        if self.approval_status == "Approved" and (self.changes_applicable_date == nowdate() or not self.changes_applicable_date):
            # ? SET EFFECTIVE DATE IF NOT ALREADY SET
            if not self.changes_applicable_date:
                self.changes_applicable_date = nowdate()
                self.save(ignore_permissions=True)

            self.apply_changes_to_employee()

        # # ? HANDLE REJECTION LOGIC
        # elif self.approval_status == "Rejected":
        #     self.sync_data_from_employee()

    # ? UPDATE EMPLOYEE MASTER WITH APPROVED CHANGES
    def apply_changes_to_employee(self):
        # if not self.employee or not self.employee_profile_id:
        #     return

        if not self.employee:
            return

        employee = frappe.get_doc("Employee", self.employee)
        employee.set(self.field_name, self.new_value)
        employee.save(ignore_permissions=True)

        # self.sync_employee_to_profile(employee)

        frappe.msgprint(f"Approved changes applied to Employee {self.employee}")

    # ? SYNC ORIGINAL VALUES FROM EMPLOYEE TO EMPLOYEE PROFILE ON REJECTION
    def sync_data_from_employee(self):
        if not self.employee or not self.employee_profile_id:
            return

        employee = frappe.get_doc("Employee", self.employee)
        self.sync_employee_to_profile(employee)

        frappe.msgprint(f"Rejected changes. Reverted Employee Profile for {self.employee}")

    # ? HELPER TO SYNC EMPLOYEE MASTER TO EMPLOYEE PROFILE
    def sync_employee_to_profile(self, employee):
        employee_profile = frappe.get_doc("Employee Profile", self.employee_profile_id)

        # Full list of common fields
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

        # Custom field mapping
        field_mapping = {
            "custom_nps_consent": "nps_consent",
            "custom_eps_consent": "eps_consent",
            "custom_esi_consent": "esi_consent",
            "custom_pf_consent": "pf_consent",
            "custom_mealcard_consent": "mealcard_consent",
            "custom_physically_handicaped": "physically_handicaped",
            "custom_weekoff": "weekoff",
            "custom_attendance_capture_scheme": "attendance_capture_scheme",
            "custom_preferred_mobile": "preferred_mobile",
        }

        # Sync common fields
        for field in common_fields:
            value = employee.get(field)
            if value not in [None, "", [], {}]:
                employee_profile.set(field, value)

        # Sync custom mapped fields
        for source_field, target_field in field_mapping.items():
            value = employee.get(source_field)
            if value not in [None, "", [], {}]:
                employee_profile.set(target_field, value)

        employee_profile.save(ignore_permissions=True)

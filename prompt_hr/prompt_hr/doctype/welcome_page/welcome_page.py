import frappe
import traceback
from frappe.model.document import Document

# ? FUNCTION TO SYNC WELCOME PAGE DATA TO EMPLOYEE AND EMPLOYEE PROFILE
def sync_welcome_page_data_to_employee_docs(user_id, fields_to_update):
    try:
        # ? GET EMPLOYEE USING USER ID
        employee = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
        if not employee:
            return

        # ? UPDATE EMPLOYEE
        frappe.db.set_value("Employee", employee, fields_to_update)

        # ? UPDATE EMPLOYEE PROFILE
        employee_profile = frappe.db.get_value("Employee Profile", {"employee": employee}, "name")
        if employee_profile:
            frappe.db.set_value("Employee Profile", employee_profile, fields_to_update)

    except Exception as e:
        frappe.log_error(
            title="Welcome Page Sync Error",
            message=f"Error syncing Welcome Page data for user {user_id}: {str(e)}\n{traceback.format_exc()}"
        )

# ? WELCOME PAGE CLASS
class WelcomePage(Document):

    # ? ON UPDATE SYNC TO EMPLOYEE + EMPLOYEE PROFILE
    def on_update(self):
        fields_to_update = {}

        # ? SYNC NPS CONSENT FIELD AS CHECKBOX (YES/NO -> 1/0)
        if self.nps_consent:
            fields_to_update["custom_nps_consent"] = 1 if self.nps_consent == "Yes" else 0

        # ? SYNC PRAN NUMBER ONLY IF USER HAS ONE
        if self.do_you_have_a_pran_no == 1 and self.pran_no:
            fields_to_update["custom_pran_number"] = self.pran_no

        # ? SYNC ONLY IF USER IS LINKED AND FIELDS EXIST
        if self.user and fields_to_update:
            sync_welcome_page_data_to_employee_docs(self.user, fields_to_update)


# ? FUNCTION To check whether a user should be redirected to the Welcome Page
@frappe.whitelist()
def check_welcome_page_validation(user_id):
    try:
        prompt_abbr, indifoss_abbr = frappe.db.get_value(
            "HR Settings", None, ["custom_prompt_abbr", "custom_indifoss_abbr"]
        )

        employee_company = frappe.db.get_value("Employee", {"user_id": user_id}, "company")
        if not employee_company:
            return {"success": 0, "message": "Employee company not found", "data": None}

        company_abbr = frappe.db.get_value("Company", employee_company, "abbr")
        if not company_abbr:
            return {"success": 0, "message": "Company abbreviation not found", "data": None}

        permission = None
        if company_abbr == prompt_abbr:
            permission = frappe.db.get_value("HR Settings", None, "custom_enable_welcome_page_for_prompt")
        elif company_abbr == indifoss_abbr:
            permission = frappe.db.get_value("HR Settings", None, "custom_enable_welcome_page_for_indifoss")
        else:
            return {
                "success": 0,
                "message": "Company abbreviation does not match any known values",
                "data": None
            }

        if str(permission) == "1":
            wp_data = frappe.db.get_value("Welcome Page", {"user": user_id}, ["name", "is_completed"], as_dict=True)
            if wp_data and str(wp_data.get("is_completed")) == "0":
                return {"success": 1, "message": "Welcome page data fetched", "data": wp_data}
            else:
                return {"success": 0, "message": "Welcome Page not found for user", "data": None}

        return {"success": 0, "message": "Welcome Page not enabled for this company", "data": None}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "check_welcome_page_validation")
        return {"success": 0, "message": f"Error: {str(e)}", "data": None}

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

# ? HELPER FUNCTION TO CHECK IF DEPENDS_ON IS SATISFIED
def is_depends_on_satisfied(doc, field_meta):
    if field_meta.depends_on and field_meta.depends_on.startswith("eval:"):
        expr = field_meta.depends_on[5:]  # ? REMOVE "eval:" PREFIX
        try:
            return frappe.safe_eval(expr, None, {"doc": doc})
        except Exception:
            return False
    return True  # ? NO DEPENDS_ON CONDITION

# ? WELCOME PAGE CLASS
class WelcomePage(Document):

    # ? VALIDATION BEFORE SAVING
    def before_save(self):
        # ? REQUIRED SELECT FIELDS THAT CANNOT BE LEFT EMPTY (IF DISPLAYED)
        required_select_fields = [
            "do_you_have_a_pran_no", "nps_consent", "meal_wallet", "meal_amount",
            "fuel_wallet", "fuel_amount", "attire_wallet", "attire_amount",
            "consent_for_background_verification"
        ]

        for fieldname in required_select_fields:
            # ? FETCH FIELD META
            meta_field = self.meta.get_field(fieldname)
            if not meta_field:
                continue

            # ? SKIP IF DEPENDS_ON IS NOT SATISFIED (I.E. FIELD NOT VISIBLE)
            if not is_depends_on_satisfied(self, meta_field):
                continue

            # ? THROW IF EMPTY
            if self.get(fieldname) == "":
                frappe.throw(f"Field '{meta_field.label}' cannot be left empty.")

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

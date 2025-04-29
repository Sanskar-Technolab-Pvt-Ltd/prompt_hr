import frappe
import json
from prompt_hr.py.utils import validate_hash

# ? FUNCTION TO START QUIZ RITUALS WITH VALIDATION
@frappe.whitelist()
def start_quiz_rituals(phone, password):
    try:
        doctype = "Job Applicant"
        filters_dict = {"phone_number": phone,"custom_active_quiz": 0}

        # ? CONVERT FILTERS_DICT TO JSON STRING
        filters_json = json.dumps(filters_dict)

        # ? VALIDATE HASH
        status = validate_hash(hash=password, filters=filters_json, doctype=doctype)

        if status:
            frappe.db.set_value("Job Applicant", filters_dict, "custom_active_quiz", 1)  

        return status

    except frappe.ValidationError as ve:
        # ? HANDLE SPECIFIC VALIDATION ERROR FROM validate_hash
        return {"error": 1, "message": str(ve)}

    except Exception as e:
        # ? LOG UNEXPECTED ERRORS
        frappe.log_error(f"Error in start_quiz_rituals: {str(e)}")
        return {"error": 1, "message": "An unexpected error occurred. Please try again."}

@frappe.whitelist()
def quiz_submission_rituals(phone, password):
    try:
        doctype = "Job Applicant"
        filters_dict = {"phone_number": phone, "custom_active_quiz": 1}

        # ? CONVERT FILTERS_DICT TO JSON STRING
        filters_json = json.dumps(filters_dict)

        # ? VALIDATE HASH
        status = validate_hash(hash=password, filters=filters_json, doctype=doctype)

        return status

    except frappe.ValidationError as ve:
        # ? HANDLE SPECIFIC VALIDATION ERROR FROM validate_hash
        return {"error": 1, "message": str(ve)}

    except Exception as e:
        # ? LOG UNEXPECTED ERRORS
        frappe.log_error(f"Error in quiz_submission_rituals: {str(e)}")
        return {"error": 1, "message": "An unexpected error occurred. Please try again."}

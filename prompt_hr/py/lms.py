import frappe
import json
from prompt_hr.py.utils import validate_hash

# ? FUNCTION TO START QUIZ RITUALS WITH VALIDATION AND HASH CHECK
@frappe.whitelist()
def start_quiz_rituals(phone, password, quiz_id):
    try:
        # ? BUILD FILTERS FOR JOB APPLICANT LOOKUP
        filters = {"phone_number": phone, "custom_active_quiz": 0}

        # ? ENSURE JOB APPLICANT EXISTS BEFORE HASH VALIDATION
        job_applicant = frappe.get_value("Job Applicant", filters, ["name", "job_title"], as_dict=True)
        if not job_applicant:
            return {"error": 1, "message": "Applicant not found or quiz already attempted. Kindly reach out to your point of contact."}

        # ? VALIDATE HASH
        if not validate_hash(hash=password, filters=json.dumps(filters), doctype="Job Applicant"):
            return {"error": 1, "message": "Invalid credentials."}

        # ? FETCH REGISTERED QUIZ FROM JOB OPENING
        registered_quiz = frappe.db.get_value("Job Opening", job_applicant.job_title, "custom_applicable_screening_test")
        if not registered_quiz:
            return {"error": 1, "message": "No screening test assigned to the job opening."}

        # ? CHECK IF QUIZ ID MATCHES THE REGISTERED ONE
        if quiz_id != registered_quiz:
            return {"error": 1, "message": "Quiz ID does not match the registered quiz."}

        # ? SET ACTIVE QUIZ FLAG TO TRUE
        frappe.db.set_value("Job Applicant", job_applicant.name, "custom_active_quiz", 1)
        return True

    except frappe.ValidationError as ve:
        # ? HANDLE VALIDATION ERRORS CLEANLY
        return {"error": 1, "message": str(ve)}

    except Exception as e:
        # ? LOG UNEXPECTED ERRORS FOR DEBUGGING
        frappe.log_error(f"start_quiz_rituals: {e}")
        return {"error": 1, "message": "Unexpected error. Please try again."}

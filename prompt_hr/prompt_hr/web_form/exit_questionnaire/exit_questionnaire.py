import frappe
import json
from prompt_hr.py.utils import get_hr_managers_by_company, send_notification_email


def get_context(context):
    # ? USED FOR WEB FORM PAGE CONTEXT (IF ANY)
    pass


# ? FUNCTION TO FETCH EXIT INTERVIEW QUESTIONS FOR AN EMPLOYEE
@frappe.whitelist()
def fetch_interview_questions(employee=None):
    # ? GET THE CURRENT LOGGED-IN USER
    user = frappe.session.user

    # ? CHECK IF USER IS HR OR ADMIN
    roles = frappe.get_roles(user)
    is_hr_or_admin = any(role in ['S - HR Director (Global Admin)', 'Administrator'] for role in roles)

    # ? IF NOT HR/ADMIN, ONLY ALLOW ACCESS TO OWN QUESTIONS
    if not is_hr_or_admin:
        if not employee:
            employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if employee != frappe.db.get_value("Employee", {"user_id": user}, "name"):
            frappe.throw("You are not authorized to fetch questions for another employee.")

    if not employee:
        frappe.throw("Employee not provided and no employee linked to the current user.")

    # ? FETCH THE QUIZ LINKED TO THIS EMPLOYEE'S EXIT INTERVIEW
    quiz = frappe.db.get_value("Exit Interview", {"employee": employee}, "custom_resignation_quiz")

    if not quiz:
        frappe.throw(f"No quiz found for employee {employee}.")

    # ? FETCH ALL QUESTIONS ASSOCIATED WITH THE QUIZ
    questions = frappe.get_all("LMS Quiz Question", filters={"parent": quiz}, fields=["question", "question_detail"])

    return questions


# ? FUNCTION TO SAVE RESPONSES FROM THE EXIT QUESTIONNAIRE WEB FORM
@frappe.whitelist()
def save_response(employee, response):
    # ? DESERIALIZE JSON STRING TO PYTHON OBJECT
    try:
        response = json.loads(response)
    except Exception as e:
        frappe.throw(f"Invalid response format: {e}")

    # ? CHECK PERMISSIONS: HR, ADMIN, OR SELF
    user = frappe.session.user
    roles = frappe.get_roles(user)
    if not ("S - HR Director (Global Admin)" in roles or user == "Administrator"):
        linked_emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if employee != linked_emp:
            frappe.throw("You are not authorized to submit responses.")

    # ? FETCH EXIT INTERVIEW DOCUMENT
    exit_doc = frappe.get_all("Exit Interview", filters={"employee": employee}, fields=["name"])
    if not exit_doc:
        frappe.throw(f"Exit Interview not found for employee: {employee}")
    
    exit_doc_name = exit_doc[0].name
    doc = frappe.get_doc("Exit Interview", exit_doc_name)

    # ? CLEAR EXISTING RESPONSES
    doc.custom_questions = []

    # ? ADD EACH NEW RESPONSE
    for entry in response:
        question_id = entry.get("question")
        answer = entry.get("answer")

        if not question_id:
            continue

        doc.append("custom_questions", {
            "question": question_id,
            "answer": answer
        })

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # ? NOTIFY HR MANAGERS
    hr_managers = get_hr_managers_by_company(doc.company)
    send_notification_email(
        doctype="Exit Interview",
        docname=doc.name,
        recipients=hr_managers,
        notification_name="Exit Questionnaire Form Submission"
    )

    return {"status": "success", "message": "Responses saved successfully."}


# ? FUNCTION TO CHECK USER ROLE AND GET LINKED EMPLOYEE (IF ANY)
@frappe.whitelist()
def check_user_role_and_employee():
    user = frappe.session.user
    roles = frappe.get_roles(user)
    is_hr_or_admin = any(role in ['HR', 'Administrator'] for role in roles)

    employee = None
    if not is_hr_or_admin:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")

    return {
        "is_hr_or_admin": is_hr_or_admin,
        "employee": employee
    }

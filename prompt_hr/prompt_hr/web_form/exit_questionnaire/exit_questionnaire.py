import frappe
import json
from prompt_hr.py.utils import get_hr_managers_by_company, send_notification_email


def get_context(context):
    # ? USED FOR WEB FORM PAGE CONTEXT (IF ANY)
    pass


# ? FUNCTION TO FETCH EXIT INTERVIEW QUESTIONS FOR AN EMPLOYEE
@frappe.whitelist()
def fetch_interview_questions(employee=None):
    user = frappe.session.user
    is_hr_or_admin = check_user_role_and_employee().get("is_hr_or_admin")
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

    for question in questions:
        question_data  = frappe.get_all(
            "LMS Question",
            {"name": question.question, "type": "Open Ended", "custom_input_type": ["is", "set"]},
            ["custom_input_type", "custom_multi_checkselect_options"]
        )
        if question_data:
            question["input_type"] = question_data[0].custom_input_type
            if question_data[0].custom_multi_checkselect_options:
                question["multi_checkselect_options"] = question_data[0].custom_multi_checkselect_options.split("\n")
        else:
            question["input_type"] = None

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
    is_hr_or_admin = check_user_role_and_employee().get("is_hr_or_admin")
    if not is_hr_or_admin:
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
        question_detail = frappe.db.get_value("LMS Question", question_id, "question")
        answer = entry.get("answer")
        if not question_id:
            continue

        doc.append("custom_questions", {
            "question": question_detail,
            "question_name": question_id,
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


# ? FUNCTION TO CHECK IF CURRENT USER IS HR/ADMIN AND GET LINKED EMPLOYEE IF NOT
@frappe.whitelist()
def check_user_role_and_employee():
    """
    CHECKS IF THE LOGGED-IN USER HAS HR OR ADMIN ROLES.
    IF NOT, RETURNS THE LINKED EMPLOYEE RECORD (IF ANY).

    RETURNS:
        dict: {
            "is_hr_or_admin": bool,  # True if user is HR/Admin
            "employee": str or None   # Employee name if user is not HR/Admin
        }
    """

    #! GET CURRENT LOGGED-IN USER
    user = frappe.session.user

    #! DEFINE ROLES THAT ARE CONSIDERED HR OR ADMIN
    HR_ADMIN_ROLES = {
        "S - HR Leave Approval",
        "S - HR leave Report",
        "S - HR L6",
        "S - HR L5",
        "S - HR L4",
        "S - HR L3",
        "S - HR L2",
        "S - HR L1",
        "S - HR Director (Global Admin)",
        "S - HR L2 Manager",
        "S - HR Supervisor (RM)",
        "System Manager"
    }

    #! FETCH ALL ROLES OF THE USER
    user_roles = set(frappe.get_roles(user))

    #? CHECK IF USER IS ADMIN OR HAS ANY HR/ADMIN ROLE
    is_hr_or_admin = user == "Administrator" or not HR_ADMIN_ROLES.isdisjoint(user_roles)

    employee = None
    #? IF USER IS NOT HR/ADMIN, GET LINKED EMPLOYEE
    if not is_hr_or_admin:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")

    #! RETURN RESULT
    return {
        "is_hr_or_admin": is_hr_or_admin,
        "employee": employee
    }

import frappe
from prompt_hr.py.utils import get_hr_managers_by_company,send_notification_email

def get_context(context):
	# do your magic here
	pass

# ! prompt_hr.prompt_hr.web_form.exit_questionnaire.exit_questionnaire.fetch_interview_questions
@frappe.whitelist()
def fetch_interview_questions(employee=None):
    # ? GET THE CURRENT LOGGED-IN USER
    user = frappe.session.user
    
    # ? CHECK IF USER IS HR OR ADMIN
    roles = frappe.get_roles(user)
    is_hr_or_admin = any(role in ['HR Manager', 'Administrator'] for role in roles)

    # ? IF THE USER IS NEITHER HR NOR ADMIN, ALLOW THEM TO FETCH ONLY THEIR OWN QUESTIONS
    if not is_hr_or_admin:
        # ? IF THE EMPLOYEE IS NOT PROVIDED, FETCH THE EMPLOYEE LINKED TO THE CURRENT SESSION USER
        if not employee:
            employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
        # ? ENSURE THE CURRENT USER IS ALLOWED TO ACCESS THEIR OWN EMPLOYEE RECORD
        if employee != frappe.db.get_value("Employee", {"user_id": user}, "name"):
            frappe.throw("You are not authorized to fetch questions for another employee.")

    if not employee:
        frappe.throw("Employee not provided and no employee linked to the current user.")
    
    # ? FETCHING THE QUIZ RELATED TO THE EMPLOYEE
    quiz = frappe.db.get_value("Exit Interview", {"employee": employee}, "custom_resignation_quiz")

    if not quiz:
        frappe.throw(f"No quiz found for employee {employee}.")

    # ? FETCH ALL QUESTIONS ASSOCIATED WITH THAT QUIZ
    questions = frappe.get_all("LMS Quiz Question", filters={"parent": quiz}, fields=["question", "question_detail"])

    return questions



# ? FUNCTION TO SAVE RESPONSES FROM THE EXIT QUESTIONNAIRE WEB FORM
# ! prompt_hr.prompt_hr.web_form.exit_questionnaire.exit_questionnaire.save_response
@frappe.whitelist()
def save_response(employee, response):
	import json

	# ? DESERIALIZE THE JSON STRING INTO PYTHON LIST OF DICTS
	try:
		response = json.loads(response)
	except Exception as e:
		frappe.throw(f"Invalid response format: {e}")

	# ? CHECK USER ROLE PERMISSIONS
	if not (frappe.session.user == "Administrator" or "HR Manager" in frappe.get_roles()):
		frappe.throw("You are not authorized to submit responses.")

	# ? FETCH THE EXIT INTERVIEW DOCUMENT FOR THE EMPLOYEE
	exit_doc = frappe.get_all("Exit Interview", filters={"employee": employee}, fields=["name"])
	if not exit_doc:
		frappe.throw(f"Exit Interview not found for the selected employee.", {employee})
	
	exit_doc_name = exit_doc[0].name
	doc = frappe.get_doc("Exit Interview", exit_doc_name)

	# ? CLEAR ANY EXISTING RESPONSES IN THE CHILD TABLE
	doc.questions = []

	# ? APPEND NEW RESPONSES TO THE CHILD TABLE
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

	hr_managers = get_hr_managers_by_company(doc.company)

	send_notification_email(doctype="Exit Interview", docname=doc.name, recipients=hr_managers, notification_name="Exit Questionnaire Form Submission")

	return {"status": "success", "message": "Responses saved successfully."}


@frappe.whitelist()
def check_user_role_and_employee():
    # ? GET THE CURRENT LOGGED-IN USER
    user = frappe.session.user
    
    # ? CHECK IF USER IS HR OR ADMIN
    roles = frappe.get_roles(user)
    
    # ? RETURN IF THE USER IS HR OR ADMIN
    is_hr_or_admin = any(role in ['HR', 'Administrator'] for role in roles)
    
    # ? GET THE EMPLOYEE LINKED TO THE USER (IF ANY)
    employee = None
    if not is_hr_or_admin:
        # ? FOR NON-HR/ADMIN, FETCH THE SESSION EMPLOYEE
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")	
		
    
    return {'is_hr_or_admin': is_hr_or_admin, 'employee': employee}

import frappe
import json
from prompt_hr.py.utils import validate_hash
import json
import frappe
import re
from frappe import _, safe_decode
from frappe.model.document import Document
from frappe.utils import cstr, comma_and, cint
from fuzzywuzzy import fuzz
from lms.lms.doctype.course_lesson.course_lesson import save_progress
from lms.lms.utils import (
	generate_slug,
)
from binascii import Error as BinasciiError
from frappe.utils.file_manager import safe_b64decode
from frappe.core.doctype.file.utils import get_random_filename

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

# ! prompt_hr.py.lmsquiz_summary
@frappe.whitelist()
def quiz_summary(quiz, results, phone_number=None, password=None):

	score = 0
	results = results and json.loads(results)
	is_open_ended = False
	percentage = 0

	quiz_details = frappe.db.get_value(
		"LMS Quiz",
		quiz,
		["total_marks", "passing_percentage", "lesson", "course"],
		as_dict=1,
	)

	score_out_of = quiz_details.total_marks

	for result in results:
		question_details = frappe.db.get_value(
			"LMS Quiz Question",
			{"parent": quiz, "question": result["question_name"]},
			["question", "marks", "question_detail", "type"],
			as_dict=1,
		)

		result["question_name"] = question_details.question
		result["question"] = question_details.question_detail
		result["marks_out_of"] = question_details.marks

		if question_details.type != "Open Ended":
			correct = result["is_correct"][0]
			for point in result["is_correct"]:
				correct = correct and point
			result["is_correct"] = correct
			result["marks"] = question_details.marks if correct else 0
			score += result["marks"]
		else:
			result["is_correct"] = 0
			is_open_ended = True

		result["answer"] = re.sub(
			r'<img[^>]*src\s*=\s*["\'](?=data:)(.*?)["\']',
			_save_file,
			result["answer"]
		)

	percentage = (score / score_out_of) * 100 if score_out_of else 0

	job_applicant = None
	if phone_number and password:
		job_applicant = frappe.db.get_value("Job Applicant", {"phone_number": phone_number}, "name")
		if not job_applicant:
			frappe.throw(_("Job Applicant not found."))

		from prompt_hr.py.utils import validate_hash
		filters = {"phone_number": phone_number, "custom_active_quiz": 1}
		if not validate_hash(hash=password, filters=json.dumps(filters), doctype="Job Applicant"):
			frappe.throw(_("Invalid credentials."))

	submission = frappe.new_doc("LMS Quiz Submission")
	submission.update({
		"quiz": quiz,
		"result": results,
		"score": score,
		"score_out_of": score_out_of,
		"member": frappe.session.user,
		"percentage": percentage,
		"passing_percentage": quiz_details.passing_percentage,
		"custom_job_applicant": job_applicant,
	})
	submission.save(ignore_permissions=True)

	if (
		percentage >= quiz_details.passing_percentage
		and quiz_details.lesson
		and quiz_details.course
	) or not quiz_details.passing_percentage:
		save_progress(quiz_details.lesson, quiz_details.course)

	return {
		"score": score,
		"score_out_of": score_out_of,
		"submission": submission.name,
		"pass": percentage >= quiz_details.passing_percentage,
		"percentage": percentage,
		"is_open_ended": is_open_ended,
	}

def _save_file(match):
	data = match.group(1).split("data:")[1]
	headers, content = data.split(",")
	mtype = headers.split(";", 1)[0]

	if isinstance(content, str):
		content = content.encode("utf-8")
	if b"," in content:
		content = content.split(b",")[1]

	try:
		content = safe_b64decode(content)
	except BinasciiError:
		frappe.flags.has_dataurl = True
		return f'<img src="#broken-image" alt="{get_corrupted_image_msg()}"'

	if "filename=" in headers:
		filename = headers.split("filename=")[-1]
		filename = safe_decode(filename).split(";", 1)[0]

	else:
		filename = get_random_filename(content_type=mtype)

	_file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"decode": False,
			"is_private": False,
		}
	)
	_file.save(ignore_permissions=True)
	file_url = _file.unique_url
	frappe.flags.has_dataurl = True

	return f'<img src="{file_url}"'


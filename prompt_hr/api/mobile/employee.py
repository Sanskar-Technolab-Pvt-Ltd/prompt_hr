# ! prompt_hr.api.mobile.employee.list
# ? GET EMPLOYEE PROFILE LIST
import frappe


@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        # ? GET EMPLOYEE LIST
        employee_list = frappe.get_list(
            "Employee",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Employee",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False,
        )
        total_count = len(total_names)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Employee List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee List Loaded Successfully!",
            "data": employee_list,
            "count": total_count,
        }


# ! prompt_hr.api.mobile.employee.get
# ? GET EMPLOYEE PROFILE DETAILS


@frappe.whitelist()
def get(name):
    try:
        # ? Check if employee exists
        employee_exists = frappe.db.exists("Employee", name)
        if not employee_exists:
            frappe.throw(f"Employee: {name} does not exist!", frappe.DoesNotExistError)

        # ? Get the employee doc
        employee = frappe.get_doc("Employee", name)

        # ? Build the structured response
        employee_info = {
            "full_name": employee.employee_name,
            "employee_number": employee.name,
            "gender": employee.gender,
            "date_of_Birth": employee.date_of_birth,
            "date_of_joining": employee.date_of_joining,
            "blood_group": employee.blood_group,
            "city": employee.custom_village_city,
        }

        education_details = []
        experience_details = []
        for ed in employee.education:
            education_details.append(
                {
                    "school_institute": ed.school_univ,
                    "university_board": ed.custom_university_board,
                    "qualification": ed.qualification,
                    "level": ed.level,
                    "year_of_passing": ed.year_of_passing,
                    "class_per": ed.class_per,
                    "maj_opt_subj": ed.maj_opt_subj,
                }
            )

        for exp in employee.external_work_history:
            experience_details.append(
                {
                    "company_name": exp.company_name,
                    "designation": exp.designation,
                    "salary": exp.salary,
                    "address": exp.address,
                    "contact": exp.contact,
                    "total_experience": exp.total_experience,
                    "custom_working_duration": exp.custom_working_duration,
                }
            )

        education_experience_details = {
            "education_details": education_details,
            "experience_details": experience_details,
        }

        company_info = {
            "company": employee.company,
            "department": employee.department,
            "designation": employee.designation,
            "employment_type": employee.employment_type,
            "work_location": employee.custom_work_location,
            "attendance_capture_schema": employee.custom_attendance_capture_scheme,
            "notice_period": employee.notice_number_of_days,
            "shift": employee.default_shift,
            "branch": employee.branch,
            "grade": employee.grade,
            "reports_to": (
                frappe.db.get_value("Employee", employee.reports_to, "employee_name")
                if employee.reports_to
                else ""
            ),
        }

        contact_info = {
            "mobile": employee.cell_number,
            "work_mobile_no": employee.custom_work_mobile_no,
            "personal_email": employee.personal_email,
            "company_email": employee.company_email,
            "emergency_contact_name": employee.person_to_be_contacted,
            "emergency_phone": employee.emergency_phone_number,
            "relation": employee.relation,
        }

        salary_info = {
            "cost_to_company": employee.ctc,
            "payroll_cost_center": employee.payroll_cost_center,
            "pan_number": employee.pan_number,
            "aadhar_number": employee.custom_aadhaar_number,
            "name_as_per_aadhar": employee.custom_name_as_per_aadhaar,
            "uan_number": employee.custom_uan_number,
            "esi_number": employee.custom_esi_number,
            "esic_ip_number": employee.custom_esic_ip_number,
            "salary_mode": employee.salary_mode,
            "bank_name": employee.bank_name,
            "bank_ac_no": employee.bank_ac_no,
            "ifsc_code": employee.ifsc_code,
            "micr_code": employee.micr_code,
            "iban": employee.iban,
            "passport_number": employee.passport_number,
        }

        settings = {
            "enable_push_notifications": True,
        }

    except Exception as e:
        frappe.log_error("Error While Getting Employee Profile Details", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Profile Loaded Successfully!",
            "data": {
                "employee_information": employee_info,
                "education_experience_details": education_experience_details,
                "company_information": company_info,
                "contact_information": contact_info,
                "salary_information": salary_info,
                "settings": settings,
            },
        }


# ! prompt_hr.api.mobile.employee.get_fields
# ? GET LIST OF CHANGEABLE EMPLOYEE FIELDS WITH OLD VALUES
@frappe.whitelist()
def get_fields(employee=None):
    try:
        if not employee:
            frappe.throw("Employee is required to fetch changeable fields.")
        emp_id = employee
        # ? FETCH EMPLOYEE COMPANY
        company = frappe.db.get_value("Employee", emp_id, "company")
        if not company:
            frappe.throw("Employee company not found")

        # ? GET ABBRs FROM HR SETTINGS
        prompt_abbr, indifoss_abbr = frappe.db.get_value(
            "HR Settings", None, ["custom_prompt_abbr", "custom_indifoss_abbr"]
        )

        # ? GET FULL COMPANY NAMES
        abbr_to_name = {
            "prompt": frappe.db.get_value("Company", {"abbr": prompt_abbr}, "name"),
            "indifoss": frappe.db.get_value("Company", {"abbr": indifoss_abbr}, "name"),
        }

        # ? MAP COMPANY TO ALLOWED FIELDS TABLE
        company_map = {
            abbr_to_name["prompt"]: "custom_employee_changes_allowed_fields_for_prompt",
            abbr_to_name[
                "indifoss"
            ]: "custom_employee_changes_allowed_fields_for_indifoss",
        }

        parentfield = company_map.get(company)
        if not parentfield:
            frappe.throw(
                "There are currently no personal details you're allowed to update. Please contact HR."
            )

        # ? GET FIELD LABELS
        allowed_fields = frappe.get_all(
            "Employee Changes Allowed Fields",
            filters={"parentfield": parentfield},
            fields=["field_label"],
        )
        field_labels = [f.field_label for f in allowed_fields]

        if not field_labels:
            frappe.throw(
                "There are currently no personal details you're allowed to update. Please contact HR."
            )

        # ? GET FIELD METADATA
        fields_meta = frappe.get_all(
            "DocField",
            filters={"parent": "Employee", "label": ["in", field_labels]},
            fields=["fieldname", "label", "fieldtype", "options"],
            ignore_permissions=True,
        )

        # ? ATTACH CURRENT VALUES
        fields = []
        emp_doc = frappe.get_doc("Employee", emp_id)
        for f in fields_meta:
            fields.append(
                {
                    "fieldname": f.fieldname,
                    "label": f.label,
                    "fieldtype": f.fieldtype,
                    "options": f.options,
                    "old_value": emp_doc.get(f.fieldname) or "",
                }
            )

        if not fields:
            frappe.throw("No fields available for update at the moment.")

    except Exception as e:
        frappe.log_error("While Fetching Employee Changeable Fields", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": [],
        }
    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee changeable fields loaded successfully!",
            "data": fields,
            "count": len(fields),
        }


# ! prompt_hr.api.mobile.employee_changes.create_request
# ? CREATE EMPLOYEE CHANGE REQUEST
@frappe.whitelist()
def create_field_changes(
    employee=None, field_name=None, field_label=None, new_value=None, old_value=None
):
    try:

        if not employee or not field_name or not field_label or new_value is None:
            frappe.throw(
                "Employee, field name, field label, new value and old value are required."
            )
        employee_id = employee

        existing_value = frappe.db.get_value(
            "Employee", {"name": employee_id, "status": "Active"}, field_name
        )

        # ? VALIDATIONS
        if not new_value or len(new_value) < 1:
            frappe.throw("New value cannot be empty.")

        if existing_value == new_value:
            frappe.throw("No changes detected.")

        # if str(existing_value).strip() != str(old_value).strip():
        #     frappe.throw(
        #         f"Mismatch in your old value and existing value. Kindly try again and if issue persists contact System Manager. Current: {existing_value}, Provided: {old_value}"
        #     )

        # ? CHECK PENDING REQUEST
        if frappe.db.exists(
            "Employee Profile Changes Approval Interface",
            {
                "employee": employee_id,
                "field_name": field_name,
                "approval_status": "Pending",
            },
        ):
            frappe.throw("A change request for this field is already pending.")

        # ? GET COMPANY
        company = frappe.db.get_value("Employee", employee_id, "company")
        if not company:
            frappe.throw("No company associated with this employee.")

        company_abbr = frappe.db.get_value("Company", company, "abbr")
        prompt_abbr, indifoss_abbr = frappe.db.get_value(
            "HR Settings", None, ["custom_prompt_abbr", "custom_indifoss_abbr"]
        )

        if company_abbr not in [prompt_abbr, indifoss_abbr]:
            frappe.throw("This feature is not available for the current company.")

        # ? GET ALLOWED FIELD CONFIG
        parentfield = (
            "custom_employee_changes_allowed_fields_for_prompt"
            if company_abbr == prompt_abbr
            else "custom_employee_changes_allowed_fields_for_indifoss"
        )

        allowed_field = frappe.db.get_value(
            "Employee Changes Allowed Fields",
            filters={"parentfield": parentfield, "field_label": field_label},
            fieldname=["field_label", "permission_required"],
        )
        if not allowed_field:
            frappe.throw(f"The field '{field_label}' is not allowed to be changed.")

        # ? VALIDATE USER
        user = frappe.db.get_value("Employee", employee_id, "user_id")
        if not user:
            frappe.throw("No user associated with this employee.")

        # ? DECIDE FLOW BASED ON PERMISSION
        if allowed_field[1] == 1:  # Approval required
            changes = {
                "doctype": "Employee Profile Changes Approval Interface",
                "field_name": field_name,
                "old_value": old_value,
                "new_value": new_value,
                "employee": employee_id,
                "approval_status": "Pending",
                "date_of_changes_made": frappe.utils.nowdate(),
            }
            doc = frappe.get_doc(changes)
            doc.insert(ignore_permissions=True)
            frappe.db.commit()

            response_data = doc.as_dict()
            msg = "Your change request has been submitted for approval. It will be processed shortly."

        else:  # Direct apply
            frappe.db.set_value("Employee", employee_id, field_name, new_value)
            frappe.db.commit()

            response_data = {
                "field_name": field_name,
                "field_label": field_label,
                "old_value": old_value,
                "new_value": new_value,
                "employee": employee_id,
                "applied_directly": True,
            }
            msg = "Employee details have been updated successfully."

    except Exception as e:
        frappe.log_error("While Creating Employee Change Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }
    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": msg,
            "data": response_data,
        }


from frappe.utils import get_url


@frappe.whitelist()
def profile_form_url():
    try:
        url = get_url()
        hr_setting = frappe.get_doc("HR Settings", "HR Settings")

        # ? GET CURRENT USER
        user = frappe.session.user
        sid = frappe.session.sid

        # ? FETCH EMPLOYEE NAME LINKED TO USER
        employee_name = frappe.db.get_value("Employee", {"user_id": user}, "name")

        if not employee_name:
            raise Exception("No Employee record linked with current user.")

        if hr_setting.custom_web_form_link:
            # ? REPLACE {name} WITH ACTUAL EMPLOYEE NAME
            final_url = f"{url}{hr_setting.custom_web_form_link.format(name=employee_name)}?sid={sid}"
        else:
            final_url = f"{url}/app?sid={sid}"

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Profile URL", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Profile URL Loaded Successfully!",
            "data": final_url,
        }


from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import frappe
from frappe.utils import get_url


@frappe.whitelist()
def resignation_form_url():
    try:
        base_url = get_url()
        hr_setting = frappe.get_doc("HR Settings", "HR Settings")
        user = frappe.session.user
        sid = frappe.session.sid

        # ? GET LINKED EMPLOYEE
        employee_name = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if not employee_name:
            frappe.throw("No Employee record linked with current user.")

      
        path = f"/app/employee"

        path += f"/{employee_name}"
        # ? PARSE EXISTING URL TO MERGE QUERY PARAMS SAFELY
        url_parts = urlparse(urljoin(base_url, path))
        query_dict = parse_qs(url_parts.query)

        # ? ADD MANDATORY QUERY PARAMS
        query_dict["sid"] = [sid]
        query_dict["raise_resignation"] = ["1"]

        # ? REBUILD QUERY STRING SAFELY
        new_query = urlencode(query_dict, doseq=True)
        final_url = urlunparse(url_parts._replace(query=new_query))

    except Exception as e:
        frappe.log_error("Error While Getting Resignation URL", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }
    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Resignation URL Loaded Successfully!",
            "data": final_url,
        }

from frappe.auth import LoginManager
@frappe.whitelist()
def employee_details_url():
    try:
        url = get_url()
        hr_setting = frappe.get_doc("HR Settings", "HR Settings")

        # Ensure we have the current user
        user = frappe.session.user
        # Generate a new session for the user
        sid = frappe.session.sid

        if hr_setting.custom_employee_details_url:
            final_url = f"{url}{hr_setting.custom_employee_details_url}?sid={sid}"
        else:
            final_url = f"{url}/app?sid={sid}"

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee Details URL", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Details URL Loaded Successfully!",
            "data": final_url,
        }

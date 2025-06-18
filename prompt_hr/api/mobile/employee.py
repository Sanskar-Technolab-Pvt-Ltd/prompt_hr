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
        total_names = frappe.get_all(
            "Employee",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Employee List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee List Loaded Successfully!",
            "data": employee_list,
            "count": total_count        
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
        }

        company_info = {
            "company": employee.company,
            "department": employee.department,
            "designation": employee.designation,
            "branch": employee.branch,
            "grade": employee.grade,
            "reports To": frappe.db.get_value("Employee", employee.reports_to, "employee_name") if employee.reports_to else "",
            "employment_type": employee.employment_type,
        }

        contact_info = {
            "mobile": employee.cell_number,
            "personal_email": employee.personal_email,
            "company_email": employee.company_email,
        }

        salary_info = {
            "cost_to_company": employee.ctc,
            "payroll_cost_center": employee.payroll_cost_center,
            "pan_number": employee.pan_number,
            "esic_ip_number": employee.custom_esi_number,
            "salary_mode": employee.salary_mode,
            "bank_name": employee.bank_name,
            "bank_ac_no": employee.bank_ac_no,
            "ifsc_code": employee.ifsc_code,
            "MICR Code": employee.micr_code,
            "IBAN": employee.iban
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
                "company_information": company_info,
                "contact_information": contact_info,
                "salary_information": salary_info,
                "settings" : settings
            },
        }

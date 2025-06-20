import frappe

# ! prompt_hr.api.mobile.salary_slip.list
# ? GET SALARY SLIP LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
    payroll_period=None,
):
    try:
        
        filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or [])

        # Get Payroll Period Dates
        start_date = frappe.db.get_value("Payroll Period", payroll_period, "start_date") if payroll_period else None
        end_date = frappe.db.get_value("Payroll Period", payroll_period, "end_date") if payroll_period else None

        if start_date and end_date:
            filters.append(["start_date", ">=", start_date])
            filters.append(["end_date", "<=", end_date])
        
        # ? GET SALARY SLIP LIST
        salary_slip_list = frappe.get_list(
            "Salary Slip",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_all(
            "Salary Slip",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Salary Slip List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Salary Slip List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Salary Slip List Loaded Successfully!",
            "data": salary_slip_list,
            "count": total_count        
        }
        
        
# ! prompt_hr.api.mobile.salary_slip.get
# ? GET SALARY SLIP DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF SALARY SLIP  DOC EXISTS OR NOT
        salary_slip_exists = frappe.db.exists("Salary Slip", name)

        # ? IF SALARY SLIP  DOC NOT
        if not salary_slip_exists:
            frappe.throw(
                f"Salary Slip: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET SALARY SLIP  DOC
        salary_slip = frappe.get_doc("Salary Slip", name).as_dict()
        salary_slip = get_data_from_employee(salary_slip)
      
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Salary Slip Loaded Successfully!",
            "data": salary_slip,
        }
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Salary Slip Detail", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

        
@frappe.whitelist()
def download(name):
    try:
        # ? CHECK IF SALARY SLIP DOC EXISTS OR NOT
        salary_slip_exists = frappe.db.exists("Salary Slip", name)

        # ? IF SALARY SLIP DOC NOT EXISTS
        if not salary_slip_exists:
            frappe.local.response["message"] = {
            "success": False,
            "message": "Salary Slip: {name} Does Not Exists!",
            "data": None,
        }
        child_table_field_name = None
        company = frappe.db.get_value("Salary Slip", name, "company")
        if company == "Prompt Equipments Pvt. ltd":
            child_table_field_name = "custom_print_format_table_prompt"
        if company == "Indifoss Analytical Pvt Ltd":
            child_table_field_name = "custom_print_format_table_indifoss"
        
        if child_table_field_name:
            for item in frappe.get_single("HR Settings").get(child_table_field_name):
                if item.document == "Salary Slip":
                    print_format = item.print_format_document
                    break
                else:
                    frappe.local.response["message"] = {
                        "success": False,
                        "message": "Please Set Print Format for Salary Slip in ERPNext HR Settings",
                        "data": None,
                    }
            site_url = frappe.utils.get_url()
            pdf_link = f"{site_url}/api/method/frappe.utils.print_format.download_pdf?doctype=Salary%20Slip&name={name}&format={print_format}&no_letterhead=1&_lang=en"
            return {
                "success": True,
                "message": "Salary Slip PDF Link Generated Successfully!",
                "data": pdf_link,
            }
        else:
            frappe.local.response["message"] = {
                "success": False,
                "message": "Please Set Print Format for Salary Slip in ERPNext HR Settings or Check the Company Name",
                "data": None,
            }

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Downloading Salary Slip", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

def get_data_from_employee(salary_slip):
    employee = frappe.get_doc("Employee", salary_slip["employee"])
    salary_slip["employment_type"] = employee.employment_type or ""
    salary_slip["pan"] = employee.pan_number or ""
    salary_slip["aadhar"] = employee.custom_aadhaar_number or ""
    salary_slip["uan"] = employee.custom_uan_number or ""
    salary_slip["monthly_salary"] = employee.ctc or ""
    salary_slip["designation"] = employee.designation or ""
    salary_slip["bank_account_number"] = employee.bank_ac_no or ""
    salary_slip["mobile_number"] = get_mobile_number(salary_slip, employee)
    salary_slip["email_id"] = get_email_id(salary_slip, employee)
    
    return salary_slip

def get_mobile_number(salary_slip, employee):
    if employee.custom_preferred_mobile == "Personal Mobile No":
        return employee.cell_number or ""
    elif employee.custom_preferred_mobile == "Work Mobile No":
        return employee.custom_work_mobile_no or ""
    else:
        return employee.custom_preferred_mobile_no or employee.cell_number or employee.custom_work_mobile_no or ""

def get_email_id(salary_slip, employee):
    if employee.prefered_contact_email == "Personal Email":
        return employee.personal_email or ""
    elif employee.prefered_contact_email == "Company Email":
        return employee.company_email or ""
    elif employee.prefered_contact_email == "User ID":
        return employee.user_id or ""
    else:
        return employee.company_email if employee.company_email else employee.personal_email or employee.user_id or ""


# Get Payroll List
@frappe.whitelist()
def get_payroll_period_list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
    payroll_period=None,
):
    try:
        payroll_list = frappe.get_list(
            "Payroll Period",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Payroll Period List Loaded Successfully!",
            "data": payroll_list
        }
    
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Payroll Period List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Payroll Period List: {str(e)}",
            "data": None,
        }

       
import frappe
from datetime import datetime, date


# ! prompt_hr.api.mobile.employee_checkin.list
# ? GET EMPLOYEE CHECKIN LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","employee_name","log_type","time"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        filters = frappe.parse_json(filters) if filters else []
        or_filters = frappe.parse_json(or_filters) if or_filters else []
        fields = frappe.parse_json(fields) if fields else ["*"]

        has_date_filter = False
        date_fields = ['time', 'creation', 'modified', 'date']
        
        # Check if any existing filters contain date/time fields
        for filter_item in filters:
            if hasattr(filter_item, '__len__') and len(filter_item) >= 1:
                field_name = str(filter_item[0])
                if any(date_field in field_name.lower() for date_field in date_fields):
                    has_date_filter = True
                    break
        
        # If no date filter exists, add today's filter
        if not has_date_filter:
            today = date.today()
            today_start = f"{today} 00:00:00"
            today_end = f"{today} 23:59:59"
            
            # Add filter for today's records
            filters.append(["time", ">=", today_start])
            filters.append(["time", "<=", today_end])
            
        # ? GET EMPLOYEE CHECKIN LIST
        employee_checkin_list = frappe.get_list(
            "Employee Checkin",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Employee Checkin",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee Checkin List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Employee Checkin List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Checkin List Loaded Successfully!",
            "data": employee_checkin_list,
            "count": total_count        
        }
        


# ! prompt_hr.api.mobile.employee_checkin.get
# ? GET EMPLOYEE CHECKIN   DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF EMPLOYEE CHECKIN  DOC EXISTS OR NOT
        employee_checkin_exists = frappe.db.exists("Employee Checkin", name)

        # ? IF EMPLOYEE CHECKIN  DOC NOT
        if not employee_checkin_exists:
            frappe.throw(
                f"Employee Checkin: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET EMPLOYEE CHECKIN  DOC
        employee_checkin = frappe.get_doc("Employee Checkin", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee Checkin Detail", str(e))
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
            "message": "Employee Checkin Loaded Successfully!",
            "data": employee_checkin,
        }
        
      
        
# ! prompt_hr.api.mobile.employee_checkin.create
# ? CREATE EMPLOYEE CHECKIN   
   
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "log_type": "Log Type",
            

        }

        # ? CHECK IF THE MANDATORY FIELD IS FILLED OR NOT IF NOT THROW ERROR
        for field, field_name in mandatory_fields.items():
            if (
                not args.get(field)
                or args.get(field) == "[]"
                or args.get(field) == "[{}]"
            ):
                frappe.throw(
                    f"Please Fill {field_name} Field!",
                    frappe.MandatoryError,
                )

        # ? IF 'time' NOT PROVIDED, USE CURRENT TIME
        if not args.get("time"):
            args["time"] = frappe.utils.now_datetime()
        print(args.get("latitude"))
        
        print(type(args.get("latitude")))
        # After mandatory field validation
        if args.get("latitude"):
            args["latitude"] = frappe.utils.flt(args["latitude"])
        if args.get("longitude"):
            args["longitude"] = frappe.utils.flt(args["longitude"])
        print(args.get("latitude"))
        print(type(args.get("latitude")))
        

        # ? FETCH EMPLOYEE DOC
        emp_doc = frappe.get_doc("Employee", args.get("employee"))    
        
        # ? CREATE EMPLOYEE CHECKIN DOC
        employee_checkin_doc = frappe.get_doc({
            "doctype": "Employee Checkin",
            **args
        })
        
        # ? IGNORE PERMISSIONS IF SCHEME MATCHES
        allowed_schemes = [
            "Biometric-Mobile Checkin-Checkout",
            "Mobile-Web Checkin-Checkout",
            "Geofencing"
        ]
         # ? VALIDATE SCHEME
        if emp_doc.custom_attendance_capture_scheme not in allowed_schemes:
            frappe.throw(
                f"Employee {emp_doc.name} is not allowed for Checkin. "
            )

        # Ignore permissions (because scheme is already validated)
        employee_checkin_doc.flags.ignore_permissions = True

        employee_checkin_doc.insert()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        # frappe.log_error("Error While Creating Employee Checkin", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"{str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Checkin Created Successfully!",
            "data": employee_checkin_doc,
        }
        
        
        
@frappe.whitelist()
def checking_log(
    filters=None,
    or_filters=None,
    fields=["name","employee","employee_name","log_type","time"],
    order_by="creation desc",  # Default to latest
    limit_page_length=1,       # Default to 1 record
    limit_start=0,
):
    try:
        filters = frappe.parse_json(filters) if filters else []
        or_filters = frappe.parse_json(or_filters) if or_filters else []
        fields = frappe.parse_json(fields) if fields else ["*"]

        has_date_filter = False
        date_fields = ['time', 'creation', 'modified', 'date']
        
        # Check if any existing filters contain date/time fields
        for filter_item in filters:
            if hasattr(filter_item, '__len__') and len(filter_item) >= 1:
                field_name = str(filter_item[0])
                if any(date_field in field_name.lower() for date_field in date_fields):
                    has_date_filter = True
                    break
        
        # If no date filter exists, add today's filter
        if not has_date_filter:
            today = date.today()
            today_start = f"{today} 00:00:00"
            today_end = f"{today} 23:59:59"
            
            # Add filter for today's records
            filters.append(["time", ">=", today_start])
            filters.append(["time", "<=", today_end])

        # Fetch latest check-in
        employee_checkin_list = frappe.get_list(
            "Employee Checkin",
            filters=filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=int(limit_page_length),
            limit_start=int(limit_start),
        )


    except Exception as e:
        frappe.log_error("Error While Getting Employee Checkin List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Employee Checkin List: {str(e)}",
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Latest Employee Checkin Loaded Successfully!",
            "data": employee_checkin_list,
        }
        
        
# ! prompt_hr.api.mobile.employee_checkin.check_button_status
# ? CHECK IF EMPLOYEE IS ALLOWED FOR CHECKIN BUTTON

@frappe.whitelist()
def check_button_status(employee):
    try:
        # ? FETCH EMPLOYEE DOC
        emp_doc = frappe.get_doc("Employee", employee)

        # ? DEFINE ALLOWED SCHEMES
        allowed_schemes = [
            "Biometric-Mobile Checkin-Checkout",
            "Mobile-Web Checkin-Checkout",
            "Geofencing"
        ]

        # ? CHECK IF SCHEME IS ALLOWED
        button_visible = emp_doc.custom_attendance_capture_scheme in allowed_schemes

        frappe.local.response["message"] = {
            "success": True,
            "button_visible": button_visible,
            "employee": emp_doc.name,
            # "scheme": emp_doc.custom_attendance_capture_scheme,
        }

    except Exception as e:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "button_visible": False,
            # "message": f"{str(e)}",
            "employee": employee,
        }
        
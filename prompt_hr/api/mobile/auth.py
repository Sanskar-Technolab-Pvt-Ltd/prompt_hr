import frappe


# ! prompt_hr.api.mobile.auth.login
# ? API FOR LOGIN WITH AUTH TOKEN AND ALL
@frappe.whitelist(allow_guest=1)
def login(email, password):
    try:
        # ? INITIALIZE VARIABLES
        work_location = None
        
        # ? SETUP THE LOGIN MANAGER
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=email, pwd=password)
        login_manager.post_login()

        # ? GET USER DETAILS AND GENERATE API KEY AND SECRET IF NEEDED
        user = frappe.get_doc("User", frappe.session.user)
        user_roles = [roles.get("role") for roles in user.get("roles")]

        # ? GET IF EMPLOYEE EXISTS FOR THE USER
        employee = (
            frappe.db.get_value("Employee", {"user_id": user.name}, "name") or None
        )
        
        if employee:
            emp_doc = frappe.get_doc("Employee", employee)
            work_location = emp_doc.get("custom_work_location")
        else:
            frappe.throw(
                "Employee record not found for the user. Please contact HR or system administrator.",
                frappe.DoesNotExistError,
            )
                    

        sales_person = sales_person = (
            frappe.db.get_value("Sales Person", {"employee": employee}, "name")
            if employee
            else None
        )

        # ? GET SESSION DETAILS
        sid = frappe.session.sid
        csrf_token = frappe.sessions.get_csrf_token()
        
        
        if user.get("api_secret"):
            try:
                api_secret = user.get_password("api_secret")
            except frappe.ValidationError:
                # Encryption key mismatch, regenerate
                api_secret = generate_keys(user)
        else:
            api_secret = generate_keys(user)

        api_key = user.get("api_key")
        auth_token = f"token {api_key}:{api_secret}"
        username = user.get("username")
        email = user.get("email")

        # ? IF ANY DATA IS MISSING, RAISE ERROR
        if not all([sid, csrf_token, api_key, api_secret, username, email]):
            frappe.throw(
                "Oops, Something Went Wrong!",
                frappe.DoesNotExistError,
            )

        # Get default company: user default, then global fallback
        company = frappe.defaults.get_user_default("Company")
        if not company:
            company = frappe.db.get_single_value("Global Defaults", "default_company")


            
    except frappe.DoesNotExistError as e:
        # ? HANDLE DOES NOT EXIST ERROR
        frappe.log_error("API Login DoesNotExistError", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    except frappe.exceptions.AuthenticationError as e:
        # ? HANDLE AUTHENTICATION ERROR
        frappe.log_error("API Login AuthenticationError", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": "Invalid Email Or Password. Please Try Again.",
            "data": None,
        }

    else:
        # ? LOGIN SUCCESSFUL
        frappe.local.response["message"] = {
            "success": True,
            "message": "Login successful!",
            "data": {
                "sid": sid,
                "csrf_token": csrf_token,
                "api_key": api_key,
                "api_secret": api_secret,
                "auth_token": auth_token,
                "username": username,
                "email": email,
                "user_roles":user_roles,
                "employee": employee,
                "work_location":work_location,
                "sales_person": sales_person,
                "company":company
            },
        }


# ? GENERATE SECRET KEY FOR USER
def generate_keys(user):
    api_secret = frappe.generate_hash(length=15)
    if not user.api_key:
        user.api_key = frappe.generate_hash(length=15)
    user.api_secret = api_secret
    user.save(ignore_permissions=True)
    frappe.db.commit()

    return api_secret

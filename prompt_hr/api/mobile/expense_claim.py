import frappe
from frappe.utils.file_manager import save_file


# ! prompt_hr.api.mobile.expense_claim.list
# ? GET EXPENSE CLAIM LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","employee_name","approval_status","custom_type","workflow_state"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        fields = frappe.parse_json(fields)

        # Ensure employee is included in the fields
        if "employee" not in fields:
            fields.append("employee")

        # Get current user's employee ID
        current_user = frappe.session.user
        current_employee = frappe.get_value("Employee", {"user_id": current_user}, "name")

        # Get all expense claims
        expense_claim_list = frappe.get_list(
            "Expense Claim",
            filters=filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        for claim in expense_claim_list:
            claim_employee = claim.get("employee")

            # Tagging logic
            if claim_employee == current_employee:
                claim["request"] = "My Request"
            else:
                reports_to = frappe.get_value("Employee", claim_employee, "reports_to")
                if reports_to == current_employee:
                    claim["request"] = "Team Request"
                else:
                    claim["request"] = "Other"

            # Fetch the first expense item
            claim_name = claim.get("name")
            if claim_name:
                expenses = frappe.get_all(
                    "Expense Claim Detail",
                    filters={"parent": claim_name},
                    fields=[
                        "expense_date",
                        "expense_type",
                        "amount",
                        "idx"
                    ],
                    order_by="idx asc",
                    limit=1
                )

                if expenses:
                    claim.update({
                        "expense_date": expenses[0].get("expense_date"),
                        "expense_type": expenses[0].get("expense_type"),
                        "amount": expenses[0].get("amount")
                    })
        

        
        # ? GET TOTAL COUNT
        total_names = frappe.get_list(
            "Expense Claim",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False  # Ensures count respects user permissions
        )
        total_count = len(total_names)

    except Exception as e:
        frappe.log_error("Error While Getting Expense Claim List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Expense Claim List: {str(e)}",
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Expense Claim List Loaded Successfully!",
            "data": expense_claim_list,
            "count": total_count
        }

# ! prompt_hr.api.mobile.expense_claim.get
# ? GET EXPENSE CLAIM DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF EXPENSE CLAIM  DOC EXISTS OR NOT
        expense_claim_exists = frappe.db.exists("Expense Claim", name)

        # ? IF EXPENSE CLAIM  DOC NOT
        if not expense_claim_exists:
            frappe.throw(
                f"Expense Claim: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET EXPENSE CLAIM  DOC
        expense_claim = frappe.get_doc("Expense Claim", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Expense Claim Detail", str(e))
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
            "message": "Expense Claim Loaded Successfully!",
            "data": expense_claim,
        }
        
      


# # ! prompt_hr.api.mobile.expense_claim.create
# # ? CREATE EXPENSE CLAIM   
       
     
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            # "expense_approver": "Expense Approver",
            "custom_type": "Type",
            "approval_status": "Approval Status",
            "expenses" : "Expenses"
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

        # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("expenses"):
            args["expenses"] = frappe.parse_json(args.get("expenses"))
        if args.get("advances"):
            args["advances"] = frappe.parse_json(args.get("advances"))
                
        # ? CREATE EXPENSE CLAIM DOC
        expense_claim_doc = frappe.get_doc({
            "doctype": "Expense Claim",
            **args
        })
        expense_claim_doc.insert()
        frappe.db.commit()
        
        # ? HANDLE MULTIPLE FILE UPLOADS
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Expense Claim",
                expense_claim_doc.name,
                is_private=0
            )
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Expense Claim", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Creating Expense Claim: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Expense Claim Created Successfully!",
            "data": expense_claim_doc,
        }
                 
     
         
         
# ! prompt_hr.api.mobile.expense_claim.update
# ? UPDATE EXPENSE CLAIM

@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("Expense Claim 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        expense_claim_doc = frappe.get_doc("Expense Claim", args.get("name"))

        # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("expenses"):
            args["expenses"] = frappe.parse_json(args.get("expenses"))
        if args.get("advances"):
            args["advances"] = frappe.parse_json(args.get("advances"))

        # ? UPDATE MAIN FIELDS AND CHILD TABLES
        for key, value in args.items():
            if key != "name":
                expense_claim_doc.set(key, value)

        expense_claim_doc.save()
        frappe.db.commit()

        # ? OPTIONAL: HANDLE FILE UPLOADS IF NEEDED
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Expense Claim",
                expense_claim_doc.name,
                is_private=0
            )
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating Expense Claim", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Updating Expense Claim: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Expense Claim Updated Successfully!",
            "data": expense_claim_doc,
        }




# ! prompt_hr.api.mobile.expense_claim.delete
# ? DELETE EXPENSE CLAIM

@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("Expense Claim 'name' is required to delete the document", frappe.MandatoryError)
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("Expense Claim", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)      

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("Expense Claim", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting Expense Claim", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Deleting Expense Claim: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Expense Claim Deleted Successfully!",
            "data": {"name": name},
        }
         
         

# ! prompt_hr.api.mobile.expense_claim.get_data_from_expense_claim_as_per_grade

@frappe.whitelist()
def get_vehicle_details(employee, company):
    try:
        # ? GET TRAVEL BUDGET FOR COMPANY
        travel_budget = frappe.db.get_value("Travel Budget", {"company": company}, "name")
        if not travel_budget:
            frappe.throw(f"No Travel Budget found for company {company}", frappe.DoesNotExistError)

        # ? GET EMPLOYEE GRADE
        grade = frappe.db.get_value("Employee", employee, "grade")
        if not grade:
            frappe.throw(f"Employee grade not found for employee {employee}", frappe.DoesNotExistError)

        # ? GET COMMUTE OPTIONS BASED ON GRADE AND TRAVEL BUDGET
        commute_options = frappe.get_all(
            "Local Commute Details",
            filters={"parent": travel_budget, "grade": grade},
            fields=["mode_of_commute", "type_of_commute","attachment_mandatory"],
        )

        # ? ORGANIZE BY MODE OF COMMUTE
        data = {"Public": [], "Non Public": []}
        for option in commute_options:
            mode = option.mode_of_commute.strip().title()
            if mode in data:
                 data[mode].append({
                    "type_of_vehicle": option.type_of_commute,
                    "attachment_mandatory": option.attachment_mandatory
                })
                

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Fetching Commute Options", str(e))
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
            "message": "Commute options fetched successfully!",
            "data": data,
        }         
        
        



@frappe.whitelist()
def field_visit_list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        # ? GET EXPENSE CLAIM LIST
        field_visit_list = frappe.get_list(
            "Field Visit",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Field Visit",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Field Visit List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Field Visit List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Field Visit List Loaded Successfully!",
            "data": field_visit_list,
            "count": total_count        
        }        
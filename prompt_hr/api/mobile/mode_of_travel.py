import frappe

@frappe.whitelist()
def get(employee=None, company=None):
    try:
        # ? VALIDATE INPUTS
        if not employee:
            frappe.throw("Employee is required")
        if not company:
            frappe.throw("Company is required")

        # ? GET TRAVEL BUDGET REFERENCE
        travel_budget = frappe.db.get_value("Travel Budget", {"company": company}, "name")
        if not travel_budget:
            frappe.throw(f"Travel Budget not found for Company: {company}")

        # ? GET EMPLOYEE GRADE
        grade = frappe.db.get_value("Employee", employee, "grade")
        if not grade:
            frappe.throw(f"Grade not found for Employee: {employee}")

        # ? FETCH TRAVEL MODES FROM BUDGET TABLE
        travel_modes = frappe.get_all(
            "Travel Mode Table",
            filters={
                "parent": travel_budget,
                "grade": grade,
            },
            fields=["mode_of_travel","attachment_mandatory"]
        )

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Travel Modes", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Travel Modes: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Travel Modes Loaded Successfully!",
            "data": travel_modes if travel_modes else [],
        }

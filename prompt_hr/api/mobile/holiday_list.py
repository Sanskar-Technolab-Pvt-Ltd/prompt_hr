import frappe
import re

def remove_html_tags(text):
    return re.sub('<.*?>', '', text)

@frappe.whitelist()
def get(company, employee, leave_type):
    try:
        # Validate input
        if not company:
            frappe.throw("Company is required")
        options = []
        festival_holiday_lists = frappe.get_all(
            "Festival Holiday List",
            filters={"company": company},
            fields=["name"]
        )

        if employee:
            leave_application = frappe.get_all(
                "Leave Application",
                filters={"employee": employee, "leave_type": leave_type},
                or_filters = {
                    "workflow_state": "Confirmed",
                    "custom_leave_status": "Confirmed",
                },
                fields=["from_date"],
                pluck="from_date"
            )
        else:
            leave_application = []

        for festival_holiday_list in festival_holiday_lists:
            holidays = frappe.get_all(
                "Holiday",
                filters={
                    "parent": festival_holiday_list.name,
                    "custom_is_optional_festival_leave": 1
                },
                fields=["name", "holiday_date", "description"],
                order_by="holiday_date"
            )
            for holiday in holidays:
                if leave_application:
                    if holiday.holiday_date in leave_application:
                        continue
                    label = f"{remove_html_tags(holiday.description) or holiday.name} ({frappe.utils.format_date(holiday.holiday_date, 'dd-MM-yyyy')})"
                options.append({"label": label, "value": label, "holiday_date": holiday.holiday_date})
    except Exception as e:
         # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Holiday List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Holiday List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Holiday List Loaded Successfully!",
            "data": options,
        }
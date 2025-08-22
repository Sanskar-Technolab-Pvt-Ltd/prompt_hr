# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months, format_date

def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "ip_number",
			"label": "IP Number",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "ip_name",
			"label": "IP Name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "total_no_of_days",
			"label": "No of days for which wages paid/payable during the month",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "total_monthly_wages",
			"label": "Total Monthly Wages",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "reason",
			"label": "Reason Code for Zero Working Days",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname":"last_working_day",
			"label": "Last Working Day",
			"fieldtype": "Date",
			"width": 150
		}
	]

def get_data(filters):
    #! SET FROM AND TO DATE FROM FILTERS
    from_date = getdate(filters.get("from_date")) or getdate()
    to_date = getdate(filters.get("to_date")) or add_months(from_date, 1)

    #! BASE SALARY SLIP FILTERS
    salary_filters = {
        "start_date": from_date,
        "end_date": to_date,
        "docstatus": 1
    }

    if filters.get("company"):
        salary_filters["company"] = filters.get("company")

    #! FETCH SALARY SLIPS
    slip_datas = frappe.get_all(
        "Salary Slip",
        filters=salary_filters,
        fields=["*"],
        order_by="creation desc"
    )

    data = []

    #! LOOP THROUGH SALARY SLIPS
    for slip_data in slip_datas:
        employee = frappe.get_doc("Employee", slip_data.employee)
        relieving_date = getdate(employee.relieving_date) if employee.relieving_date else None

        #! DEFAULT REASON CODE
        reason_code = ""
        last_working_day = ""

        if slip_data.payment_days == 0:
            #? REASON 1 - ZERO WORKING DAYS
            reason_code = "1"
            slip_data.gross_pay = 0
            slip_data.payment_days = 0

        elif relieving_date and from_date <= relieving_date <= to_date:
            #? REASON 2 - RELIEVED THIS MONTH
            reason_code = "2"
            last_working_day = relieving_date

        #! FILTER BY SALARY STRUCTURE ASSIGNMENT AND BASE CONDITION
        if slip_data.custom_salary_structure_assignment:
            salary_structure_assignment = frappe.get_doc(
                "Salary Structure Assignment",
                slip_data.custom_salary_structure_assignment
            )

            # ? SHOW IN REPORT ONLY IF EMPLOYEE BASE SALARY <= 21000
            if salary_structure_assignment.base <= 21000:
                # ? INITIAL GROSS PAY
                gross_pay = slip_data.gross_pay
                salary_details  = frappe.get_all(
                    "Salary Detail",
                    filters={
                        "parent": slip_data.name,
                        "parentfield": "earnings",
                    },
                    fields=["salary_component", "amount"]
                )
                for salary_detail in salary_details:
                    salary_component = frappe.get_doc("Salary Component", salary_detail.salary_component)
                    # ? SEPARATE LEAVE ENCASHMENT AMOUNT FROM TOTAL GROSS WAGES
                    if salary_component.custom_salary_component_type == "Leave Encashment":
                        gross_pay -= salary_detail.amount

                row = {
                    "ip_number": employee.custom_esic_ip_number,
                    "ip_name": slip_data.employee_name,
                    "total_no_of_days": slip_data.payment_days,
                    "total_monthly_wages": round(gross_pay),
                    "reason": reason_code,
                    "last_working_day": last_working_day
                }

                data.append(row)

    return data

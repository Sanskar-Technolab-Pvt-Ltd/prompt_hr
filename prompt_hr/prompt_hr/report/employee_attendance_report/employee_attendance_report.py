import frappe
from frappe.utils import get_first_day, get_last_day, today

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date") or get_first_day(today())
    to_date = filters.get("to_date") or get_last_day(today())

    columns = [
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Data", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Job Title", "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
        {"label": "Business Unit", "fieldname": "custom_business_unit", "fieldtype": "Link", "options": "Business Unit", "width": 150},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 100},
        {"label": "Sub Department", "fieldname": "sub_department", "fieldtype": "Data", "width": 100},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 100},
        {"label": "Cost Center", "fieldname": "cost_center", "fieldtype": "Data", "width": 100},
        {"label": "Reporting Manager", "fieldname": "reports_to", "fieldtype": "Link", "options": "Employee", "width": 100},
        {"label": "Days Present", "fieldname": "present", "fieldtype": "Int", "width": 100},
        {"label": "Days Absent", "fieldname": "absent", "fieldtype": "Int", "width": 100},
        {"label": "Break Duration", "fieldname": "break_duration", "fieldtype": "Float", "width": 120},
        {"label": "Paid Leave Taken", "fieldname": "paid_leave", "fieldtype": "Int", "width": 120},
        {"label": "Unpaid Leave Taken", "fieldname": "unpaid_leave", "fieldtype": "Int", "width": 120},
        {"label": "Penalized Paid Leaves", "fieldname": "penalized_paid", "fieldtype": "Int", "width": 150},
        {"label": "Penalized Unpaid Leaves", "fieldname": "penalized_unpaid", "fieldtype": "Int", "width": 150},
        {"label": "Weekly Offs", "fieldname": "weekly_off", "fieldtype": "Int", "width": 100},
        {"label": "Holidays", "fieldname": "holiday", "fieldtype": "Int", "width": 100},
        {"label": "Worked During Week-Offs/Holidays", "fieldname": "worked_on_offs", "fieldtype": "Int", "width": 200},
    ]

    employees = frappe.get_all("Employee",
        fields=[
            "name", "employee_name", "department", "designation", "custom_business_unit",
            "custom_subdepartment", "custom_work_location", "payroll_cost_center",
            "employee_number", "reports_to"
        ]
    )

    # Load holidays
    all_holiday_dates = {
        h["holiday_date"]
        for h in frappe.get_all("Holiday", fields=["holiday_date"])
    }

    data = []

    for emp in employees:
        attendance_records = frappe.get_all("Attendance",
            filters={
                "employee": emp.name,
                "attendance_date": ["between", [from_date, to_date]],
                "docstatus": 1
            },
            fields=["*"]
        )
        penalty_records = frappe.get_all("Employee Penalty", filters={
                "employee": emp.name,
                "penalty_date": ["between", [from_date, to_date]],
            },
            fields=["*"])

        summary = {
            "present": 0,
            "absent": 0,
            "break_duration": 0,
            "paid_leave": 0,
            "unpaid_leave": 0,
            "penalized_paid": 0,
            "penalized_unpaid": 0,
            "weekly_off": 0,
            "holiday": 0,
            "worked_on_offs": 0
        }

        if penalty_records:
            for penalty_record in penalty_records:
                if penalty_record.deduct_earned_leave:
                    summary["penalized_paid"] += penalty_record.deduct_earned_leave
                if penalty_record.deduct_leave_without_pay:
                    summary["penalized_unpaid"] += penalty_record.deduct_leave_without_pay

        for record in attendance_records:
            status = (record.status or "").lower().strip()

            if status == "present":
                if record.attendance_date not in all_holiday_dates:
                    summary["present"] += 1
                else:
                    summary["worked_on_offs"] += 1

            elif status == "absent":
                summary["absent"] += 1

            elif status == "on leave":
                if record.leave_type:
                    leave_type_doc = frappe.get_doc("Leave Type", record.leave_type)
                    if leave_type_doc.is_lwp:
                        summary["unpaid_leave"] += 1
                    else:
                        summary["paid_leave"] += 1

        holiday_dates = frappe.get_all(
            "Holiday",
            filters={"holiday_date": ["between", [from_date, to_date]]},
            fields=["name", "weekly_off"]
        )	

        for holiday in holiday_dates:
            if holiday.weekly_off:
                summary["weekly_off"] += 1
            else:
                summary["holiday"] += 1

        row = {
            "employee": emp.employee_number,
            "employee_name": emp.employee_name,
            "designation": emp.designation,
            "custom_business_unit": emp.custom_business_unit,
            "department": emp.department,
            "sub_department": emp.custom_subdepartment,
            "location": emp.custom_work_location,
            "cost_center": emp.payroll_cost_center,
            "reports_to": emp.reports_to or "",
            **summary
        }

        data.append(row)

    return columns, data

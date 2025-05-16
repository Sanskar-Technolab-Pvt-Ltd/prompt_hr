# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt


import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data

def get_columns():
    return [
        {"label": "Emp No", "fieldname": "emp_no", "fieldtype": "Data", "width": 90},
        {"label": "Emp Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 130},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 100},
        {"label": "Productline", "fieldname": "productline", "fieldtype": "Data", "width": 120},
        {"label": "KPI (%)", "fieldname": "kpi_score", "fieldtype": "Percent", "width": 90},
        {"label": "Behavioural (%)", "fieldname": "behavioural_score", "fieldtype": "Percent", "width": 90},
        {"label": "HOD (%)", "fieldname": "hod_score", "fieldtype": "Percent", "width": 90},
        {"label": "CEO (%)", "fieldname": "ceo_score", "fieldtype": "Percent", "width": 90},
        {"label": "Directors (%)", "fieldname": "directors_score", "fieldtype": "Percent", "width": 90},
        {"label": "Final Performance (%)", "fieldname": "final_score", "fieldtype": "Percent", "width": 120},
        {"label": "Top Management Remarks", "fieldname": "top_remarks", "fieldtype": "Small Text", "width": 200},
        {"label": "KPI Remarks", "fieldname": "kpi_remarks", "fieldtype": "Small Text", "width": 200},
        {"label": "Behaviour Remarks", "fieldname": "behaviour_remarks", "fieldtype": "Small Text", "width": 200},
    ]

# Function to fetch data from the Appraisal doctype
# and calculate the final performance score based on weights
# and other criteria
def get_data():
    appraisal_docs = frappe.get_all("Appraisal", filters={"docstatus": 1}, fields=["*"])
    
    for doc in appraisal_docs:
        # Fetching employee details
        employee = frappe.get_doc("Employee", doc.get("employee"))
        doc["emp_no"] = employee.employee_number
        doc["employee_name"] = employee.employee_name
        doc["department"] = employee.department
        doc["productline"] = ""

        # Ensure scores have default values
        doc["kpi_score"] = doc.get("kpi_score") or 0
        doc["behavioural_score"] = doc.get("behavioural_score") or 0
        doc["hod_score"] = doc.get("hod_score") or 0
        doc["ceo_score"] = doc.get("ceo_score") or 0
        doc["directors_score"] = doc.get("directors_score") or 0

        # Remarks
        doc["top_remarks"] = doc.get("top_remarks") or ""
        doc["kpi_remarks"] = doc.get("kpi_remarks") or ""
        doc["behaviour_remarks"] = doc.get("behaviour_remarks") or ""

        # Calculate final performance based on weights
        weights = {
            "kpi_score": 0.6,
            "behavioural_score": 0.1,
            "hod_score": 0.1,
            "ceo_score": 0.1,
            "directors_score": 0.1
        }
        final = 0
        for key, weight in weights.items():
            final += (doc.get(key) or 0) * weight
        doc["final_score"] = round(final, 2)

    return appraisal_docs



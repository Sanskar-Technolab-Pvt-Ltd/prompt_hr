# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_link_to_form

def execute(filters=None):
	#! MAIN FUNCTION TO EXECUTE THE REPORT
	columns = get_columns()
	data = get_data(filters or {})
	return columns, data


def get_columns():
	#! DEFINE COLUMNS FOR THE REPORT
	return [
		{"label": "Expense Claim", "fieldname": "expense_claim_name", "fieldtype": "Link", "options": "Expense Claim", "width": 220},
		{"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Expense Claim", "width": 220},
		{"label": "Start Date", "fieldname": "start_date", "fieldtype": "Date", "width": 150},
		{"label": "Start Time", "fieldname": "start_time", "fieldtype": "Time", "width": 150},
		{"label": "End Date", "fieldname": "end_date", "fieldtype": "Date", "width": 150},
		{"label": "End Time", "fieldname": "end_time", "fieldtype": "Time", "width": 150},
		{"label": "Expense Type", "fieldname": "expense_claim_type", "fieldtype": "Link","options":"Expense Claim Type", "width": 200},
		{"label": "Mode of Journey", "fieldname": "mode_of_journey", "fieldtype": "Data", "width": 160},
		{"label": "From Location", "fieldname": "from_location", "fieldtype": "Data", "width": 160},
		{"label": "To Location", "fieldname": "to_location", "fieldtype": "Data", "width": 160},
		{"label": "City", "fieldname": "city", "fieldtype": "Link", "options": "Village or City", "width": 200},
		{"label": "Field Visit", "fieldname": "field_visit", "fieldtype": "Data", "width": 200},
		{"label": "Service Call", "fieldname": "service_call", "fieldtype": "Data", "width": 200},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 200},
		{"label": "Tour Visit", "fieldname": "tour_visit", "fieldtype": "Data", "width": 150},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 150},
		{"label": "Sanctioned Amount", "fieldname": "sanctioned_amount", "fieldtype": "Currency", "width": 150},
		{"label": "Supporting Document", "fieldname": "supporting_document", "fieldtype": "Data", "width": 150},
		{"label": "Remark", "fieldname": "remark", "fieldtype": "Data", "width": 200},
		{"label": "Status", "fieldname": "workflow_state", "fieldtype": "Data", "width": 150},
	]


def get_data(filters):
	data = []

	#? FIRST FILTER EMPLOYEES BASED ON GRADE AND DESIGNATION
	filtered_employees = get_filtered_employees(filters)
	
	#? HANDLE FILTERS FOR PARENT DOCTYPE (EXPENSE CLAIM)
	expense_claim_filters = {}

	if filters.get("employee"):
		expense_claim_filters["employee"] = filters["employee"]
	elif filtered_employees is not None:
		# If we have grade/designation filters, limit to filtered employees
		if not filtered_employees:
			return []  # No employees match the criteria
		expense_claim_filters["employee"] = ["in", filtered_employees]
		
	if filters.get("company"):
		expense_claim_filters["company"] = filters["company"]

	# ? HANDLE DEPARTMENT AS MULTISELECT
	if filters.get("department"):
		departments = filters.get("department")
		if isinstance(departments, list):
			expense_claim_filters["department"] = ["in", departments]
		else:
			expense_claim_filters["department"] = departments

	if filters.get("status"):
		expense_claim_filters["docstatus"] = filters["status"]

	#? FETCH MATCHING EXPENSE CLAIM DOCS WITH META FIELDS
	expense_claim_docs = frappe.get_all(
		"Expense Claim",
		fields=["name", "employee", "workflow_state"],
		filters=expense_claim_filters
	)

	if not expense_claim_docs:
		return []

	#? PREPARE MAPPING FOR PARENT DATA
	claim_meta_map = {
		d.name: {
			"employee": d.employee,
			"workflow_state": d.workflow_state
		}
		for d in expense_claim_docs
	}
	claim_names = list(claim_meta_map)
	#? FILTERS FOR CHILD(EXPENSE CLAIM DETAIL) DOCTYPE
	child_filters = {
		"parent": ["in", claim_names]
	}

	if filters.get("from_date") and filters.get("to_date"):
		child_filters["custom_expense_end_date"] = ["between", [filters["from_date"], filters["to_date"]]]
		child_filters["expense_date"] = ["between", [filters["from_date"], filters["to_date"]]]

	if filters.get("expense_claim_type"):
		child_filters["expense_type"] = filters["expense_claim_type"]

	# ? HANDLE CITY AS MULTISELECT
	if filters.get("city"):
		cities = filters["city"]
		child_filters["custom_city"] = ["in", cities] if isinstance(cities, list) else cities

	#? GET CHILD RECORDS
	child_records = frappe.get_all(
		"Expense Claim Detail",
		fields=[
			"parent", "expense_date", "custom_expense_end_date",
			"custom_expense_start_time", "custom_expense_end_time",
			"expense_type",
			"custom_from_location", "custom_to_location", "custom_city",
			"amount", "sanctioned_amount", "custom_type_of_vehicle",
			"custom_field_visits", "custom_service_calls", "custom_tour_visits", "custom_supporting_document_available", "custom_remark", "custom_customer_details"
		],
		filters=child_filters
	)

	#? HANDLE MULTISELECTS ON PYTHON SIDE
	field_visit_filter = set(filters.get("field_visit", []))
	service_call_filter = set(filters.get("service_call", []))
	tour_visit_filter = set(filters.get("tour_visit", []))
	customer_filter = set(filters.get("customer", []))

	for record in child_records:
		service_calls = {sc.strip() for sc in (record.custom_service_calls or "").split(",") if sc.strip()}
		field_visits = {fv.strip() for fv in (record.custom_field_visits or "").split(",") if fv.strip()}
		tour_visits = {tv.strip() for tv in (record.custom_tour_visits or "").split(", ") if tv.strip()}
		customers_from_service_calls = set(get_customers_from_service_calls(service_calls))
		customers_from_tour_visits = set(get_customers_from_tour_visit(tour_visits))
		normal_customers = {nc.strip() for nc in (record.custom_customer_details or "").split(",") if nc.strip()}
		#? COMBINE ALL CUSTOMERS
		customers = customers_from_service_calls.union(customers_from_tour_visits).union(normal_customers)
		if field_visit_filter and not field_visit_filter & field_visits:
			continue
		if service_call_filter and not service_call_filter & service_calls:
			continue
		if tour_visit_filter and not tour_visit_filter & tour_visits:
			continue
		if customer_filter and not customer_filter & customers:
			continue
		#? MAKE CLICKABLE LINKS
		clickable_service_calls = ", ".join([get_link_to_form("Service Call", sc) for sc in service_calls])
		clickable_field_visits = ", ".join([get_link_to_form("Field Visit", fv) for fv in field_visits])
		clickable_tour_visits = ", ".join([get_link_to_form("Tour Visit", tv) for tv in tour_visits])
		#? USE CUSTOMER NAME IN LINK DISPLAY
		clickable_customers = ", ".join([
			get_link_to_form("Customer", c, frappe.db.get_value("Customer", c, "customer_name"))
			for c in customers
		])
		parent_meta = claim_meta_map.get(record.parent, {})
		data.append({
			"expense_claim_name": record.parent,
			"employee": parent_meta.get("employee"),
			"workflow_state": parent_meta.get("workflow_state"),
			"tour_visit": clickable_tour_visits,
			"start_date": record.expense_date,
			"end_date": record.custom_expense_end_date,
			"start_time": record.custom_expense_start_time,
			"end_time": record.custom_expense_end_time,
			"expense_claim_type": record.expense_type,
			"from_location": record.custom_from_location,
			"to_location": record.custom_to_location,
			"city": record.custom_city,
			"field_visit": clickable_field_visits,
			"service_call": clickable_service_calls,
			"customer": clickable_customers,
			"amount": record.amount,
			"sanctioned_amount": record.sanctioned_amount,
			"supporting_document": "YES" if record.custom_supporting_document_available else "NO",
			"remark": record.custom_remark,
			"mode_of_journey": record.custom_type_of_vehicle
		})

	return data


def get_filtered_employees(filters):
	"""
	Filter employees based on grade and designation
	Returns None if no grade/designation filters are applied
	Returns list of employee IDs if filters are applied
	"""
	employee_filters = {}
	
	# Check if grade or designation filters are applied
	if not (filters.get("grade") or filters.get("designation")):
		return None
	
	if filters.get("grade"):
		employee_filters["grade"] = filters["grade"]
	
	if filters.get("designation"):
		employee_filters["designation"] = filters["designation"]
	
	# Get filtered employees
	employees = frappe.get_all(
		"Employee",
		fields=["name"],
		filters=employee_filters
	)
	
	return [emp.name for emp in employees]


def get_customers_from_service_calls(service_call_ids):
	#! HELPER TO FETCH CUSTOMER NAMES FOR GIVEN SERVICE CALL IDs
	customers = []
	for sc_id in service_call_ids:
		customer = frappe.db.get_value("Service Call", sc_id, "customer")
		if customer:
			customers.append(customer)
	return customers

def get_customers_from_tour_visit(tour_visit_ids):
	customers = []
	#! HELPER TO FETCH CUSTOMER NAMES FOR GIVEN TOUR VISIT IDs
	for tv_id in tour_visit_ids:
		customer = frappe.db.get_value("Tour Visit", tv_id, "customer")
		if customer:
			customers.append(customer)

	return customers


@frappe.whitelist()
def get_employee_grades(doctype, txt, searchfield, start, page_len, filters):
	"""
	Get employee grades without SQL
	"""
	employee_filter = filters.get('employee') if filters else None
	
	if employee_filter:
		# Get specific employee's grade
		employee_doc = frappe.get_doc("Employee", employee_filter)
		grade = employee_doc.grade
		
		if grade and txt.lower() in grade.lower():
			return [[grade]]
		else:
			return []
	else:
		print(frappe.db.get_all("Employee Grade", fields=["name"], pluck="name"))
		# Return all Employee Grade options (default behavior)
		return [[d] for d in frappe.db.get_all("Employee Grade", fields=["name"], pluck="name")]


@frappe.whitelist()
def get_employee_designations(doctype, txt, searchfield, start, page_len, filters):
	"""
	Get employee designations without SQL
	"""
	employee_filter = filters.get('employee') if filters else None
	
	if employee_filter:
		# Get specific employee's designation
		employee_doc = frappe.get_doc("Employee", employee_filter)
		designation = employee_doc.designation
		
		if designation and txt.lower() in designation.lower():
			return [[designation]]
		else:
			return []
	else:
		# Return all Designation options (default behavior)
		return [[d] for d in frappe.db.get_all("Designation", fields=["name"], pluck="name")]

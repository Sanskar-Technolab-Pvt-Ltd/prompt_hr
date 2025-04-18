import frappe
import json
from frappe import _
from frappe.model.workflow import get_workflow, is_transition_condition_satisfied
from frappe.model.document import Document

from frappe.model.workflow import WorkflowStateError 
from frappe.workflow.doctype.workflow.workflow import Workflow

from typing import Union



@frappe.whitelist()
def get_transitions(
	doc: Union[Document, str, dict], workflow: "Workflow" = None, raise_exception: bool = False
) -> list[dict]:
	"""Returns list of possible transitions, combining default role-based and custom user-based transitions"""

	# Convert to doc object
	print(f"\n\n\n\n\n\n\n\n\n\n override successfull{doc}\n\n\n")
	if not isinstance(doc, Document):
		doc = frappe.get_doc(frappe.parse_json(doc))
		doc.load_from_db()

	if doc.is_new():
		return []

	doc.check_permission("read")

	workflow = workflow or get_workflow(doc.doctype)
	current_state = doc.get(workflow.workflow_state_field)

	if not current_state:
		if raise_exception:
			raise WorkflowStateError
		else:
			frappe.throw(_("Workflow State not set"), WorkflowStateError)

	roles = frappe.get_roles()
	transitions = []

	# --- 1. Default Role-based Transitions from Workflow DocType ---
	# for transition in workflow.transitions:
	# 	if transition.state == current_state and transition.allowed in roles:
	# 		if not is_transition_condition_satisfied(transition, doc):
	# 			continue
	# 		transitions.append(transition.as_dict())

	# --- 2. Your Custom User-Based & Criteria-Based Transitions ---
	if frappe.db.exists("Workflow Approval", {"applicable_doctype": doc.doctype}):
		transitions += get_custom_transitions(doc, current_state)

	return transitions


def get_custom_transitions(doc, current_state):
	user = frappe.session.user
	custom_transitions = []

	approvals = frappe.get_all("Workflow Approval", filters={
		"applicable_doctype": doc.doctype
	}, fields=["name"])


	for approval in approvals:
		if not matches_criteria(approval, doc):
			continue
        
        

		children = frappe.get_all("Workflow Approval Hierarchy", filters={
			"parent": approval.name,
			"current_state": current_state
		}, fields=["action", "next_state", "user", "role"])

		for t in children:
			if t.user == user or (t.role and t.role in frappe.get_roles(user)):
				custom_transitions.append({
					"action": t.action,
					"next_state": t.next_state,
					"allowed": t.role or t.user,  # just for display
					"state": current_state
				})

	return custom_transitions


def matches_criteria(rule, doc):
	# Matching all fields one by one, you can make this dynamic later

	#* FETCHING ALL Doctype fieldname from the WORKFLOW APPROVAL CRITERIA CHILD TABLE
	#* and checking if the rule value is not empty
	print(f"\n\n\nmatching creiteria\n\n\n")
	fields = frappe.get_all("Workflow Approval Criteria", filters={
		"parent": rule.name
	}, fields=["field_name", "expected_value"])

	final_fields = {}
	for field in fields:
		if final_fields.get(field.get("field_name")):
			final_fields[field.get("field_name")].append(field.get("expected_value"))
		else:
			final_fields[field.get("field_name")] = [field.get("expected_value")]

	# fields = ["company", "department", "designation", "employment_type",
                # "employee_grade", "product_line", "business_unit", "work_location"]

	for field_name, field_value in final_fields.items():
		rule_value = field_value
		doc_value = doc.get(field_name)
		if rule_value and doc_value not in rule_value:
			return False
	print(f"\n\n\ncriteris match\n\n\n")# Check if the rule value is empt
	return True

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
	for transition in workflow.transitions:
		if transition.state == current_state and transition.allowed in roles:
			if not is_transition_condition_satisfied(transition, doc):
				continue
			transitions.append(transition.as_dict())

	# --- 2. Your Custom User-Based & Criteria-Based Transitions ---
	if frappe.db.exists("Workflow Approval", {"applicable_doctype": doc.doctype}):
		transitions += get_custom_transitions(doc, current_state)

	return transitions


def get_custom_transitions(doc, current_state):
	user = frappe.session.user
	custom_transitions = []

	approvals = frappe.get_all("Workflow Approval", filters={
		"applicable_doctype": doc.doctype
	}, fields=["name", "company"])


	for approval in approvals:
		if not matches_criteria(approval, doc):
			continue
        
        

		children = frappe.get_all("Workflow Approval Transition", filters={
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
	fields = ["company", "department", "designation", "employment_type",
                "employee_grade", "product_line", "business_unit", "work_location"]

	for field in fields:
		rule_value = rule.get(field)
		doc_value = doc.get(field)
		if rule_value and rule_value != doc_value:
			return False
	return True

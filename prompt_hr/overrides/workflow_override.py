import frappe
from frappe import _
from frappe.model.workflow import WorkflowStateError, is_transition_condition_satisfied, get_workflow
from frappe.model.document import Document
from typing import Union
from frappe.workflow.doctype.workflow.workflow import Workflow


@frappe.whitelist()
def custom_get_transitions(
	doc: Union["Document", str, dict], workflow: "Workflow" = None, raise_exception: bool = False
) -> list[dict]:
	""" Overriding this method to add custom logic for workflow transitions. Overrided using MonkeyPatch"""
	from frappe.model.document import Document

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

	transitions = []
	roles = frappe.get_roles()
	user = frappe.session.user
	approval = get_matching_workflow_approval(doc)
	if approval:
		print(f"\n\n  Going with Custom Flow {user}\n\n")
		for transition in approval.workflow_approval_hierarchy:
            
				if transition.allowed_by == "User" and transition.user == user:
					print(f"\n\n User wise \n\n")
					if transition.state == current_state:
						transitions.append(frappe._dict({
							"state": transition.state,
							"action": transition.action,
							"next_state": transition.next_state,
							"allowed_by": transition.allowed_by,
							"allowed": transition.user,
							"allow_self_approval": transition.allow_self_approval,
							"send_email_to_creator": transition.send_email_to_creator,
							"condition": transition.condition,
						}))
				elif transition.allowed_by == "Role" and transition.role in roles:
					print(f"\n\n role wise\n\n")
					if transition.state == current_state:
						transitions.append(frappe._dict({
							"state": transition.state,
							"action": transition.action,
							"next_state": transition.next_state,
							"allowed_by": transition.allowed_by,
							"allowed": transition.role,
							"allow_self_approval": transition.allow_self_approval,
							"send_email_to_creator": transition.send_email_to_creator,
							"condition": transition.condition,
						}))

	else:
		for transition in workflow.transitions:
			if transition.state == current_state and transition.allowed in roles:
				if not is_transition_condition_satisfied(transition, doc):
					continue
				transition_as_dict = transition.as_dict()
				transition_as_dict["allowed_by"] = "Role"	
				# transitions.append(transition.as_dict())
				transitions.append(transition_as_dict)

	return transitions

def custom_has_approval_access(user, doc, transition):
    """ Overriding this method to add custom logic for approval access for workflow transitions. Overrided using MonkeyPatch"""
    if transition.get("allowed_by") == "User":
        return user == transition.get("allowed") or user == "Administrator"
    return user == "Administrator" or transition.get("allow_self_approval") or user != doc.get("owner")


def get_matching_workflow_approval(doc):
    all_approvals = frappe.get_all("Workflow Approval", filters={"applicable_doctype": doc.doctype}, pluck="name")
    for name in all_approvals:
        approval = frappe.get_doc("Workflow Approval", name)
        if all(str(doc.get(c.field_name)).strip() == str(c.expected_value).strip() for c in approval.workflow_approval_criteria):
            return approval
    return None


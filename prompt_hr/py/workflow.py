import frappe

from frappe.model.workflow import get_transitions

# ! prompt_hr.py.workflow.get_workflow_transitions
def get_workflow_transitions(doctype, docname):
    """
    ! FUNCTION: Get unique workflow transition actions for a given document
    ? Logic:
        - Fetch the document
        - Get its transitions
        - Collect only unique actions (avoid duplicates)
    """
    doc = frappe.get_doc(doctype, docname)
    transitions = get_transitions(doc)

    actions = []
    for t in transitions:
        # exclude when self approval is not allowed and user = doc owner
        if not t.get("allow_self_approval", 0) and frappe.session.user == doc.owner:
            continue

        actions.append(t["action"])

    # return only unique actions (order preserved)
    unique_actions = list(dict.fromkeys(actions))

    return unique_actions


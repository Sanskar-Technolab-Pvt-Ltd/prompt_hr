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

    # ? Use set comprehension to keep only unique actions
    unique_actions = {t.action for t in transitions}

    # ? Convert back to list before returning
    return list(unique_actions)

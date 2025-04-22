__version__ = "0.0.1"

from frappe.model import workflow
from prompt_hr.overrides.workflow_override import custom_get_transitions, custom_has_approval_access




workflow.has_approval_access = custom_has_approval_access
workflow.get_transitions = custom_get_transitions


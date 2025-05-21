
from prompt_hr.py.utils import expense_claim_workflow_email

def on_update(doc, method):
    # ? SEND EMAIL NOTIFICATION FOR EXPENSE CLAIM WORKFLOW
    expense_claim_workflow_email(doc)
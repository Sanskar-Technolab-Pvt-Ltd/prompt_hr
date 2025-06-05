import frappe
from frappe.utils import getdate
import frappe.workflow
from prompt_hr.py.utils import (
    send_notification_email,
    expense_claim_and_travel_request_workflow_email,
    get_prompt_company_name,
    get_indifoss_company_name,
)


# ! prompt_hr.py.expense_clain.before_submit
# ? BEFORE SUBMIT EVENT
def before_submit(doc, method):

    # ? UPDATE THE ACTUAL EXPENSE AMOUNT IN CAMPAIGN AND MARKETING PLANNING
    update_amount_in_marketing_planning(doc, method)


def before_save(doc, method):

    # ? CHECK IF EXPENSE CLAIM IS EXCEEDING THE ALLOWED BUDGET
    if doc.expenses:
        validate_attachments_compulsion(doc)
        get_expense_claim_exception(doc)


def on_update(doc, method):

    # ? SHARE DOCUMENT AND SEND NOTIFICATION EMAIL
    expense_claim_and_travel_request_workflow_email(doc)


#  !prompt_marketing.api.hook.doctype.purchase_invoice.update_amount_in_marketing_planning
# ? UPDATE THE ACTUAL EXPENSE AMOUNT IN CAMPAIGN AND MARKETING PLANNING
def update_amount_in_marketing_planning(doc, method):

    # ? IF CAMPAIGN IS LINKED WITH DOCTYPE
    if doc.campaign:

        # ? GET CAMPAIGN DOCUMENT
        campaign_doc = frappe.get_doc("Campaign", doc.campaign)
        if campaign_doc.custom_marketing_plan:

            # ? GET MARKETING PLANNING DOCUMENT IF CAMPAIGN IS LINKED WITH MARKETING PLANNING
            marketing_plan = frappe.get_doc(
                "Marketing Planning", campaign_doc.custom_marketing_plan
            )

            # ? FOR BEFORE SUBMIT METHOD CHECK IF BUDGET IS EXCEEDING THE EXPECTED BUDGET OR NOT
            if method == "before_submit":

                # ? GET CONTROL ACTION ON DOCTYPE
                control_action = get_control_flags(doc, marketing_plan)

                # ? GET CURRENT QUARTER
                current_quarter = quarter_map(campaign_doc.custom_start_date)
                if not current_quarter:
                    return

                # ? VALIDATE THE CURRENT QUARTER IS CLOED OR NOT
                is_quarter_closed(marketing_plan, current_quarter)

                # ? CHECK IF BUDGET EXCEEDES THE EXPECTED BUDGET
                budget_exceeded = is_budget_exceeded(
                    campaign_doc, marketing_plan, current_quarter, doc.total
                )

                # ? IF BUDGET IS EXCEEDING THE EXPECTED BUDGET THEN CHECK THE CONTROL ACTION IN MARKETING PLANNING
                if budget_exceeded and control_action:
                    enforce_budget_control(
                        campaign_doc.custom_campaign_type,
                        current_quarter,
                        marketing_plan,
                        control_action,
                    )

                # ? UPDATE MARKETING PLAN EXPENSE AND REMAINING BUDGET VALUES
                update_marketing_planning_row(
                    doc, method, campaign_doc, marketing_plan, current_quarter
                )

            # ? FOR ON CANCEL METHOD UPDATE VALUES DIRECTLY
            elif method == "on_cancel":
                current_quarter = quarter_map(campaign_doc.custom_start_date)
                if not current_quarter:
                    return

                # ? UPDATE MARKETING PLAN EXPENSE AND REMAINING BUDGET VALUES
                update_marketing_planning_row(
                    doc, method, campaign_doc, marketing_plan, current_quarter
                )


# ? METHOD FOR CONTROL ACTIONS
def enforce_budget_control(campaign, quarter, marketing_plan, action):

    link = ""
    if marketing_plan:
        link = (
            f'<a href="/app/marketing-planning/{marketing_plan.name}" target="_blank">'
            f"{marketing_plan.name}</a>"
        )

    if action == "Stop":
        # ? PREVENT SUBMISSION OF DOCUMENT IF CONTROL ACTION IS STOP
        frappe.throw(
            f"This entry exceeds the allocated budget and cannot be submitted. "
            f"Please review your budget limits in the <b>Expense Planning </b> section of the Marketing Planning document.<br><br>"
            f"<span style='color:red'> Note: Look for the row with Campaign Type: <b>{campaign}</b> and Quarter: <b>{quarter}</b> in Marketing Plan : <b>{link}</b></span>",
            exc=frappe.ValidationError,
        )
    elif action == "Warn":
        # ? WARNING MESSAGE IF CONTROL ACTION IF WARN
        frappe.msgprint(
            f"Warning: This entry exceeds the planned budget. "
            f"Please review the budget in the <b>Expense Planning</b> section of the Marketing Planning document.<br><br>"
            f"Here is the link to the document: {link} <br><br>"
            f"<span style='color:red'> Note: Look for the row with Campaign Type: <b>{campaign}</b> and Quarter: <b>{quarter}</b> in Marketing Plan : <b>{link}</b></span>",
        )


# ? METHOD TO GET CONTROL ACTION SETTINGS FROM MARKETING PLANNING
def get_control_flags(doc, marketing_plan):

    # ? FOR PURCHASE INVOICE
    if doc.doctype == "Purchase Invoice":
        control_enabled = marketing_plan.applicable_on_purchase_invoice
        control_action = (
            marketing_plan.action_if_budget_exceeded_on_pi if control_enabled else None
        )

    # ? FOR EXPENSE CLAIM
    elif doc.doctype == "Expense Claim":
        control_enabled = marketing_plan.applicable_on_expense_claim
        control_action = (
            marketing_plan.action_if_budget_exceeded_on_ec if control_enabled else None
        )

    # ? RETURN CONTROL ACTION
    return control_action


# ? METHOD TO CHECK IF BUDGET EXCEEDS THE EXPECTED BUDGET IN MARKETING PLANNING
def is_budget_exceeded(campaign_doc, marketing_plan, current_quarter, invoice_total):
    for row in marketing_plan.monthly_campaign_planning:
        if (
            row.campaign_type == campaign_doc.custom_campaign_type
            and row.month == current_quarter
        ):
            return (row.actual_expense + invoice_total) > row.expected_budget
    return False


# ? METHOD TO CHECK IF CURRENT QUARTER IS CLOSED IN MARKETING PLANNING DOC
def is_quarter_closed(marketing_plan, current_quarter):

    # ? LOOP ON BUDGET PLANNING TABLE
    for row in marketing_plan.quarter_budget_planning:

        # ? GET THE ROW FOR CURRENT QUARTER
        if row.quarter == current_quarter:

            # ? IF QUARTER IS CLOSED
            if row.quarter_closed:

                # ? THROW ERROR
                frappe.throw(
                    "Transactions are not allowed for quarters marked as <b>Closed</b> in Marketing Planning. "
                    "Please make transactions for current quarter."
                )


# ? METHOD FOR UPDATING ACTUAL EXPENSE IN MARKETING PLANNING CHILD TABLE FOR RELATED ROW
def update_marketing_planning_row(
    doc, method, campaign_doc, marketing_plan, current_quarter
):
    for row in marketing_plan.monthly_campaign_planning:

        # ? FIND THE ROW WITH MATCH OF CAMPAIGN TYPE AND QUARTER
        if (
            row.campaign_type == campaign_doc.custom_campaign_type
            and row.month == current_quarter
        ):

            # ? IF METHOD IS BEFORE SUBMIT ADD GRAND TOTAL IN ACTUAL EXPENSE
            if method == "before_submit":
                row.actual_expense += doc.total

            # ? IF METHOD IS ON CANCEL REMOVE GRAND TOTAL FROM ACTUAL EXPENSE
            elif method == "on_cancel":
                row.actual_expense -= doc.total

            # ? UPDATE REMAINING BUDGET
            row.remaining_budget = row.expected_budget - row.actual_expense

    # ? UPDATE THE QUARTERLY PLANNING TABLE AS WELL
    for q_row in marketing_plan.quarter_budget_planning:

        # ? MATCH THE QUARTER
        if q_row.quarter == current_quarter:

            # ? AGGREGATE ALL ACTUAL EXPENSES FROM MONTHLY ROWS IN THE SAME QUARTER
            total_actual_expense = sum(
                r.actual_expense
                for r in marketing_plan.monthly_campaign_planning
                if r.month == current_quarter
            )

            # ? SET ACTUAL AND REMAINING BUDGETS
            q_row.actual_expense = total_actual_expense
            q_row.remaining_budget = q_row.expected_budget - total_actual_expense
    marketing_plan.save()

    # ? LOG THE ENTRY IN CAMPAIGN LOGS TABLE
    record_expense_log_in_campaign(doc, campaign_doc, method)


def quarter_map(date):

    # ? QUARTER MAPPING WITH MONHTS
    quarter_map = {
        "April": (4, 5, 6),
        "July": (7, 8, 9),
        "October": (10, 11, 12),
        "January": (1, 2, 3),
    }

    # ? GET CURRENT QUARTER BASED ON START DATE OF CAMPAIGN
    start_month = getdate(date).month
    current_quarter = next(
        (quarter for quarter, months in quarter_map.items() if start_month in months),
        None,
    )
    return current_quarter


# ? METHOD TO ADD EXPENCE LOGS IN CHILD TABLE OF CAMPAIGN
def record_expense_log_in_campaign(doc, campaign_doc, method):

    # ? GET THE TYPE OF ENTRY (PURCHASE INVOICE OR EXPENSE CLAIM)
    entry_type = (
        "Purchase Invoice" if doc.doctype == "Purchase Invoice" else "Expense Claim"
    )

    if method == "before_submit":
        # ? ADD A NEW CHILD TABLE ROW
        campaign_doc.append(
            "custom_logs",
            {"entry_type": entry_type, "id": doc.name, "amount": doc.total},
        )
        campaign_doc.save()

    elif method == "on_cancel":
        # ? FIND AND REMOVE THE MATCHING ROW BASED ON TYPE AND RECORD ID
        logs_to_remove = [
            row
            for row in campaign_doc.custom_logs
            if row.id == doc.name and row.entry_type == entry_type
        ]
        for row in logs_to_remove:
            campaign_doc.remove(row)
        campaign_doc.save()


def get_expense_claim_exception(doc):
    # ? GET TRAVEL BUDGET
    travel_budget = frappe.db.get_value(
        "Travel Budget", {"company": doc.company}, "name"
    )
    if not travel_budget:
        frappe.throw(
            "Travel Budget is not set for this company. Please create a Travel Budget first."
        )

    # ? GET EMPLOYEE GRADE
    employee_grade = frappe.db.get_value("Employee", doc.employee, "grade")
    if not employee_grade:
        frappe.throw("Employee grade is not set. Please set the employee grade first.")

    # ? GET BUDGET ALLOCATION FOR THE GRADE
    budget_row = frappe.db.get_value(
        "Budget Allocation",
        {
            "parent": travel_budget,
            "parentfield": "buget_allocation",
            "grade": employee_grade,
        },
        [
            "lodging_allowance_metro",
            "lodging_allowance_non_metro",
            "meal_allowance_metro",
            "meal_allowance_non_metro",
            "local_commute_limit",
        ],
        as_dict=True,
    )

    if not budget_row:
        frappe.throw(
            f"No budget allocation found for employee grade '{employee_grade}' in Travel Budget '{travel_budget}'. Please create a budget allocation first."
        )

    # ? LOOP THROUGH EACH EXPENSE ITEM
    for idx, expense in enumerate(doc.expenses, start=1):
        allowed_amount = 0
        is_exception = False

        if expense.expense_type == "Food":
            allowed_amount = (
                budget_row.meal_allowance_metro
                if expense.custom_for_metro_city
                else budget_row.meal_allowance_non_metro
            )
            is_exception = expense.amount > allowed_amount

        elif expense.expense_type == "Lodging":
            allowed_amount = (
                budget_row.lodging_allowance_metro
                if expense.custom_for_metro_city
                else budget_row.lodging_allowance_non_metro
            )
            is_exception = expense.amount > allowed_amount

        elif expense.expense_type == "Local Commute":
            allowed_amount = budget_row.local_commute_limit
            is_exception = expense.amount > allowed_amount

        # ? IF EXCEPTION, FLAG IT AND CHECK ATTACHMENT
        if is_exception:

            if (
                not expense.custom_attachments
                and doc.company == get_indifoss_company_name().get("company_name")
            ):
                frappe.throw(
                    f"Attachment is required for Expense at row #{idx} of type '{expense.expense_type}' because it exceeds the allowed limit ({allowed_amount}). Please upload the attachment."
                )
            else:
                expense.custom_is_exception = 1


def validate_attachments_compulsion(doc):

    emp_company = frappe.db.get_value("Employee", doc.employee, "company")
    if not emp_company:
        frappe.throw(
            "Employee company not found. Please set the employee company first."
        )

    if emp_company == get_indifoss_company_name().get("company_name"):

        for expense in doc.expenses:
            if expense.custom_is_exception == 1 and not expense.attachments:

                frappe.throw(
                    f"Attachments are mandatory for the expense type '{expense.expense_type}' "
                    f"when it exceeds the allowed budget. Please attach the necessary documents."
                )

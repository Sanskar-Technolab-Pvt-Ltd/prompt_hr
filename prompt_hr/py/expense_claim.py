import frappe
from frappe.utils import cint, flt, getdate
import frappe.workflow
from prompt_hr.py.utils import (
    send_notification_email,
    expense_claim_and_travel_request_workflow_email,
    get_prompt_company_name,
    get_indifoss_company_name,
)
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Constants for expense types
EXPENSE_TYPES = {"FOOD": "Food", "LODGING": "Lodging", "LOCAL_COMMUTE": "Local Commute"}

COMMUTE_MODES = {"PUBLIC": "Public", "NON_PUBLIC": "Non-Public"}


# Hooks for Expense Claim lifecycle events
def before_submit(doc, method):
    """
    Called before an Expense Claim is submitted.
    Updates actual expense amounts in related Marketing Planning documents.
    """
    update_amount_in_marketing_planning(doc, method)


def before_save(doc, method):
    """
    Called before an Expense Claim is saved.
    Validates expenses against budget limits and checks for mandatory attachments.
    """
    if doc.expenses:
        validate_attachments_compulsion(doc)
        get_expense_claim_exception(doc)


def on_update(doc, method):
    """
    Called after an Expense Claim is updated.
    Shares the document and sends notification emails for workflow updates.
    """
    expense_claim_and_travel_request_workflow_email(doc)


def update_amount_in_marketing_planning(doc, method):
    """
    Updates the actual expense amount in Campaign and Marketing Planning documents
    linked to the Expense Claim. Handles 'before_submit' and 'on_cancel' events.
    """
    if doc.campaign:
        campaign_doc = frappe.get_doc("Campaign", doc.campaign)
        if campaign_doc.custom_marketing_plan:
            marketing_plan = frappe.get_doc(
                "Marketing Planning", campaign_doc.custom_marketing_plan
            )

            if method == "before_submit":
                control_action = get_control_flags(doc, marketing_plan)
                current_quarter = quarter_map(campaign_doc.custom_start_date)
                if not current_quarter:
                    return

                is_quarter_closed(marketing_plan, current_quarter)

                budget_exceeded = is_budget_exceeded(
                    campaign_doc, marketing_plan, current_quarter, doc.total
                )

                if budget_exceeded and control_action:
                    enforce_budget_control(
                        campaign_doc.custom_campaign_type,
                        current_quarter,
                        marketing_plan,
                        control_action,
                    )

                update_marketing_planning_row(
                    doc, method, campaign_doc, marketing_plan, current_quarter
                )

            elif method == "on_cancel":
                current_quarter = quarter_map(campaign_doc.custom_start_date)
                if not current_quarter:
                    return

                update_marketing_planning_row(
                    doc, method, campaign_doc, marketing_plan, current_quarter
                )


def enforce_budget_control(campaign, quarter, marketing_plan, action):
    """
    Enforces budget control actions ('Stop' or 'Warn') if the budget is exceeded.
    """
    link = ""
    if marketing_plan:
        link = (
            f'<a href="/app/marketing-planning/{marketing_plan.name}" target="_blank">'
            f"{marketing_plan.name}</a>"
        )

    if action == "Stop":
        frappe.throw(
            f"This entry exceeds the allocated budget and cannot be submitted. "
            f"Please review your budget limits in the <b>Expense Planning </b> section of the Marketing Planning document.<br><br>"
            f"<span style='color:red'> Note: Look for the row with Campaign Type: <b>{campaign}</b> and Quarter: <b>{quarter}</b> in Marketing Plan : <b>{link}</b></span>",
            exc=frappe.ValidationError,
        )
    elif action == "Warn":
        frappe.msgprint(
            f"Warning: This entry exceeds the planned budget. "
            f"Please review the budget in the <b>Expense Planning</b> section of the Marketing Planning document.<br><br>"
            f"Here is the link to the document: {link} <br><br>"
            f"<span style='color:red'> Note: Look for the row with Campaign Type: <b>{campaign}</b> and Quarter: <b>{quarter}</b> in Marketing Plan : <b>{link}</b></span>",
        )


def get_control_flags(doc, marketing_plan):
    """
    Retrieves the control action settings (Stop/Warn) from the Marketing Planning document
    based on the document type (Purchase Invoice or Expense Claim).
    """
    if doc.doctype == "Purchase Invoice":
        control_enabled = marketing_plan.applicable_on_purchase_invoice
        control_action = (
            marketing_plan.action_if_budget_exceeded_on_pi if control_enabled else None
        )
    elif doc.doctype == "Expense Claim":
        control_enabled = marketing_plan.applicable_on_expense_claim
        control_action = (
            marketing_plan.action_if_budget_exceeded_on_ec if control_enabled else None
        )
    return control_action


def is_budget_exceeded(campaign_doc, marketing_plan, current_quarter, invoice_total):
    """
    Checks if the current expense claim's total, when added to the actual expense,
    exceeds the expected budget for the linked campaign and quarter.
    """
    for row in marketing_plan.monthly_campaign_planning:
        if (
            row.campaign_type == campaign_doc.custom_campaign_type
            and row.month == current_quarter
        ):
            return (row.actual_expense + invoice_total) > row.expected_budget
    return False


def is_quarter_closed(marketing_plan, current_quarter):
    """
    Checks if the current quarter in the Marketing Planning document is marked as closed.
    If so, prevents transactions for that quarter.
    """
    for row in marketing_plan.quarter_budget_planning:
        if row.quarter == current_quarter:
            if row.quarter_closed:
                frappe.throw(
                    "Transactions are not allowed for quarters marked as <b>Closed</b> in Marketing Planning. "
                    "Please make transactions for current quarter."
                )


def update_marketing_planning_row(
    doc, method, campaign_doc, marketing_plan, current_quarter
):
    """
    Updates the 'actual_expense' and 'remaining_budget' fields in the relevant
    rows of the Marketing Planning's child tables (monthly and quarterly).
    """
    for row in marketing_plan.monthly_campaign_planning:
        if (
            row.campaign_type == campaign_doc.custom_campaign_type
            and row.month == current_quarter
        ):
            if method == "before_submit":
                row.actual_expense += doc.total
            elif method == "on_cancel":
                row.actual_expense -= doc.total
            row.remaining_budget = row.expected_budget - row.actual_expense

    for q_row in marketing_plan.quarter_budget_planning:
        if q_row.quarter == current_quarter:
            total_actual_expense = sum(
                r.actual_expense
                for r in marketing_plan.monthly_campaign_planning
                if r.month == current_quarter
            )
            q_row.actual_expense = total_actual_expense
            q_row.remaining_budget = q_row.expected_budget - total_actual_expense
    marketing_plan.save()

    record_expense_log_in_campaign(doc, campaign_doc, method)


def quarter_map(date):
    """
    Maps a given date's month to its corresponding financial quarter.
    """
    quarter_map = {
        "April": (4, 5, 6),
        "July": (7, 8, 9),
        "October": (10, 11, 12),
        "January": (1, 2, 3),
    }

    start_month = getdate(date).month
    current_quarter = next(
        (quarter for quarter, months in quarter_map.items() if start_month in months),
        None,
    )
    return current_quarter


def record_expense_log_in_campaign(doc, campaign_doc, method):
    """
    Records an expense entry (Purchase Invoice or Expense Claim) in the
    custom logs child table of the Campaign document.
    """
    entry_type = (
        "Purchase Invoice" if doc.doctype == "Purchase Invoice" else "Expense Claim"
    )

    if method == "before_submit":
        campaign_doc.append(
            "custom_logs",
            {"entry_type": entry_type, "id": doc.name, "amount": doc.total},
        )
        campaign_doc.save()

    elif method == "on_cancel":
        logs_to_remove = [
            row
            for row in campaign_doc.custom_logs
            if row.id == doc.name and row.entry_type == entry_type
        ]
        for row in logs_to_remove:
            campaign_doc.remove(row)
        campaign_doc.save()


def get_expense_claim_exception(doc):
    """
    Flags exceptions in an Expense Claim document based on configured travel budget limits
    for employee grade and specific expense types (Food, Lodging, Local Commute).
    """
    try:
        travel_budget = frappe.db.get_value(
            "Travel Budget", {"company": doc.company}, "name"
        )
        if not travel_budget:
            frappe.throw(
                f"Travel Budget not configured for company '{doc.company}'. Please contact your administrator to set up the travel budget."
            )

        employee_grade = frappe.db.get_value("Employee", doc.employee, "grade")
        if not employee_grade:
            frappe.throw(
                "Employee grade is not set. Please set it before submitting the claim."
            )

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
                "local_commute_limit_daily",
                "local_commute_limit_monthly",
            ],
            as_dict=True,
        )

        if not budget_row:
            frappe.throw(
                f"No Budget Allocation found for grade '{employee_grade}' in '{travel_budget}'. Please contact your administrator."
            )

        km_rate_map = {
            entry["type_of_travel"]: entry["rate_per_km"]
            for entry in frappe.db.get_all(
                "Service KM Rate",
                filters={"parent": travel_budget, "parentfield": "service_km_rate"},
                fields=["type_of_travel", "rate_per_km"],
            )
        }

        total_km = 0

        # Determine the earliest and latest expense dates in the current document
        # to define the overall date range for fetching approved expenses.
        current_expense_dates = [
            getdate(exp.expense_date) for exp in doc.expenses if exp.expense_date
        ]
        if not current_expense_dates:
            earliest_expense_date = latest_expense_date = getdate(doc.posting_date)
        else:
            earliest_expense_date = min(current_expense_dates)
            latest_expense_date = max(current_expense_dates)

        # Retrieve total approved local commute expenses for the *month of latest_expense_date*.
        # This forms the base for cumulative monthly limit checking.
        monthly_spent_base = get_approved_category_monthly_expense(
            employee=doc.employee,
            expense_date=latest_expense_date,  # Only needs a date within the target month
            expense_type=EXPENSE_TYPES["LOCAL_COMMUTE"],
            current_doc_name=doc.name,  # Exclude current document if it's already saved
        )

        # This defaultdict accumulates local commute expenses from the *current document*
        # for each month they fall into, allowing for cumulative checks.
        current_doc_monthly_totals = defaultdict(float)

        # Initialize daily_food_lodging_totals with approved amounts for the relevant date range
        # CORRECTED: _get_approved_food_lodging_daily_totals now returns daily totals per expense type
        daily_food_lodging_totals_by_type = _get_approved_food_lodging_daily_totals(
            employee=doc.employee,
            from_date=earliest_expense_date,
            to_date=latest_expense_date,
            current_doc_name=doc.name,  # Exclude current document if it's already saved
        )

        expenses = sorted(doc.expenses, key=lambda x: (x.expense_date, x.idx or 0))
        daily_totals_local_commute = defaultdict(
            float
        )  # Accumulates daily totals for current document's LOCAL COMMUTE expenses

        # NEW: For current document's Food/Lodging expenses, accumulate daily by type
        current_doc_daily_food_lodging_totals = defaultdict(lambda: defaultdict(float))


        for exp in expenses:
            exp.custom_is_exception = 0

        for idx, exp in enumerate(expenses, start=1):
            _validate_and_process_expense(
                exp,
                idx,
                budget_row,
                km_rate_map,
                daily_totals_local_commute, # Passed for Local Commute
                monthly_spent_base,
                current_doc_monthly_totals,
                employee_grade,
                doc.company,
                daily_food_lodging_totals_by_type,  # Pass the initialized historical totals
                current_doc_daily_food_lodging_totals, # Pass the current doc's accumulating totals
            )

            if (
                exp.expense_type == EXPENSE_TYPES["LOCAL_COMMUTE"]
                and exp.custom_mode_of_vehicle == COMMUTE_MODES["NON_PUBLIC"]
            ):
                total_km += flt(exp.custom_km or 0)

        doc.custom_total_km = total_km

    except frappe.ValidationError:
        # Re-raise Frappe ValidationErrors directly as they are intended user-facing errors.
        raise
    except Exception as e:
        frappe.throw(
            f"An unexpected error occurred during expense claim validation: {e}"
        )


def _validate_and_process_expense(
    exp,
    idx,
    budget_row,
    km_rate_map,
    daily_totals_local_commute,  # For Local Commute
    monthly_spent_base,
    current_doc_monthly_totals,
    employee_grade,
    company,
    daily_food_lodging_totals_by_type,  # Historical (approved) daily totals by type
    current_doc_daily_food_lodging_totals, # Current doc daily totals by type
):
    """
    Validates and processes an individual expense item within the claim.
    This includes checking for negative amounts, required dates,
    month-crossing for local commute, and flagging exceptions based on budget.
    """
    exp.custom_is_exception = 0
    exp_amount = flt(exp.amount or 0)
    days = cint(exp.custom_days or 0)  # Default to 0 for validation
    expense_date = getdate(exp.expense_date)

    if not exp.expense_date:
        frappe.throw(f"Expense date is required in Row #{idx}")

    if exp_amount < 0:
        frappe.throw(f"Amount cannot be negative in Row #{idx}")

    if exp.expense_type in [EXPENSE_TYPES["FOOD"], EXPENSE_TYPES["LODGING"]]:
        if days <= 0:
            frappe.throw(
                f"For {exp.expense_type} expense (Row #{idx}), 'Days' must be a positive number greater than 0."
            )

        _process_food_lodging_expense(
            exp,
            exp_amount,
            days,
            expense_date,
            budget_row,
            daily_food_lodging_totals_by_type,  # Historical totals for comparison
            current_doc_daily_food_lodging_totals # Current doc totals for accumulation
        )

    elif exp.expense_type == EXPENSE_TYPES["LOCAL_COMMUTE"]:
        if days < 1:
            frappe.throw(f"Days cannot be less than 1 in Row #{idx}")

        end_date = expense_date + timedelta(days=days - 1)

        # Local Commute expense cannot span across different months
        if expense_date.month != end_date.month or expense_date.year != end_date.year:
            frappe.throw(
                f"Row #{idx}: Local Commute expense cannot span across different months. "
                f"Expense starts on {expense_date.strftime('%Y-%m-%d')} and ends on {end_date.strftime('%Y-%m-%d')}."
            )

        _process_local_commute_expense(
            exp,
            idx,
            exp_amount,
            days,
            expense_date,
            budget_row,
            km_rate_map,
            daily_totals_local_commute,
            monthly_spent_base,
            current_doc_monthly_totals,
            employee_grade,
            company,
        )


def _process_food_lodging_expense(
    exp,
    total_exp_amount,
    days,
    expense_start_date,
    budget_row,
    approved_daily_food_lodging_totals_by_type, # Historical totals (from approved claims)
    current_doc_daily_food_lodging_totals # Totals for current document's expenses
):
    """
    Processes validation for Food and Lodging expenses against their defined allowances.
    Flags `custom_is_exception` if the *accumulated daily average* amount exceeds the limit.
    This function now correctly distributes the daily expense across all covered days,
    considering both previously approved and current document's entries,
    and maintains separate daily totals for Food and Lodging.
    """
    daily_per_item_amount = total_exp_amount / days

    metro = exp.custom_for_metro_city
    expense_type_for_budget_lookup = exp.expense_type.lower() # 'food' or 'lodging'

    if expense_type_for_budget_lookup == "food":
        expense_type_for_budget_lookup = "meal" # Adjust for budget field naming

    limit_field = f"{expense_type_for_budget_lookup}_allowance_{'metro' if metro else 'non_metro'}"
    limit = budget_row.get(limit_field, 0)

    exceeded_any_day = False
    for i in range(days):
        current_day = expense_start_date + timedelta(days=i)

        # Accumulate current document's expense for this specific (day, type)
        # current_doc_daily_food_lodging_totals is for this specific claim only
        current_doc_daily_food_lodging_totals[current_day][exp.expense_type] += daily_per_item_amount

        # Calculate cumulative total for this (day, type) by adding historical and current
        cumulative_daily_total = (
            approved_daily_food_lodging_totals_by_type[current_day][exp.expense_type] +
            current_doc_daily_food_lodging_totals[current_day][exp.expense_type]
        )

        # Check if the cumulative daily total for this day and type exceeds the limit
        if cumulative_daily_total > flt(limit):
            exceeded_any_day = True
            break

    if exceeded_any_day:
        exp.custom_is_exception = 1


def _get_approved_food_lodging_daily_totals(
    employee, from_date, to_date, current_doc_name=None
):
    """
    Calculates the accumulated daily sanctioned amounts for Food and Lodging,
    SEPARATELY BY EXPENSE TYPE, from *approved* Expense Claims within a given date range.
    Returns a defaultdict(lambda: defaultdict(float)) where keys are
    date -> expense_type -> total_sanctioned_amount_for_that_date_and_type.
    """
    # CORRECTED: Use nested defaultdict to store totals per date and per expense type
    approved_daily_totals_by_type = defaultdict(lambda: defaultdict(float))

    # Get all approved expense claims for the employee within the date range
    filters = {
        "employee": employee,
        "approval_status": "Approved",
        # Consider a wider range for posting_date to ensure all spanning claims are caught
        "posting_date": ["between", [getdate(from_date) - timedelta(days=30), getdate(to_date) + timedelta(days=30)]],
    }
    if current_doc_name:
        filters["name"] = ["!=", current_doc_name]

    approved_claim_names = frappe.get_all(
        doctype="Expense Claim",
        filters=filters,
        pluck="name",
        limit_page_length="UNLIMITED",
    )

    if not approved_claim_names:
        return approved_daily_totals_by_type

    # Get all matching expense claim details for Food and Lodging within these approved claims
    expense_claim_details = frappe.get_all(
        doctype="Expense Claim Detail",
        filters={
            "parent": ["in", approved_claim_names],
            "expense_type": ["in", [EXPENSE_TYPES["FOOD"], EXPENSE_TYPES["LODGING"]]],
            # Filter by expense_date (start date of item) to narrow results before looping
            "expense_date": ["between", [getdate(from_date) - timedelta(days=30), getdate(to_date) + timedelta(days=30)]],
        },
        fields=[
            "parent",
            "expense_date",
            "custom_days",
            "sanctioned_amount",
            "expense_type", # IMPORTANT: Fetch expense_type to differentiate
        ],
        limit_page_length="UNLIMITED",
    )

    for detail in expense_claim_details:
        if not detail.expense_date or not detail.sanctioned_amount:
            continue

        start_date = getdate(detail.expense_date)
        days = cint(detail.custom_days or 1)

        if days <= 0:
            continue

        per_day_amount = flt(detail.sanctioned_amount) / days

        # Distribute the per-day amount across all days covered by this approved expense item
        for i in range(days):
            current_day = start_date + timedelta(days=i)
            # Only add if the current day falls within our *originally requested* from_date to_date range
            # (or within the slightly expanded range for robustness)
            if getdate(from_date) <= current_day <= getdate(to_date):
                # CORRECTED: Use expense_type as part of the key
                approved_daily_totals_by_type[current_day][detail.expense_type] += per_day_amount

    return approved_daily_totals_by_type


def _process_local_commute_expense(
    exp,
    idx,
    exp_amount,
    days,
    expense_date,
    budget_row,
    daily_totals,
    monthly_spent_base,
    current_doc_monthly_totals,
    employee_grade,
    company,
):
    """
    Processes validation for Local Commute expenses, including attachment requirements,
    KM rate calculation (if applicable), and checks against daily/monthly limits.
    Flags `custom_is_exception` if limits are exceeded or attachments are missing.
    """
    # Check if attachment is mandatory based on commute details
    attach_required = frappe.db.get_value(
        "Local Commute Details",
        {
            "grade": employee_grade,
            "mode_of_commute": exp.custom_mode_of_vehicle,
            "type_of_commute": exp.custom_type_of_vehicle,
        },
        "attachment_mandatory",
    )

    if attach_required and not exp.custom_attachments:
        frappe.throw(
            f"Attachment required for Local Commute (Row #{idx}) as per commute rules."
        )

    # If non-public transport and amount not provided, calculate from KM rate
    if exp.custom_mode_of_vehicle == COMMUTE_MODES["NON_PUBLIC"]:
        km = flt(exp.custom_km or 0)
        rate = km_rate_map.get(exp.custom_type_of_vehicle, 0)

        if not exp.amount:  # Only calculate if amount is not manually entered
            exp.amount = exp.sanctioned_amount = rate * km
            exp_amount = flt(exp.amount)  # Update exp_amount with the calculated value

    daily_limit = flt(budget_row.get("local_commute_limit_daily", 0))
    monthly_limit = flt(budget_row.get("local_commute_limit_monthly", 0))

    daily_avg = exp_amount / days if days > 0 else exp_amount
    exceeded_daily = False
    exceeded_monthly = False

    # Check daily limits for each day spanned by the expense
    for i in range(days):
        day = expense_date + timedelta(days=i)
        daily_totals[day] += daily_avg
        if daily_limit and daily_totals[day] > daily_limit:
            exceeded_daily = True

    # Check monthly limit by combining previously approved amounts and current document's amounts
    current_month_key = (expense_date.year, expense_date.month)
    current_doc_monthly_totals[current_month_key] += exp_amount
    cumulative_monthly_spend = (
        monthly_spent_base + current_doc_monthly_totals[current_month_key]
    )

    if monthly_limit and cumulative_monthly_spend > monthly_limit:
        exceeded_monthly = True

    # Flag as exception if any limit is exceeded or attachments are missing for Indifoss
    if exceeded_daily or exceeded_monthly:
        if not exp.custom_attachments and company == get_indifoss_company_name().get(
            "company_name"
        ):
            frappe.throw(
                f"Row #{idx}: Attachment is required as the expense exceeds limits."
            )
        exp.custom_is_exception = 1


def validate_attachments_compulsion(doc):
    """
    Enforces attachment requirement for expenses flagged as exceptions,
    specifically for the Indifoss company. Throws an error if an exception
    is flagged but no attachment is provided.
    """
    try:
        emp_company = frappe.db.get_value("Employee", doc.employee, "company")
        if not emp_company:
            frappe.throw(
                "Employee company not found. Please set the employee company first."
            )

        if emp_company == get_indifoss_company_name().get("company_name"):
            for expense in doc.expenses:
                if expense.custom_is_exception == 1 and not expense.custom_attachments:
                    frappe.throw(
                        f"Attachments are mandatory for the expense type '{expense.expense_type}' "
                        f"when it exceeds the allowed budget. Please attach the necessary documents."
                    )
    except Exception as e:
        frappe.throw(f"An error occurred during attachment validation: {e}")


@frappe.whitelist()
def get_data_from_expense_claim_as_per_grade(employee, company):
    """
    Whitelisted function to retrieve allowed local commute options (public/non-public)
    for a given employee's grade and company based on configured Travel Budgets.
    """
    try:
        travel_budget = frappe.db.get_value(
            "Travel Budget", {"company": company}, "name"
        )
        grade = frappe.db.get_value("Employee", employee, "grade")

        if not travel_budget:
            return {
                "success": 0,
                "message": f"No Travel Budget found for company {company}",
            }

        if not grade:
            return {
                "success": 0,
                "message": f"Employee grade not found for employee {employee}",
            }

        commute_options = frappe.get_all(
            "Local Commute Details",
            filters={"parent": travel_budget, "grade": grade},
            fields=["mode_of_commute", "type_of_commute"],
        )

        public = []
        non_public = []

        for option in commute_options:
            if option.mode_of_commute == COMMUTE_MODES["PUBLIC"]:
                public.append(option.type_of_commute)
            elif option.mode_of_commute == "Non Public":
                non_public.append(option.type_of_commute)

        return {
            "success": 1,
            "data": {
                "allowed_local_commute_public": public,
                "allowed_local_commute_non_public": non_public,
            },
        }

    except Exception as e:
        frappe.throw(f"Error retrieving commute options: {e}")


def get_approved_category_monthly_expense(
    employee, expense_date, expense_type, current_doc_name=None
):
    """
    Calculates the total sanctioned amount for a specific expense category
    incurred by an employee within the calendar month of the given `expense_date`,
    considering only *approved* Expense Claims and excluding the current document if specified.
    """
    try:
        expense_date = getdate(expense_date)

        month_start = expense_date.replace(day=1)
        next_month = month_start + relativedelta(months=1)
        month_end = next_month - timedelta(days=1)

        # Get all approved expense claims for the employee
        filters = {"employee": employee, "approval_status": "Approved"}
        if current_doc_name:
            filters["name"] = ["!=", current_doc_name]

        all_approved_expense_claims = frappe.get_all(
            doctype="Expense Claim",
            filters=filters,
            pluck="name",
            limit_page_length="UNLIMITED",
        )

        if not all_approved_expense_claims:
            return 0.0

        # Get all matching expense claim details for the specified type and approved claims
        expense_claim_details = frappe.get_all(
            doctype="Expense Claim Detail",
            filters={
                "expense_type": expense_type,
                "parent": ["in", all_approved_expense_claims],
            },
            fields=["expense_date", "custom_days", "sanctioned_amount"],
            limit_page_length="UNLIMITED",
        )

        total_sanctioned_amount = 0

        for detail in expense_claim_details:
            if not detail.expense_date or not detail.sanctioned_amount:
                continue

            start_date = getdate(detail.expense_date)
            days = cint(detail.custom_days or 1)

            if days <= 0:
                continue

            end_date = start_date + timedelta(days=days - 1)
            per_day_amount = flt(detail.sanctioned_amount) / days

            # Calculate overlapping days with the target month
            overlap_start = max(start_date, month_start)
            overlap_end = min(end_date, month_end)

            if overlap_start <= overlap_end:
                overlapping_days = (overlap_end - overlap_start).days + 1
                total_sanctioned_amount += per_day_amount * overlapping_days

        return round(total_sanctioned_amount, 2)

    except Exception as e:
        frappe.throw(
            f"An error occurred while calculating approved monthly expenses: {e}"
        )
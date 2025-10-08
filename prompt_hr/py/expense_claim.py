import frappe
from frappe.auth import today
from frappe.utils import cint, flt, getdate, get_datetime, add_days, date_diff, time_diff_in_hours
import frappe.workflow
import json
from datetime import time
from frappe import _
from prompt_hr.py.utils import (
    send_notification_email,
    expense_claim_and_travel_request_workflow_email,
    get_prompt_company_name,
)
from collections import defaultdict
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim
from datetime import datetime, timedelta,time
from dateutil.relativedelta import relativedelta

# Constants for expense types
EXPENSE_TYPES = {"FOOD": "Food", "LODGING": "Lodging", "LOCAL_COMMUTE": "Local Commute"}

COMMUTE_MODES = {"PUBLIC": "Public", "NON_PUBLIC": "Private"}


# Hooks for Expense Claim lifecycle events
def before_submit(doc, method):
    """
    Called before an Expense Claim is submitted.
    Updates actual expense amounts in related Marketing Planning documents.
    """
    update_amount_in_marketing_planning(doc, method)
    send_mail_for_updates(doc)


def before_save(doc, method):
    """
    Called before an Expense Claim is saved.
    Validates expenses against budget limits and checks for mandatory attachments.
    """
    if doc.expenses:
        validate_attachments_compulsion(doc)
        validate_number_of_days(doc)
        get_expense_claim_exception(doc)
        validate_expenses_entry(doc)
        validate_expense_claim_detail_rules(doc)
        update_da_amount_as_per_time(doc)
        ExpenseClaim.calculate_total_amount(doc)
        ExpenseClaim.calculate_taxes(doc)
        sort_expense_claim_data(doc)

    if not doc.is_new():
        send_mail_for_updates(doc)

def send_mail_for_updates(doc):
    if doc.is_new():
        return

    # ? Pre-fetch employee details
    employee = frappe.db.get_value("Employee", doc.employee, ["employee_name", "user_id", "reports_to"], as_dict=True)
    employee_name = employee.employee_name
    employee_id = employee.user_id
    expense_approver = doc.expense_approver

    reporting_manager_user_id = None
    reporting_manager_name = None
    if employee.reports_to:
        rm = frappe.db.get_value("Employee", employee.reports_to, ["user_id", "employee_name"], as_dict=True)
        if rm:
            reporting_manager_user_id = rm.user_id
            reporting_manager_name = rm.employee_name

    try:
        workflow_state_change = doc.has_value_changed("workflow_state")
    except Exception:
        workflow_state_change = True

    if not workflow_state_change:
        return

    # ? Base helper for sending mail
    def send_notification(notification_name, context_updates=None, recipients=None):
        notification_doc = frappe.get_doc("Notification", notification_name)
        ctx = {"employee_name": employee_name, "expense_approver_name": "", "can_approve": 0, "doc":doc}
        if context_updates:
            ctx.update(context_updates)

        subject = frappe.render_template(notification_doc.subject, ctx)
        message = frappe.render_template(notification_doc.message, ctx)

        if recipients:
            if isinstance(recipients, str):
                recipients = [recipients]
            frappe.sendmail(recipients=recipients, subject=subject, message=message)

    # Workflow state handling
    if doc.workflow_state == "Pending For Approval":
        if expense_approver:
            ea = frappe.db.get_value("Employee", {"user_id": expense_approver}, "employee_name") or expense_approver
            send_notification("Expense Claim Send For Approval Notification",
                            {"expense_approver_name": ea, "can_approve": 1},
                            recipients=expense_approver)

        if reporting_manager_user_id:
            send_notification("Expense Claim Send For Approval Notification",
                            {"expense_approver_name": reporting_manager_name, "can_approve": 0},
                            recipients=reporting_manager_user_id)

        if employee_id:
            send_notification("Expense Claim Send For Approval Notification",
                            {"expense_approver_name": employee_name, "can_approve": 0},
                            recipients=employee_id)

    elif doc.workflow_state == "Rejected":
        if expense_approver:
            ea = frappe.db.get_value("Employee", {"user_id": expense_approver}, "employee_name") or expense_approver
            send_notification("Expense Claim Rejection Notification",
                            {"expense_approver_name": ea, "can_approve": 1},
                            recipients=expense_approver)

        if reporting_manager_user_id:
            send_notification("Expense Claim Rejection Notification",
                            {"expense_approver_name": reporting_manager_name, "can_approve": 0},
                            recipients=reporting_manager_user_id)

        if employee_id:
            send_notification("Expense Claim Rejection Notification",
                            {"expense_approver_name": employee_name, "can_approve": 0},
                            recipients=employee_id)

    elif doc.workflow_state in ("Escalated", "Sent to Accounting Team"):
        stage = doc.workflow_state
        if expense_approver:
            ea = frappe.db.get_value("Employee", {"user_id": expense_approver}, "employee_name") or expense_approver
            send_notification("Expense Claim Escalation Notification",
                            {"expense_approver_name": ea, "stage": stage},
                            recipients=expense_approver)

        if reporting_manager_user_id:
            send_notification("Expense Claim Escalation Notification",
                            {"expense_approver_name": reporting_manager_name, "stage": stage},
                            recipients=reporting_manager_user_id)

        if employee_id:
            send_notification("Expense Claim Escalation Notification",
                            {"stage": stage},
                            recipients=employee_id)

        # For last shared user
        last_shared = frappe.get_all(
            "DocShare",
            filters={"share_doctype": doc.doctype, "share_name": doc.name, "user": ["!=", employee_id]},
            fields=["user"],
            order_by="creation desc",
            limit_page_length=1
        )

        if last_shared:
            last_shared_user = last_shared[0].user
            shared_employee_name = frappe.db.get_value("Employee", {"user_id": last_shared_user}, "employee_name")
            if shared_employee_name:
                send_notification("Expense Claim Escalation Notification",
                                {"expense_approver_name": shared_employee_name, "can_approve": 1, "stage": stage},
                                recipients=last_shared_user)

    elif doc.workflow_state == "Expense Claim Submitted":
        if expense_approver:
            ea = frappe.db.get_value("Employee", {"user_id": expense_approver}, "employee_name") or expense_approver
            send_notification("Expense Claim Submitted Notification",
                            {"expense_approver_name": ea},
                            recipients=expense_approver)

        if reporting_manager_user_id:
            send_notification("Expense Claim Submitted Notification",
                            {"expense_approver_name": reporting_manager_name},
                            recipients=reporting_manager_user_id)

        if employee_id:
            send_notification("Expense Claim Submitted Notification",
                            recipients=employee_id)


def validate_number_of_days(doc):
    try:
        meal_configs = fetch_meal_allowance_settings()
        meal_configs = sorted(meal_configs, key=lambda x: x["from_hours"])
        employee_grade = frappe.db.get_value("Employee", doc.employee, "grade")
        #? ENSURE THAT EACH EXPENSE ENTRY HAS custom_days <= 1
        for expense in doc.expenses:
            expense_days = expense.custom_days or 0
            expense_type = expense.expense_type

            if get_allowance_budgets(employee_grade,doc.company,expense_type, expense.custom_for_metro_city) == -1:
                raise frappe.ValidationError(
                    _("Row #{0}: Expense Type {1} is not allowed for Employee Grade {2}.")
                    .format(expense.idx, expense_type, employee_grade)
                )
            #! THROW AN ERROR IF MORE THAN 1 DAY IS SELECTED FOR A SINGLE EXPENSE ROW
            if expense_days > 1:
                if expense_type not in ["Lodging", "Local Commute", "Food"]:
                    raise frappe.ValidationError(
                        _("Row #{0}: Each expense entry must have Days 1 or less. Found {1} days.")
                        .format(expense.idx, expense.custom_days)
                    )

            if expense.expense_type == "DA":
                if expense.expense_date != expense.custom_expense_end_date:
                    raise frappe.ValidationError(
                        _("Row #{0}: Start Date and End Date must be the same for Daily Allowance (DA). Multi-day claims are not allowed.")
                        .format(expense.idx)
                    )

            # ! VALIDATION FOR END TIME CANNOT BE EARLIER THAN START TIME FOR SAME DATE
            if expense.expense_date == expense.custom_expense_end_date:
                start_time = get_datetime(expense.custom_expense_start_time)
                end_time = get_datetime(expense.custom_expense_end_time)

                if start_time > end_time:
                    raise frappe.ValidationError(
                        _("Row #{0}: End Time cannot be earlier than Start Time.").format(expense.idx)
                    )

            if expense.expense_type == "DA" and expense.custom_expense_start_time and expense.custom_expense_end_time:
                #? CALCULATE DIFFERENCE IN HOURS
                hours = time_diff_in_hours(expense.custom_expense_end_time, expense.custom_expense_start_time)

                if expense.custom_field_visits or expense.custom_service_calls:
                    #? GET FIELD VISITS AS LIST
                    field_visits_list = []
                    if expense.custom_field_visits:
                        field_visits_list = [v.strip() for v in expense.custom_field_visits.split(",") if v.strip()]

                    #? GET SERVICE CALLS AS LIST
                    service_calls_list = []
                    if expense.custom_service_calls:
                        service_calls_list = [v.strip() for v in expense.custom_service_calls.split(",") if v.strip()]

                    if len(field_visits_list) > 1 or len(service_calls_list) > 1:
                        continue

                #! FIND MATCHED CONFIG
                for config in meal_configs:
                    if config["from_hours"] <= hours <= config["to_hours"]:
                        expense.custom_days = config["meal_allowance"]/100
                        break
            else:
                #! FOR NON-DA EXPENSE TYPES, ASSUME FULL DAY
                if expense.expense_type != "Lodging" and expense.expense_type != "Local Commute" and expense.expense_type != "Food":
                    expense.custom_days = 1
                else:
                    #? COMBINE DATE + TIME INTO DATETIME OBJECTS
                    start_dt = get_datetime(str(expense.expense_date) + " " + str(expense.custom_expense_start_time or "00:00:00"))
                    end_dt = get_datetime(str(expense.custom_expense_end_date) + " " + str(expense.custom_expense_end_time or "00:00:00"))

                    #? CALCULATE TOTAL HOURS
                    total_hours = time_diff_in_hours(end_dt, start_dt)
                    #? CONVERT HOURS TO DAYS (E.G. 24 HRS = 1 DAY)
                    expense.custom_days = round(total_hours / 24 * 4) / 4 or 1
                
    except Exception as e:
        frappe.throw(str(e))

def validate_expenses_entry(doc):
    try:
        #! GET ALL NON-CANCELLED EXPENSE CLAIMS FOR EMPLOYEE EXCLUDING CURRENT DOC
        employee_expense_claims = frappe.get_all(
            "Expense Claim",
            filters={"employee": doc.employee, "docstatus": ["!=", 2], "name": ["!=", doc.name]},
            pluck="name"
        )

        #! TRACK ENTRIES IN CURRENT DOC FOR DUPLICATES
        seen_entries = set()
        da_day_map = {}  #? MAP TO TRACK TOTAL CUSTOM_DAYS PER DATE IN CURRENT DOC

        for row in doc.expenses:
            key = None

            if row.expense_type == "DA":
                #? USE DATE AS KEY FOR DA
                key = ("DA", row.expense_date)

                #! ACCUMULATE DA DAYS FOR THIS DATE
                da_day_map.setdefault(row.expense_date, 0)
                da_day_map[row.expense_date] += row.custom_days or 0

                #! IF TOTAL DAYS FOR DATE EXCEED 1, THROW ERROR
                if da_day_map[row.expense_date] > 1:
                    frappe.throw(f"Total DA days exceed 1 for <b>{row.expense_date}</b>.")

            #! CHECK FOR EXISTING DUPLICATES IN OTHER DOCS
            filters = {
                "expense_date": row.expense_date,
                "parent": ["in", employee_expense_claims],
                "expense_type": row.expense_type
            }

            if row.expense_type in ["DA"]:
                duplicate = frappe.db.exists("Expense Claim Detail", filters)

                if duplicate:
                    if row.expense_type == "DA":
                        #! GET TOTAL custom_days FROM MATCHING EXPENSE CLAIM DETAILS
                        existing_days = sum(
                            frappe.db.get_all(
                                "Expense Claim Detail",
                                filters=filters,
                                pluck="custom_days"  #? PLUCK AS SINGLE FIELD, NOT A LIST
                            )
                        )
                        total_days = existing_days + da_day_map.get(row.expense_date, 0)
                        if total_days > 1:
                            raise frappe.ValidationError(
                                f"Duplicate DA entry already exists for <b>{row.expense_date}</b> and will exceed 1 day."
                            )
                    else:
                        frappe.throw(
                            f"Duplicate {row.expense_type} entry already exists in another Expense Claim for "
                            f"<b>{doc.employee}</b> on <b>{row.expense_date}</b>."
                        )
    except Exception as e:
        frappe.throw(str(e))

def validate_expense_claim_detail_rules(doc):
    try:
        #! LOOP THROUGH ALL CHILD ROWS IN EXPENSE CLAIM
        for row in doc.expenses:
            expense_days = row.custom_days or 0
            #? RULE 1: CITY IS MANDATORY IF EXPENSE TYPE IS 'Lodging'
            if row.expense_type == "Lodging" and not row.custom_city:
                frappe.throw(
                    _(f"City is mandatory for Lodging expense. Please fill 'City' in row {row.idx}.")
                )

            #? RULE 2: DAYS GREATER THAN ZERO FOR DA
            if row.expense_type == "DA" and not expense_days and expense_days <= 0:
                frappe.throw(
                    _(f"Days Must Be Greater Than Zero For DA in row {row.idx}.")
                )
            
            if row.custom_field_visits:
                error = validate_field_visits_timing(row.expense_date, row.custom_expense_end_date, row.custom_expense_start_time, row.custom_expense_end_time, row.custom_field_visits)
                if error:
                    raise frappe.ValidationError(f"Row #{row.idx}: {error}")
    except Exception as e:
        frappe.throw(str(e))

def update_da_amount_as_per_time(doc):
    da_amount = 0
    hr_settings = frappe.get_single("HR Settings")
    time_map = {}
    if hr_settings.custom_meal_allowance_table:
        for row in hr_settings.custom_meal_allowance_table:
            time_map.update({f"{row.from_no_of_hours_travel_per_day or 0}:{row.to_no_of_hours_travel_per_day or 0}": row.meal_allowance or 0})
    else:
        frappe.throw("Please add meal allowance table in HR Settings")

    #! FETCH LATEST SUBMITTED TRAVEL BUDGET DOCUMENT FOR THE GIVEN COMPANY
    travel_visit_doc = frappe.get_all(
                "Travel Budget",
                filters={"docstatus": 1, "company": doc.company},
                fields=["name"],
                order_by="creation desc",
                limit=1
            )
    #? IF A TRAVEL BUDGET EXISTS
    if travel_visit_doc:
        #? GET EMPLOYEE GRADE
        employee_grade = frappe.get_value("Employee", doc.employee, "grade")

        #? FETCH FULL TRAVEL BUDGET DOCUMENT
        travel_budget = frappe.get_doc("Travel Budget", travel_visit_doc[0].name)

        #? MATCH EMPLOYEE GRADE TO FIND APPLICABLE DA ALLOWANCE
        if employee_grade:
            for budget in travel_budget.buget_allocation:
                if employee_grade == budget.grade:
                    da_amount = budget.da_allowance
                    break   
    for expense in doc.expenses:
        if expense.expense_type == "DA":
            if da_amount < 0:
                frappe.throw(
                    "You Are Not Eligible For DA Allowance"
                )
            if expense.expense_date != expense.custom_expense_end_date:
                frappe.throw("Expense Start and End Date Must Be Same For DA")
            if expense.custom_field_visits or expense.custom_service_calls:
                #? GET FIELD VISITS AS LIST
                field_visits_list = []
                if expense.custom_field_visits:
                    field_visits_list = [v.strip() for v in expense.custom_field_visits.split(",") if v.strip()]

                #? GET SERVICE CALLS AS LIST
                service_calls_list = []
                if expense.custom_service_calls:
                    service_calls_list = [v.strip() for v in expense.custom_service_calls.split(",") if v.strip()]

                if len(field_visits_list) > 1 or len(service_calls_list) > 1:
                    continue


            if expense.custom_expense_start_time is not None and expense.custom_expense_end_time is not None:
                #? CALCULATE DIFFERENCE IN HOURS
                diff_in_hours = time_diff_in_hours(expense.custom_expense_end_time, expense.custom_expense_start_time)

                #? FIND MATCHING TIME SLAB FROM HR SETTINGS
                for time_range, allowance_multiplier in time_map.items():
                    from_hours, to_hours = map(float, time_range.split(":"))
                    if from_hours <= diff_in_hours <= to_hours:
                        expense.amount = da_amount * allowance_multiplier/100
                        expense.sanctioned_amount = expense.amount
                        break
                else:
                    expense.amount = da_amount
                    expense.sanctioned_amount = da_amount
            else:
                frappe.throw("Start Time and End Time is Mandatory For DA")


def on_update(doc, method):
    """
    Called after an Expense Claim is updated.
    Shares the document and sends notification emails for workflow updates.
    """
    expense_claim_and_travel_request_workflow_email(doc)
    set_local_commute_expense_in_employee(doc.employee)


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


from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import frappe
from frappe.utils import flt, cint, getdate


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
        current_expense_dates = [
            getdate(exp.expense_date) for exp in doc.expenses if exp.expense_date
        ]
        if not current_expense_dates:
            earliest_expense_date = latest_expense_date = getdate(doc.posting_date)
        else:
            earliest_expense_date = min(current_expense_dates)
            latest_expense_date = max(current_expense_dates)

        # Get unique months from current document's local commute expenses
        unique_months = set()
        for exp in doc.expenses:
            if exp.expense_type == EXPENSE_TYPES["LOCAL_COMMUTE"] and exp.expense_date:
                exp_date = getdate(exp.expense_date)
                unique_months.add((exp_date.year, exp_date.month))

        # Get approved monthly totals for each unique month
        monthly_approved_totals = {}
        for year, month in unique_months:
            month_date = getdate(f"{year}-{month:02d}-01")
            monthly_approved_totals[(year, month)] = (
                get_approved_category_monthly_expense(
                    employee=doc.employee,
                    expense_date=month_date,
                    expense_type=EXPENSE_TYPES["LOCAL_COMMUTE"],
                    current_doc_name=doc.name,
                )
            )

        # Initialize daily totals for food, lodging, and local commute
        daily_food_lodging_totals_by_type = _get_approved_food_lodging_daily_totals(
            employee=doc.employee,
            from_date=earliest_expense_date,
            to_date=latest_expense_date,
            current_doc_name=doc.name,
        )

        # Get approved daily local commute totals
        daily_local_commute_totals = _get_approved_local_commute_daily_totals(
            employee=doc.employee,
            from_date=earliest_expense_date,
            to_date=latest_expense_date,
            current_doc_name=doc.name,
        )

        expenses = sorted(doc.expenses, key=lambda x: (x.expense_date, x.idx or 0))

        # Current document's daily totals accumulation
        current_doc_daily_food_lodging_totals = defaultdict(lambda: defaultdict(float))
        current_doc_daily_local_commute_totals = defaultdict(float)
        current_doc_monthly_totals = defaultdict(float)

        for exp in expenses:
            exp.custom_is_exception = 0

        for idx, exp in enumerate(expenses, start=1):
            _validate_and_process_expense(
                exp,
                idx,
                budget_row,
                km_rate_map,
                daily_local_commute_totals,
                current_doc_daily_local_commute_totals,
                monthly_approved_totals,
                current_doc_monthly_totals,
                employee_grade,
                doc.company,
                daily_food_lodging_totals_by_type,
                current_doc_daily_food_lodging_totals,
                doc,
                travel_budget
            )

            if (
                exp.expense_type == EXPENSE_TYPES["LOCAL_COMMUTE"]
                and exp.custom_mode_of_vehicle == COMMUTE_MODES["NON_PUBLIC"]
            ):
                total_km += flt(exp.custom_km or 0)

        doc.custom_total_km = total_km

    except frappe.ValidationError:
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
    daily_local_commute_totals,
    current_doc_daily_local_commute_totals,
    monthly_approved_totals,
    current_doc_monthly_totals,
    employee_grade,
    company,
    daily_food_lodging_totals_by_type,
    current_doc_daily_food_lodging_totals,
    doc,
    travel_budget
):
    """
    Validates and processes an individual expense item within the claim.
    """
    exp.custom_is_exception = 0
    exp_amount = flt(exp.amount or 0)
    days = exp.custom_days or 1
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
            daily_food_lodging_totals_by_type,
            current_doc_daily_food_lodging_totals,
            company,
            travel_budget,
            doc
        )

    elif exp.expense_type == EXPENSE_TYPES["LOCAL_COMMUTE"]:
        if days <= 0:
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
            daily_local_commute_totals,
            current_doc_daily_local_commute_totals,
            monthly_approved_totals,
            current_doc_monthly_totals,
            employee_grade,
            company,
            doc,
        )


def _process_food_lodging_expense(
    exp,
    total_exp_amount,
    days,
    expense_start_date,
    budget_row,
    approved_daily_food_lodging_totals_by_type,
    current_doc_daily_food_lodging_totals,
    company,
    travel_budget,
    doc
):
    """
    Processes validation for Food and Lodging expenses against their defined allowances.
    """
    daily_per_item_amount = total_exp_amount / days
    days = cint(days) or 1
    metro = exp.custom_for_metro_city
    expense_type_for_budget_lookup = exp.expense_type.lower()
    if doc.employee:
        employee_grade = frappe.db.get_value("Employee", doc.employee, "grade")
        employee_budget_row = frappe.db.get_value(
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
    if expense_type_for_budget_lookup == "food":
        expense_type_for_budget_lookup = "meal"

    limit_field = f"{expense_type_for_budget_lookup}_allowance_{'metro' if metro else 'non_metro'}"
    limit = budget_row.get(limit_field, 0)
    #! VALIDATE LODGING EXPENSES TO AVOID DUPLICATES FOR EMPLOYEE OR SHARED ACCOMMODATION

    #? ONLY PROCESS IF EXPENSE TYPE IS LODGING
    if exp.expense_type == EXPENSE_TYPES["LODGING"]:
        
        #? DETERMINE EMPLOYEES TO CHECK (INCLUDE SHARED ACCOMMODATION IF PRESENT)
        employees_to_check = [doc.employee]
        if exp.custom_shared_accommodation_employee:
            employees_to_check.append(exp.custom_shared_accommodation_employee)

        #! CHECK IN EXPENSE CLAIM DETAIL DIRECTLY
        existing_detail = frappe.get_all(
            "Expense Claim Detail",
            filters=[
                ["parent", "!=", doc.name],
                ["expense_type", "=", "Lodging"],
                ["custom_shared_accommodation_employee", "in", employees_to_check],
                ["expense_date", "between", [exp.expense_date, exp.custom_expense_end_date]],
            ],
            or_filters=[
                ["parent", "!=", doc.name],
                ["expense_type", "=", "Lodging"],
                ["custom_shared_accommodation_employee", "in", employees_to_check],
                ["custom_expense_end_date", "between", [exp.expense_date, exp.custom_expense_end_date]],
            ],
            fields=["name", "custom_shared_accommodation_employee"],
            limit=1
        )

        #? IF FOUND, THROW ERROR
        if existing_detail:
            frappe.throw(
                f"Lodging expense for {exp.expense_date} already exists for employee(s): {existing_detail[0].get('custom_shared_accommodation_employee')}"
            )


        #! CHECK IN OTHER EXPENSE CLAIMS OF EMPLOYEE(S)
        other_claims = frappe.get_all(
            "Expense Claim",
            filters={
                "employee": ("in", employees_to_check),
                "name": ("!=", doc.name)
            },
            pluck="name"
        )

        if other_claims:
            existing_in_claims = frappe.get_all(
                "Expense Claim Detail",
                filters={
                    "parent": ("in", other_claims),
                    "expense_type": "Lodging",
                    "expense_date": exp.expense_date
                },
                fields = ["name"],
                limit=1
            )
            if existing_in_claims:
                frappe.throw(
                    f"Lodging expense for {exp.expense_date} already exists for employee(s): {doc.get('employee')}"
                )


        #? IF SHARED ACCOMMODATION WITH SOMEONE
        if exp.custom_shared_accommodation_employee:
            #? FETCH GRADE OF SHARED ACCOMODATION EMPLOYEE
            shared_employee_grade = frappe.db.get_value(
                "Employee", exp.custom_shared_accommodation_employee, "grade"
            )
            if shared_employee_grade:
                #? FETCH SHARED EMPLOYEE'S BUDGET ALLOCATION ROW BASED ON GRADE
                shared_employee_budget_row = frappe.db.get_value(
                    "Budget Allocation",
                    {
                        "parent": travel_budget,
                        "parentfield": "buget_allocation",
                        "grade": shared_employee_grade,
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
                if shared_employee_budget_row:
                    #? DETERMINE ALLOWANCE FIELD NAME BASED ON METRO/NON-METRO
                    shared_employee_limit_field = f"{expense_type_for_budget_lookup}_allowance_{'metro' if metro else 'non_metro'}"
                    
                    #? GET SHARED EMPLOYEE LIMIT VALUE
                    shared_employee_limit = shared_employee_budget_row.get(shared_employee_limit_field, 0)

                    if shared_employee_limit == 0:
                        limit = 0
                    #? IF SHARED EMPLOYEE LIMIT IS LESS THAN CURRENT LIMIT → ADD 40% OF THEIR LIMIT
                    if shared_employee_limit < limit:
                        limit = limit + shared_employee_limit * 0.4
                    else:
                        #? ELSE TAKE 40% OF CURRENT LIMIT + FULL SHARED EMPLOYEE LIMIT
                        limit = limit * 0.4  + shared_employee_limit
            else:
                #! THROW ERROR IF GRADE NOT SET FOR SHARED EMPLOYEE
                frappe.throw(
                    f"Grade not set for employee {exp.custom_shared_accommodation_employee}"
                )

        if exp.custom_lodging_adjustment_type:
            #! FETCH ADJUSTMENT PERCENTAGE AND ATTACHMENT MANDATORY FLAG
            change_percentage, is_attachment_mandatory = frappe.db.get_value(
                "Lodging Adjustment Type",
                exp.custom_lodging_adjustment_type,
                ["adjustment_percentage", "is_attachment_mandatory"]
            )

            #! VALIDATE ATTACHMENT IF MANDATORY
            if is_attachment_mandatory and not exp.custom_attachments:
                frappe.throw(
                    f"Row #{exp.get('idx')}: Attachment is required as it is mandatory for Lodging Adjustment Type {exp.custom_lodging_adjustment_type}"
                )
            # ? GET PREVIOUS VALUE FROM DB
            prev_lodging_adjustment_type = frappe.db.get_value("Expense Claim Detail", exp.name, "custom_lodging_adjustment_type")
            #! APPLY PERCENTAGE CHANGE TO AMOUNT IF LODGING ADJUSTMENT TYPE IS CHANGED
            if change_percentage and prev_lodging_adjustment_type != change_percentage:
                exp.amount = (change_percentage * exp.amount) / 100
                exp.sanctioned_amount = exp.amount


    exceeded_any_day = False
    for i in range(days):
        current_day = expense_start_date + timedelta(days=i)

        current_doc_daily_food_lodging_totals[current_day][
            exp.expense_type
        ] += daily_per_item_amount

        cumulative_daily_total = (
            approved_daily_food_lodging_totals_by_type[current_day][exp.expense_type]
            + current_doc_daily_food_lodging_totals[current_day][exp.expense_type]
        )

        if cumulative_daily_total > flt(limit) and limit>0:
            exceeded_any_day = True
            break

    if exceeded_any_day:
        employee_limit_field = f"{expense_type_for_budget_lookup}_allowance_{'metro' if metro else 'non_metro'}"
        employee_limit = employee_budget_row.get(employee_limit_field, 0)

        if (not exp.custom_attachments) and employee_limit !=0:
            frappe.throw(
                f"Row #{exp.get('idx')}: Attachment is required as the expense exceeds limits."
            )

        if employee_limit != 0:
            exp.custom_is_exception = 1

@frappe.whitelist()
def get_employees_by_role(doctype, txt, searchfield, start, page_len, filters):
    
    if not filters.get("role"):
        return []

    role = filters.get("role")

    # ? GET THE LIST OF USER IDS WHO HAVE THE GIVEN ROLE
    user_with_role = frappe.get_all("Has Role",
        filters={"role": role},
        fields=["parent"]
    )
    user_ids = [d.parent for d in user_with_role]
    if not user_ids:
        return []

    # ? GET ACTIVE EMPLOYEES WHOSE USER_ID IS IN THE USER_IDS LIST
    employees = frappe.get_all("Employee",
        filters={
            "status": "Active",
            "user_id": ("in", user_ids)
        },
        fields=["name", "employee_name"],
    )

    return [(e.name, e.employee_name) for e in employees]

def _get_approved_food_lodging_daily_totals(
    employee, from_date, to_date, current_doc_name=None
):
    """
    Calculates the accumulated daily sanctioned amounts for Food and Lodging,
    SEPARATELY BY EXPENSE TYPE, from *approved* Expense Claims within a given date range.
    """
    approved_daily_totals_by_type = defaultdict(lambda: defaultdict(float))

    filters = {
        "employee": employee,
        "approval_status": "Approved",
        "posting_date": [
            "between",
            [
                getdate(from_date) - timedelta(days=30),
                getdate(to_date) + timedelta(days=30),
            ],
        ],
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

    expense_claim_details = frappe.get_all(
        doctype="Expense Claim Detail",
        filters={
            "parent": ["in", approved_claim_names],
            "expense_type": ["in", [EXPENSE_TYPES["FOOD"], EXPENSE_TYPES["LODGING"]]],
            "expense_date": [
                "between",
                [
                    getdate(from_date) - timedelta(days=30),
                    getdate(to_date) + timedelta(days=30),
                ],
            ],
        },
        fields=[
            "parent",
            "expense_date",
            "custom_days",
            "sanctioned_amount",
            "expense_type",
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

        for i in range(days):
            current_day = start_date + timedelta(days=i)
            if getdate(from_date) <= current_day <= getdate(to_date):
                approved_daily_totals_by_type[current_day][
                    detail.expense_type
                ] += per_day_amount

    return approved_daily_totals_by_type


def _get_approved_local_commute_daily_totals(
    employee, from_date, to_date, current_doc_name=None
):
    """
    Calculates the accumulated daily sanctioned amounts for Local Commute
    from *approved* Expense Claims within a given date range.
    """
    approved_daily_totals = defaultdict(float)

    filters = {
        "employee": employee,
        "approval_status": "Approved",
        "posting_date": [
            "between",
            [
                getdate(from_date) - timedelta(days=30),
                getdate(to_date) + timedelta(days=30),
            ],
        ],
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
        return approved_daily_totals

    expense_claim_details = frappe.get_all(
        doctype="Expense Claim Detail",
        filters={
            "parent": ["in", approved_claim_names],
            "expense_type": EXPENSE_TYPES["LOCAL_COMMUTE"],
            "expense_date": [
                "between",
                [
                    getdate(from_date) - timedelta(days=30),
                    getdate(to_date) + timedelta(days=30),
                ],
            ],
        },
        fields=[
            "expense_date",
            "custom_days",
            "sanctioned_amount",
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

        for i in range(days):
            current_day = start_date + timedelta(days=i)
            if getdate(from_date) <= current_day <= getdate(to_date):
                approved_daily_totals[current_day] += per_day_amount

    return approved_daily_totals


def _process_local_commute_expense(
    exp,
    idx,
    exp_amount,
    days,
    expense_date,
    budget_row,
    km_rate_map,
    daily_local_commute_totals,
    current_doc_daily_local_commute_totals,
    monthly_approved_totals,
    current_doc_monthly_totals,
    employee_grade,
    company,
    doc,
):
    """
    Processes validation for Local Commute expenses using daily allowance logic
    similar to food and lodging, plus monthly limit checks.
    """
    # Check if attachment is mandatory
    days = cint(days) or 1

    # ? GET IF ATTACHMENT IS REQUIRED BASED ON COMMUTE RULES
    custom_mode_of_vehicle = exp.custom_mode_of_vehicle
    if custom_mode_of_vehicle == "Non-Public" or custom_mode_of_vehicle == "Non Public":
        custom_mode_of_vehicle = "Private"
    attach_required = frappe.db.get_value(
        "Local Commute Details",
        {
            "grade": employee_grade,
            "mode_of_commute": custom_mode_of_vehicle,
            "type_of_commute": exp.custom_type_of_vehicle,
        },
        "attachment_mandatory",
    )

    # ? THROW ERROR IF ATTACHMENT IS REQUIRED BUT NOT PROVIDED
    if attach_required and not exp.custom_attachments:
        frappe.throw(
            f"Attachment required for Local Commute (Row #{idx}) as per commute rules."
        )

    # Calculate amount for non-public transport if not provided
    if exp.custom_mode_of_vehicle == COMMUTE_MODES["NON_PUBLIC"]:
        km = flt(exp.custom_km or 0) if exp.custom_manual_km <=0 else flt(exp.custom_manual_km)
        rate = km_rate_map.get(exp.custom_type_of_vehicle, 0)
        
        if exp.amount != rate*km:
            exp.amount = exp.sanctioned_amount = rate * km
            exp_amount = flt(exp.amount)

    daily_limit = flt(budget_row.get("local_commute_limit_daily", 0))
    monthly_limit = flt(budget_row.get("local_commute_limit_monthly", 0))

    daily_per_item_amount = exp_amount / days
    exceeded_daily = False
    exceeded_monthly = False

    # Check daily limits using logic similar to food/lodging
    for i in range(days):
        current_day = expense_date + timedelta(days=i)

        # Accumulate current document's expense for this day
        current_doc_daily_local_commute_totals[current_day] += daily_per_item_amount

        # Calculate cumulative daily total
        cumulative_daily_total = (
            daily_local_commute_totals[current_day]
            + current_doc_daily_local_commute_totals[current_day]
        )

        # Check if daily limit is exceeded
        if daily_limit and cumulative_daily_total > daily_limit:
            exceeded_daily = True
            break

    # Check monthly limit - simplified since no overlapping logic needed
    current_month_key = (expense_date.year, expense_date.month)
    current_doc_monthly_totals[current_month_key] += exp_amount

    approved_monthly_total = monthly_approved_totals.get(current_month_key, 0)
    cumulative_monthly_spend = (
        approved_monthly_total + current_doc_monthly_totals[current_month_key]
    )

    doc.custom_local_commute_monthly_balance = monthly_limit - cumulative_monthly_spend

    if monthly_limit and cumulative_monthly_spend > monthly_limit:
        exceeded_monthly = True

    # Flag as exception if any limit is exceeded
    if exceeded_daily or exceeded_monthly:
        if (not exp.custom_attachments):
            frappe.throw(
                f"Row #{exp.get('idx')}: Attachment is required as the expense exceeds limits."
            )

        exp.custom_is_exception = 1


def validate_attachments_compulsion(doc):
    """
    Enforces attachment requirement for expenses flagged as exceptions,
    specifically for the Indifoss company.
    """
    try:
        emp_company = frappe.db.get_value("Employee", doc.employee, "company")
        if not emp_company:
            frappe.throw(
                "Employee company not found. Please set the employee company first."
            )

        for expense in doc.expenses:
            if (expense.custom_is_exception == 1 or expense.expense_type == "Lodging" or expense.custom_supporting_document_available == 1) and not expense.custom_attachments:
                if expense.expense_type == "Lodging":
                    raise frappe.ValidationError(
                        f"Attachments are mandatory for the expense type '{expense.expense_type}' ")
                else:
                    raise frappe.ValidationError(
                        f"Attachments are mandatory for the expense type '{expense.expense_type}' "
                        f"when it exceeds the allowed budget. Please attach the necessary documents."
                    )
    except Exception as e:
        frappe.throw(str(e))


@frappe.whitelist()
def get_data_from_expense_claim_as_per_grade(employee, company):
    """
    Whitelisted function to retrieve allowed local commute options.
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
            elif option.mode_of_commute == "Private":
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
    for the month of the given expense_date, simplified without overlapping logic.
    """
    try:
        expense_date = getdate(expense_date)
        month_start = expense_date.replace(day=1)
        next_month = month_start + relativedelta(months=1)
        month_end = next_month - timedelta(days=1)
        grade, company = frappe.db.get_value('Employee', employee, ["grade", "company"])
        additional_filters = {}
        if grade:
            # ? FETCH TRAVEL BUDGET RECORD LINKED TO EMPLOYEE
            travel_budget_name = frappe.db.get_value(
                "Travel Budget", {"company": company}, "name"
            )

            if travel_budget_name:
                local_commute_entries = frappe.get_all(
                    "Local Commute Details",
                    filters={"parent": travel_budget_name, "grade": grade, "include_expenses":1},
                    fields=["mode_of_commute", "type_of_commute","include_expenses"],
                )
                if local_commute_entries:
                    type_of_commutes = []
                    for entry in local_commute_entries:
                        type_of_commutes.append(entry.type_of_commute)
                        
                    if type_of_commutes:
                        additional_filters["custom_type_of_vehicle"] = ["in", type_of_commutes]
                        
        filters = {
            "employee": employee,
            "approval_status": ["in", ["Draft", "Approved"]],
        }
        if current_doc_name:
            filters["name"] = ["!=", current_doc_name]

        all_approved_expense_claims = frappe.get_all(
            doctype="Expense Claim",
            filters=filters,
            pluck="name",
        )

        if not all_approved_expense_claims:
            return 0.0

        if expense_type == "Local Commute" and additional_filters:

            filters={
                    "expense_type": expense_type,
                    "parent": ["in", all_approved_expense_claims],
                    "expense_date": ["between", [month_start, month_end]],                    
            }
            filters.update(additional_filters)
            expense_claim_details = frappe.get_all(
                doctype="Expense Claim Detail",
                filters=filters,
                fields=["sanctioned_amount"],
            )
                
        else:
            expense_claim_details = frappe.get_all(
                doctype="Expense Claim Detail",
                filters={
                    "expense_type": expense_type,
                    "parent": ["in", all_approved_expense_claims],
                    "expense_date": ["between", [month_start, month_end]],
                },
                fields=["sanctioned_amount"],
            )

        total_sanctioned_amount = sum(
            flt(detail.sanctioned_amount or 0) for detail in expense_claim_details
        )

        return round(total_sanctioned_amount, 2)

    except Exception as e:
        frappe.throw(
            f"An error occurred while calculating approved monthly expenses: {e}"
        )


# ? FUNCTION TO FETCH TOTAL APPROVED 'LOCAL COMMUTE' EXPENSES FOR THE CURRENT MONTH FOR A GIVEN EMPLOYEE
def set_local_commute_expense_in_employee(employee):
    try:
        today_date = getdate(today())

        # ? GET TOTAL APPROVED EXPENSES
        monthly_expense = get_approved_category_monthly_expense(
            employee, today_date, expense_type="Local Commute"
        )

        # ? UPDATE ONLY THE CURRENT MONTH'S EXPENSE IN THE EMPLOYEE RECORD
        frappe.db.set_value(
            "Employee",
            employee,
            "custom_local_commute_current_month_wallet_expense",
            monthly_expense,
        )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "Error in set_local_commute_expense_in_employee"
        )


@frappe.whitelist()
def get_local_commute_expense_in_expense_claim(employee):
    try:
        # ? GET CURRENT MONTH'S EXPENSE + GRADE FROM EMPLOYEE
        fields = frappe.db.get_value(
            "Employee",
            employee,
            ["custom_local_commute_current_month_wallet_expense", "grade"],
            as_dict=True,
        )
        if not fields:
            return {}

        # ? FETCH BUDGET FROM BUDGET ALLOCATION USING GRADE
        budget = (
            frappe.db.get_value(
                "Budget Allocation",
                {"grade": fields.get("grade")},
                "local_commute_limit_monthly",
            )
            or 0
        )

        # ? CALCULATE REMAINING BUDGET
        remaining = max(
            0,
            budget
            - (fields.get("custom_local_commute_current_month_wallet_expense") or 0),
        )

        return {
            "monthly_expense": fields.custom_local_commute_current_month_wallet_expense
            or 0,
            "monthly_budget": budget,
            "remaining_budget": remaining,
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Error in get_local_commute_expense_in_expense_claim",
        )
        return {}



@frappe.whitelist()
def get_date_wise_da_hours(employee, from_date, to_date, company, expense_claim_name=None, type=None):
    """
    #! FETCHES DATE-WISE DAILY ALLOWANCE (DA) AND COMMUTE EXPENSE ENTRIES FOR AN EMPLOYEE

    This function calculates eligible DA and travel reimbursements based on field visits 
    completed by an employee between a given date range, excluding specific time ranges 
    defined in HR Settings. It handles:
    
    - Fetching eligible Field Visits
    - Calculating eligible hours after exclusions
    - Generating DA entries based on full/half day thresholds
    - Creating or appending to Expense Claim
    - Generating Local Commute expense entries
    - Providing a summary of entries added/skipped
    
    Args:
        employee (str): Employee ID.
        from_date (str): Start date of the range.
        to_date (str): End date of the range.
        company (str): Company name.
        expense_claim_name (str, optional): Existing Expense Claim name (if any).

    Returns:
        dict: {
            "expense_claim_name": str,
            "da_expense_rows": list,
            "commute_expense_rows": list,
            "summary_html": str
        }
    """

    try:

        meal_configs = fetch_meal_allowance_settings()
        
        # Loop through and use the configs
        for config in meal_configs:
            from_hours = config["from_hours"]
            to_hours = config["to_hours"]
            allowance = config["meal_allowance"]

        
        #? FETCH FIELD VISIT RECORDS WITHIN THE GIVEN DATE RANGE
        field_visits = frappe.db.get_all(
            "Field Visit",
            filters={
                "field_visited_by": employee,
                "status": "Visit Completed",
                "service_mode": "On Site(Customer Premise)"
            },
            or_filters=[
                ["visit_started", "between", [from_date, to_date]],
                ["visit_ended", "between", [from_date, to_date]],
            ],
            fields=["name", "visit_started", "visit_ended"]
        )

        #? INITIALIZE EMPTY LISTS FOR OUTPUT
        added_travel_entries = []
        da_expense_rows = []
        commute_expense_rows = []

        #? FETCH LATEST DA AMOUNT AND TRAVEL RATES FOR EMPLOYEE
        da_amount, private_service_rate = get_latest_travel_budget_and_rates(employee, company)
        
     
        # calculate daily hours (NO exclusion)
        date_wise_da_hours = calculate_date_wise_hours(field_visits, from_date, to_date)
        #? TRACK DUPLICATE TRAVEL ENTRIES (IF ANY)
        duplicates = []

        #! -------------------------------------------------------------------
        #! APPEND / CREATE EXPENSE CLAIM FOR DAILY ALLOWANCE (DA) ENTRIES
        #! -------------------------------------------------------------------
        expense_claim_doc, da_expense_rows, already_exists_dates, added_da_dates = build_da_expense_rows(
            date_wise_da_hours=date_wise_da_hours,
            da_amount=da_amount,
            employee=employee,
            expense_claim_name=expense_claim_name,
            visit_type="Field Visit"
        )

        #! -------------------------------------------------------------------
        #! GENERATE TRAVEL (LOCAL COMMUTE) EXPENSE CLAIM ENTRIES
        #! -------------------------------------------------------------------
        commute_expense_rows, added_travel_entries, duplicates = build_commute_expense_entries(
            field_visits=field_visits,
            private_service_rate=private_service_rate,
            expense_claim_doc=expense_claim_doc,
            from_date=from_date,
            to_date=to_date,
        )

        #! -------------------------------------------------------------------
        #! BUILD MESSAGES TO SHOW ENTRY SUMMARY TO THE USER
        #! -------------------------------------------------------------------
        messages = build_expense_notification_messages(
            added_da_dates=added_da_dates,
            added_travel_entries=added_travel_entries,
            already_exists_dates=already_exists_dates,
            duplicates=duplicates
        )

        #? RETURN FINAL RESULT WITH EXPENSE CLAIM NAME, ENTRIES, AND SUMMARY
        return {
            "expense_claim_name": expense_claim_doc.name,
            "da_expense_rows": da_expense_rows,
            "commute_expense_rows": commute_expense_rows,
            "summary_html": "<br><br>".join(messages) if messages else "No entries were added."
        }
    except Exception as e:
        frappe.throw(str(e))



def fetch_meal_allowance_settings():
    """
    FETCHES MEAL ALLOWANCE CONFIGURATIONS FROM HR SETTINGS CHILD TABLE.

    Returns:
        list[dict]: A list of dicts where each dict contains:
            - from_hours (float)
            - to_hours (float)
            - meal_allowance (float)
    """

    #! FETCH HR SETTINGS SINGLETON DOCUMENT
    hr_settings = frappe.get_single("HR Settings")

    #? GET CHILD TABLE
    meal_allowance_table = hr_settings.get("custom_meal_allowance_table")

    #! THROW ERROR IF CHILD TABLE IS EMPTY
    if not meal_allowance_table:
        frappe.throw("Please configure 'Meal Allowance Table' in HR Settings.")

    #? PARSE CHILD TABLE ROWS INTO LIST OF DICTS
    meal_allowance_configs = []
    for row in meal_allowance_table:
        meal_allowance_configs.append({
            "from_hours": row.from_no_of_hours_travel_per_day,
            "to_hours": row.to_no_of_hours_travel_per_day,
            "meal_allowance": row.meal_allowance,
        })

    return meal_allowance_configs


def build_commute_expense_entries(
    field_visits,
    private_service_rate,
    expense_claim_doc,
    from_date,
    to_date,
):
    """
    Build commute (local travel) expense entries from field visit data.

    Args:
        field_visits (list): List of Field Visit docs.
        private_service_rate (dict): Dictionary mapping vehicle types to per-km rates.
        expense_claim_doc (Document): The parent expense claim document.
        from_date (str): Start date (inclusive) for filtering expense dates.
        to_date (str): End date (inclusive) for filtering expense dates.

    Returns:
        tuple: (commute_expense_rows, added_travel_entries, duplicates)
    """

    # ? GET NAMES OF ALL FIELD VISITS
    field_visit_names = [fv.name for fv in field_visits]
    commute_expense_rows = []
    added_travel_entries = []
    duplicates = []
    # ? RETURN BLANK LIST IF NOT FIELD VISIT PRESENT
    if not field_visit_names:
        return commute_expense_rows, added_travel_entries, duplicates

    # ? GET CHILD TABLE DATAS FROM FIELD VISITS
    child_table_rows = frappe.get_all(
        "Field Visit Child Table",
        filters={"parent": ["in", field_visit_names]},
        fields=[
            "name", "service_call", "start_time", "end_time",
            "mode_of_vehicle", "type_of_vehicle", "travelled_km", "amount", "parent", "from_location", "to_location"
        ]
    )

    #! SET DEFAULT START AND END TIME TO FULL DAY RANGE
    default_start_time = time(0, 0, 0)       # 00:00:00
    default_end_time   = time(23, 59, 59)    # 23:59:59

    #? CREATE DEFAULT DICT FOR CALCULATING AMOUNT, KM, TIME, LOCATIONS,START TIME, END TIME FIELD VISITS AND SERVICE CALLS
    visit_map = defaultdict(lambda: {
        "amount": 0.0,
        "child_rows": set(),
        "travelled_km": 0.0,
        "start_time": default_start_time,
        "end_time": default_end_time,
        "from_location": None,
        "to_location": None
    })

    for row in child_table_rows:
        start_date = getdate(row.start_time)
        end_date = getdate(row.end_time)
        total_days = date_diff(end_date, start_date) + 1
        # ? GET START DAY INITIAL TIME AND END DAY FINAL TIME
        start_time = get_datetime(row.start_time).time()
        end_time = get_datetime(row.end_time).time()
        #? FOR PUBLIC VEHICLE AMOUNT IS ZERO AND TRAVEL KM IS ZERO (ADD MANUALLY)
        if row.mode_of_vehicle == "Public":
            daily_amount = 0.0
            daily_km = 0.0

        #? FOR OTHER VEHICLE TYPES CALCULATE PER DAY AMOUNT AND TRAVELLED KM
        elif row.mode_of_vehicle:
            rate = flt(private_service_rate.get(row.type_of_vehicle, 0))
            total_amount = flt(row.travelled_km) * rate
            daily_amount = total_amount / total_days
            daily_km = flt(row.travelled_km) / total_days
        else:
            daily_amount = 0.0
            daily_km = 0.0

        #? ADD AMOUNT, TRAVEL KM, SERVICE CALL, TIME, LOCATION IN VISIT_MAP DICT
        for i in range(total_days):
            visit_date = add_days(start_date, i)
            key = (visit_date, row.mode_of_vehicle, row.type_of_vehicle)
            visit_map[key]["amount"] += daily_amount
            visit_map[key]["travelled_km"] += daily_km
            visit_map[key]["child_rows"].add((row.service_call, row.parent, row.travelled_km, row.from_location, row.to_location))

            # ? ADD LOCATION TO DICT IF NOT ALREADY SET
            if not visit_map[key].get("from_location"):
                visit_map[key]["from_location"] = row.from_location

            if not visit_map[key].get("to_location"):
                visit_map[key]["to_location"] = row.to_location


            #? CHECK AND SET EARLIEST START TIME AND FROM LOCATION
            if visit_date == start_date:
                if (
                    start_time < visit_map[key].get("start_time") or visit_map[key].get("start_time") == default_start_time
                ):
                    visit_map[key]["start_time"] = start_time
                    visit_map[key]["from_location"] = row.from_location

            #? CHECK AND SET LATEST END TIME AND TO LOCATION
            if visit_date == end_date:
                if (
                    (end_time > visit_map[key].get("end_time") or visit_map[key].get("end_time") == default_end_time
                    )
                ):
                    visit_map[key]["end_time"] = end_time
                    visit_map[key]["to_location"] = row.to_location

    existing_keys = set()
    # ? FETCH ALL EXISTING EXPENSE CLAIM DETAIL OF CURRENT EXPENSE CLAIM
    existing_details = frappe.get_all(
        "Expense Claim Detail",
        filters={"parent": expense_claim_doc.name},
        fields=["expense_date", "custom_mode_of_vehicle", "custom_type_of_vehicle"]
    )
    for d in existing_details:
        existing_keys.add((
            getdate(d.expense_date),
            d.custom_mode_of_vehicle or "",
            d.custom_type_of_vehicle or "",
        ))

    base_url = frappe.utils.get_url()

    for key, data in visit_map.items():
        visit_date, mode, type_ = key
        # ? MAKE MODE PRIVATE FOR EXPENSE CLAIM DETAIL IF MODE IS NON PUBLIC OR PRIVATE
        if mode == "Non Public" or mode == "Private":
            mode = "Private"

        secondary_key = (visit_date, mode, type_)
        if secondary_key in existing_keys:
            duplicates.append(f"{visit_date} - {type_} - {mode}")
            continue

        if not (getdate(from_date) <= getdate(visit_date) <= getdate(to_date)):
            continue

        description = f"Travelled on {visit_date} via {mode} ({type_}) for local commute."

        field_visit_map = {}
        all_field_visits_set = set()
        all_service_calls_set = set()

        #? MAP FIELD VISITS TO SERVICE CALLS
        for service_call, field_visit, travelled_km, from_location, to_location in data["child_rows"]:
            field_visit_map.setdefault(field_visit, []).append({
                "service_call": service_call,
                "travelled_km": travelled_km or "0",
                "from_location": from_location or "-",
                "to_location": to_location or "-"
            })
            all_field_visits_set.add(field_visit)
            all_service_calls_set.add(service_call)

        #? HTML table generation
        table_rows = ""
        for field_visit, service_call_rows in sorted(field_visit_map.items()):
            rowspan = len(service_call_rows)
            for i, row_data in enumerate(service_call_rows):
                service_call = row_data["service_call"]
                from_location = row_data["from_location"]
                to_location = row_data["to_location"]
                travelled_km = row_data["travelled_km"]

                #? FETCH CUSTOMER ONLY
                customer = "-"
                sc_data = frappe.db.get_value(
                    "Service Call", service_call, ["customer"], as_dict=True
                )
                if sc_data and sc_data.get("customer"):
                    customer = sc_data.get("customer")
                    customer_name = frappe.db.get_value("Customer", customer, "customer_name")

                table_rows += "<tr>"
                if i == 0:
                    table_rows += f"""
                        <td rowspan="{rowspan}" style="border: 1px solid #000; padding: 8px;">
                            <a href="{base_url}/app/field-visit/{field_visit}" target="_blank">{field_visit}</a>
                        </td>
                    """
                table_rows += f"""
                    <td style="border: 1px solid #000; padding: 8px;">
                        <a href="{base_url}/app/service-call/{service_call}" target="_blank">{service_call}</a>
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">{from_location}</td>
                    <td style="border: 1px solid #000; padding: 8px;">{to_location}</td>
                    <td style="border: 1px solid #000; padding: 8px;">{travelled_km}</td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        <a href="{base_url}/app/customer/{customer}" target="_blank">{customer_name}</a>
                    </td>
                </tr>
                """

        #? Final HTML Table
        html_table = f"""
        <div class="ql-editor read-mode">
            <table style="border-collapse: collapse; width: 100%; font-size: 14px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Field Visit</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Service Call</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">From Location</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">To Location</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Travelled KM</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Customer</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """

        commute_expense_rows.append({
            "expense_date": visit_date,
            'custom_expense_end_date': visit_date,
            "expense_type": "Local Commute",
            "custom_mode_of_vehicle": mode,
            "custom_type_of_vehicle": type_,
            "custom_expense_start_time": data["start_time"],
            "custom_expense_end_time": data["end_time"],
            "custom_from_location": data["from_location"],
            "custom_to_location": data["to_location"],
            "custom_days": 1,
            "description": description,
            "custom_field_visit_and_service_call_details": html_table,
            "amount": data["amount"],
            "sanctioned_amount": data["amount"],
            "custom_km": data.get("travelled_km"),
            "custom_field_visits": ", ".join(sorted(all_field_visits_set)),
            "custom_service_calls": ", ".join(sorted(all_service_calls_set))
        })
        added_travel_entries.append(f"{visit_date} - {type_} - {mode}")

    return commute_expense_rows, added_travel_entries, duplicates

def get_latest_travel_budget_and_rates(employee, company):
    """
    FETCHES THE LATEST SUBMITTED TRAVEL BUDGET FOR THE GIVEN COMPANY AND RETURNS:
        - THE DA ALLOWANCE BASED ON EMPLOYEE'S GRADE
        - A DICTIONARY OF SERVICE TRAVEL TYPES AND THEIR RATE PER KM

    Args:
        employee (str): The employee ID or name.
        company (str): The company name to filter Travel Budgets.

    Returns:
        tuple[float, dict]: 
            - DA amount (float)
            - Private service rate dictionary (dict[str, float])
    """

    #! INITIALIZE RETURN VARIABLES
    da_amount = 0.0
    private_service_rate = {}

    #! FETCH LATEST SUBMITTED TRAVEL BUDGET DOCUMENT FOR THE GIVEN COMPANY
    travel_visit_doc = frappe.get_all(
        "Travel Budget",
        filters={"docstatus": 1, "company": company},
        fields=["name"],
        order_by="creation desc",
        limit=1
    )

    #? IF A TRAVEL BUDGET EXISTS
    if travel_visit_doc:
        #? GET EMPLOYEE GRADE
        employee_grade = frappe.get_value("Employee", employee, "grade")

        #? FETCH FULL TRAVEL BUDGET DOCUMENT
        travel_budget = frappe.get_doc("Travel Budget", travel_visit_doc[0].name)

        #? MATCH EMPLOYEE GRADE TO FIND APPLICABLE DA ALLOWANCE
        if employee_grade:
            for budget in travel_budget.buget_allocation:
                if employee_grade == budget.grade:
                    da_amount = budget.da_allowance
                    break

        #? BUILD PRIVATE SERVICE RATE DICTIONARY
        for service in travel_budget.service_km_rate:
            if service.type_of_travel not in private_service_rate:
                private_service_rate[service.type_of_travel] = service.rate_per_km

    #! RETURN THE DA AMOUNT AND SERVICE RATES
    return da_amount, private_service_rate

def calculate_date_wise_hours(visits, from_date, to_date, start_key="visit_started", end_key="visit_ended", start_time_key = None, end_time_key=None):
    """
    CALCULATE DATE-WISE HOURS FROM VISITS (DISTRIBUTED ACROSS MULTIPLE DAYS).
    """

    date_wise_data = defaultdict(lambda: {
        "hours": 0.0,
        "visits": set(),
        "earliest_start": None,
        "latest_end": None
    })

    for visit in visits:
        # ! FOR TOUR VISIT FIELD IS NOT DATETIME BUT DATE AND TIME FIELDS ARE DIFFERENT HENCE COMBINE THE<
        if start_key == "tour_start_date" and end_key == "tour_end_date":
            # ? GET START TIME KEY AND END TIME KEY
            if start_time_key is None:
                start_time_key = "tour_start_date_time"
            if end_time_key is None:
                end_time_key = "tour_end_date_time"

            start_time = visit[start_time_key]
            end_time = visit[end_time_key]

            # ? IF START TIME OR END TIME IS NONE FALL TO DEFAULT VALUES
            if start_time is None:
                start_time = time(0, 0, 0)
            if end_time is None:
                end_time = time(23, 59, 59)

            # ? CONVERT START TIME AND END TIME TO TIME FORMAT
            if isinstance(start_time, str):
                start_time = datetime.strptime(start_time, '%H:%M:%S').time()
            if isinstance(end_time, str):
                end_time = datetime.strptime(end_time, '%H:%M:%S').time()

            
            if isinstance(start_time, timedelta):
                start_time = (datetime.min + start_time).time()
            if isinstance(end_time, timedelta):
                end_time = (datetime.min + end_time).time()

            # ? COMBINE START DATE AND START TIME, END DATE AND END TIME
            tour_visit_start_time = datetime.combine(getdate(visit[start_key]), start_time)
            tour_visit_end_time = datetime.combine(getdate(visit[end_key]), end_time)
            start_dt = get_datetime(max(tour_visit_start_time, get_datetime(from_date)))
            end_dt = get_datetime(min(tour_visit_end_time, datetime.combine(getdate(to_date), time(23, 59, 59))))
        else:
            start_dt = get_datetime(max(visit[start_key], get_datetime(from_date)))
            end_dt = get_datetime(min(visit[end_key], datetime.combine(getdate(to_date), time(23, 59, 59))))

        current = start_dt
        while current < end_dt:
            day = current.date()
            # end of this day or visit end, whichever comes first
            day_end = datetime.combine(day, time.max)
            segment_end = min(day_end, end_dt)

            duration_hours = round((segment_end - current).total_seconds() / 3600, 2)
            date_str = str(day)

            data = date_wise_data[date_str]
            data["hours"] += duration_hours
            data["visits"].add(visit["name"])

            start_time = current.time()
            end_time = segment_end.time()

            if not data["earliest_start"] or start_time < data["earliest_start"]:
                data["earliest_start"] = start_time
            if not data["latest_end"] or end_time > data["latest_end"]:
                data["latest_end"] = end_time

            # move to next day
            current = segment_end + timedelta(seconds=1)

    return date_wise_data


def build_da_expense_rows(
    date_wise_da_hours,
    da_amount,
    employee,
    expense_claim_name=None,
    visit_type="Field Visit"
):
    """
    BUILDS DA EXPENSE ROWS BASED ON DATE-WISE HOURS AND MEAL ALLOWANCE CONFIGS.
    """

    already_exists_dates = []
    added_da_dates = [] 
    da_expense_rows = []

    #! FETCH MEAL ALLOWANCE CONFIGS
    meal_configs = fetch_meal_allowance_settings()
    meal_configs = sorted(meal_configs, key=lambda x: x["from_hours"])  # ensure ascending order

    #! GET OR CREATE EXPENSE CLAIM DOC
    if expense_claim_name:
        expense_claim_doc = frappe.get_doc("Expense Claim", expense_claim_name)
    else:
        latest_ec = frappe.get_all(
            "Expense Claim",
            filters={"employee": employee, "approval_status": "Draft"},
            order_by="posting_date desc",
            limit=1,
            fields=["name"]
        )
        if latest_ec:
            expense_claim_doc = frappe.get_doc("Expense Claim", latest_ec[0].name)
        else:
            expense_claim_doc = frappe.get_doc({
                "doctype": "Expense Claim",
                "employee": employee,
                "approval_status": "Draft",
                "custom_type": visit_type,
                "expenses": []
            })

    #! PROCESS EACH DATE
    for date, data in date_wise_da_hours.items():
        hours = data["hours"]
        if hours <= 0:
            continue

        #! FIND MATCHED CONFIG
        matched_config = None
        for config in meal_configs:
            if config["from_hours"] <= hours <= config["to_hours"]:
                matched_config = config
                break

        if not matched_config:
            continue  # no config matched → skip

        percentage = matched_config["meal_allowance"]
        amount = round((da_amount * percentage) / 100, 2)

        #! VALIDATION ONLY WORKS FOR SAME-TYPE ENTRIES
        if visit_type == "Field Visit":
            already_exists = any(
                exp.expense_type == "DA" and str(exp.expense_date) == str(date) and exp.custom_field_visits
                for exp in expense_claim_doc.expenses
            )
        else:
            already_exists = any(
                exp.expense_type == "DA" and str(exp.expense_date) == str(date) and not exp.custom_field_visits
                for exp in expense_claim_doc.expenses
            )

        if already_exists:
            already_exists_dates.append(str(date))
            continue

        if amount > 0:
            #! BASE EXPENSE ROW
            expense_row = {
                "expense_type": "DA",
                "expense_date": getdate(date),
                "custom_expense_end_date": getdate(date),
                "amount": amount,
                "sanctioned_amount": amount,
                "custom_days": 1,   # now always "per day" since hours are already split
                "custom_mode_of_vehicle": "",
                "custom_type_of_vehicle": "",
                "custom_expense_start_time": data.get("earliest_start"),
                "custom_expense_end_time": data.get("latest_end"),
                "description": f"{percentage}% DA - {date}"
            }

            #? ONLY FOR FIELD VISIT: ADD FIELD VISIT → SERVICE CALL MAPPING + HTML
            if visit_type == "Field Visit":
                base_url = frappe.utils.get_url()
                all_field_visits_set = set()
                all_service_calls_set = set()
                field_visit_map = {}

                for fv_name in data["visits"]:
                    field_visit_doc = frappe.get_doc("Field Visit", fv_name)
                    all_field_visits_set.add(fv_name)
                    for row in field_visit_doc.service_calls:
                        if row.service_call:
                            field_visit_map.setdefault(fv_name, []).append({
                                "service_call": row.service_call,
                                "from_location": row.from_location or "-",
                                "to_location": row.to_location or "-",
                                "travelled_km": row.travelled_km or "0"
                            })
                            all_service_calls_set.add(row.service_call)

                # build table rows
                table_rows = ""
                for field_visit, service_call_rows in sorted(field_visit_map.items()):
                    rowspan = len(service_call_rows)
                    for i, row_data in enumerate(service_call_rows):
                        service_call = row_data["service_call"]
                        from_location = row_data["from_location"]
                        to_location = row_data["to_location"]
                        travelled_km = row_data["travelled_km"]

                        # fetch customer
                        customer = "-"
                        customer_name = "-"
                        sc_data = frappe.db.get_value(
                            "Service Call", service_call, ["customer"], as_dict=True
                        )
                        if sc_data and sc_data.get("customer"):
                            customer = sc_data.get("customer")
                            customer_name = frappe.db.get_value("Customer", customer, "customer_name")

                        table_rows += "<tr>"
                        if i == 0:
                            table_rows += f"""
                                <td rowspan="{rowspan}" style="border: 1px solid #000; padding: 8px;">
                                    <a href="{base_url}/app/field-visit/{field_visit}" target="_blank">{field_visit}</a>
                                </td>
                            """
                        table_rows += f"""
                            <td style="border: 1px solid #000; padding: 8px;">
                                <a href="{base_url}/app/service-call/{service_call}" target="_blank">{service_call}</a>
                            </td>
                            <td style="border: 1px solid #000; padding: 8px;">{from_location}</td>
                            <td style="border: 1px solid #000; padding: 8px;">{to_location}</td>
                            <td style="border: 1px solid #000; padding: 8px;">{travelled_km}</td>
                            <td style="border: 1px solid #000; padding: 8px;">
                                <a href="{base_url}/app/customer/{customer}" target="_blank">{customer_name}</a>
                            </td>
                        </tr>
                        """

                html_table = f"""
                <div class="ql-editor read-mode">
                    <table style="border-collapse: collapse; width: 100%; font-size: 14px;">
                        <thead>
                            <tr style="background-color: #f5f5f5;">
                                <th style="border: 1px solid #000; padding: 8px;">Field Visit</th>
                                <th style="border: 1px solid #000; padding: 8px;">Service Call</th>
                                <th style="border: 1px solid #000; padding: 8px;">From Location</th>
                                <th style="border: 1px solid #000; padding: 8px;">To Location</th>
                                <th style="border: 1px solid #000; padding: 8px;">Travelled KM</th>
                                <th style="border: 1px solid #000; padding: 8px;">Customer</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
                """

                expense_row.update({
                    "custom_field_visit_and_service_call_details": html_table,
                    "custom_field_visits": ", ".join(sorted(all_field_visits_set)),
                    "custom_service_calls": ", ".join(sorted(all_service_calls_set)),
                })

            # ? ONLY FOR TOUR VISIT
            elif visit_type == "Tour Visit":
                base_url = frappe.utils.get_url()
                all_tour_visit_set = set()
                tour_visit_map = {}
                
                for visit in data["visits"]:
                    all_tour_visit_set.add(visit)

                    # ? FETCH CUSTOMER LINKED TO THIS TOUR VISIT
                    customer = frappe.db.get_value("Tour Visit", visit, "customer")
                    if not customer:
                        continue

                    customer_name = frappe.db.get_value("Customer", customer, "customer_name") or "-"

                    # Store visit mapping (no list, just dict)
                    tour_visit_map[visit] = {
                        "tour_visit": visit,
                        "customer": customer,
                        "customer_name": customer_name
                    }

                all_tour_visits = ", ".join(sorted(all_tour_visit_set))
                tour_table_rows = ""
                tour_html_table = ""

                if tour_visit_map:
                    tour_table_rows = ""

                    for tour_visit, row in sorted(tour_visit_map.items()):
                        tour_name = row["tour_visit"]
                        customer = row["customer"]
                        customer_name = row["customer_name"]

                        tour_table_rows += f"""
                            <tr>
                                <td style="border: 1px solid #000; padding: 6px; text-align: left; white-space: nowrap;">
                                    <a href="{base_url}/app/tour-visit/{tour_name}" target="_blank">{tour_name}</a>
                                </td>
                                <td style="border: 1px solid #000; padding: 6px; text-align: left; white-space: nowrap;">
                                    <a href="{base_url}/app/customer/{customer}" target="_blank">{customer_name}</a>
                                </td>
                            </tr>
                        """

                    # CREATE FULL HTML TABLE IF ANY ROWS EXIST
                    if tour_table_rows:
                        tour_html_table = f"""
                        <div class="ql-editor read-mode">
                            <table style="width: 100%; border-collapse: collapse; font-size: 13px; table-layout: auto;">
                                <thead>
                                    <tr style="background-color: #f5f5f5;">
                                        <th style="border: 1px solid #000; padding: 6px; text-align: left;">Tour Visit</th>
                                        <th style="border: 1px solid #000; padding: 6px; text-align: left;">Customer</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {tour_table_rows}
                                </tbody>
                            </table>
                        </div>
                        """


                if all_tour_visit_set:
                    expense_row.update({
                        "custom_tour_visits": all_tour_visits,
                        "custom_tour_visit_details": tour_html_table
                    })
            da_expense_rows.append(expense_row)
            added_da_dates.append(str(date))

    return expense_claim_doc, da_expense_rows, already_exists_dates, added_da_dates



def build_expense_notification_messages(
    added_da_dates=None,
    already_exists_dates=None,
):
    """
    BUILDS NOTIFICATION MESSAGES FOR EXPENSE CLAIM OPERATIONS.

    Args:
        added_da_dates (list): Dates where DA was successfully added.
        added_travel_entries (list): Dates where travel entries were successfully added.
        already_exists_dates (list): Dates where DA already existed and was skipped.
        duplicates (list): Travel entries that already existed and were skipped.

    Returns:
        list: A list of HTML-formatted notification strings.
    """

    #! INITIALIZE MESSAGE LIST
    messages = []

    #? ENSURE NONE ARE NULL
    added_da_dates = added_da_dates or []
    already_exists_dates = already_exists_dates or []

    #? SUCCESSFUL DA ENTRIES
    if added_da_dates:
        messages.append(
            "Daily Allowance (DA) has been successfully added for the following dates:<br><b>{}</b>".format(
                ", ".join(added_da_dates)
            )
        )

    #? ALREADY PRESENT DA ENTRIES
    if already_exists_dates:
        messages.append(
            "DA was already recorded for the following dates and was not added again:<br><b>{}</b>".format(
                ", ".join(already_exists_dates)
            )
        )


    return messages



@frappe.whitelist()
def get_service_calls_from_field_visits(field_visits, txt=None):
    """
    Return unique Service Calls from child table of selected Field Visit records.
    """
    if isinstance(field_visits, str):
        field_visits = json.loads(field_visits)

    if not field_visits:
        return []

    service_calls = frappe.get_all(
        "Field Visit Child Table",
        filters={"parent": ["in", field_visits]},
        fields=["service_call"],
    )

    unique_service_calls = list({sc.service_call for sc in service_calls if sc.service_call})

    if txt:
        unique_service_calls = [sc for sc in unique_service_calls if txt.lower() in sc.lower()]

    return [{"name": sc} for sc in unique_service_calls]


@frappe.whitelist()
def get_field_visit_service_call_details(field_visits, service_calls):
    """
    Returns:
    - custom_field_visit (comma-separated)
    - custom_service_call (comma-separated)
    - html_table: rowspan-based service call table
    """

    if isinstance(field_visits, str):
        field_visits = json.loads(field_visits)
    if isinstance(service_calls, str):
        service_calls = json.loads(service_calls)

    base_url = frappe.utils.get_url()
    details = []
    table_rows = ""

    for field_visit in field_visits:
        #? Get matching child records for this field visit
        children = frappe.get_all(
            "Field Visit Child Table",
            filters={
                "parent": field_visit,
                "service_call": ["in", service_calls]
            },
            fields=[
                "service_call",
                "from_location",
                "to_location",
                "travelled_km"
            ],
            order_by="service_call asc"
        )

        rowspan = len(children) or 1

        if children:
            for i, child in enumerate(children):
                service_call = child.service_call
                from_location = child.from_location or ""
                to_location = child.to_location or ""
                travelled_km = child.travelled_km or 0

                #? Get customer from Service Call
                customer = frappe.db.get_value("Service Call", service_call, "customer") or "None"
                customer_name = frappe.db.get_value("Customer", customer, "customer_name")

                #? Build details dict
                details.append({
                    "field_visit": field_visit,
                    "service_call": service_call,
                    "from_location": from_location,
                    "to_location": to_location,
                    "travelled_km": travelled_km,
                    "customer": customer
                })

                #? Build HTML row
                table_rows += "<tr>"
                if i == 0:
                    table_rows += f"""
                        <td rowspan="{rowspan}" style="border: 1px solid #000; padding: 8px;">
                            <a href="{base_url}/app/field-visit/{field_visit}" target="_blank">{field_visit}</a>
                        </td>
                    """
                table_rows += f"""
                    <td style="border: 1px solid #000; padding: 8px;">
                        <a href="{base_url}/app/service-call/{service_call}" target="_blank">{service_call}</a>
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">{from_location}</td>
                    <td style="border: 1px solid #000; padding: 8px;">{to_location}</td>
                    <td style="border: 1px solid #000; padding: 8px;">{travelled_km}</td>
                    <td style="border: 1px solid #000; padding: 8px;">
                        <a href="{base_url}/app/customer/{customer}" target="_blank">{customer_name}</a>
                    </td>
                </tr>
                """
        else:
            #? No matching service call for this field visit, render "None"
            details.append({
                "field_visit": field_visit,
                "service_call": "",
                "from_location": "",
                "to_location": "",
                "travelled_km": 0,
                "customer": ""
            })
            table_rows += f"""
                <tr>
                    <td rowspan="1" style="border: 1px solid #000; padding: 8px;">
                        <a href="{base_url}/app/field-visit/{field_visit}" target="_blank">{field_visit}</a>
                    </td>
                    <td style="border: 1px solid #000; padding: 8px;">None</td>
                    <td style="border: 1px solid #000; padding: 8px;">None</td>
                    <td style="border: 1px solid #000; padding: 8px;">None</td>
                    <td style="border: 1px solid #000; padding: 8px;">0</td>
                    <td style="border: 1px solid #000; padding: 8px;">None</td>
                </tr>
            """

    html_table = f"""
        <div class="ql-editor read-mode">
            <table style="border-collapse: collapse; width: 100%; font-size: 14px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Field Visit</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Service Call</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">From Location</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">To Location</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Travelled KM</th>
                        <th style="border: 1px solid #000; padding: 8px; text-align: left;">Customer</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    """

    return {
        "custom_field_visit": ", ".join(field_visits),
        "custom_service_call": ", ".join(service_calls),
        "custom_field_visit_and_service_call_details": html_table
    }

def validate_field_visits_timing(start_date, end_date, start_time, end_time, field_visits_csv):
    """
    VALIDATE WHETHER THE GIVEN DATE AND TIME RANGE IS WITHIN THE BOUNDS
    OF THE PROVIDED COMMA-SEPARATED FIELD VISIT NAMES.

    ARGS:
        START_DATE (STR): START DATE (YYYY-MM-DD)
        END_DATE (STR): END DATE (YYYY-MM-DD)
        START_TIME (STR): START TIME (HH:MM:SS)
        END_TIME (STR): END TIME (HH:MM:SS)
        FIELD_VISITS_CSV (STR): COMMA-SEPARATED STRING OF FIELD VISIT NAMES

    RAISES:
        FRAPPE.VALIDATIONERROR: IF THE GIVEN TIME RANGE IS NOT FULLY WITHIN THE BOUNDS OF ALL FIELD VISITS
    """

    field_visits = [fv.strip() for fv in field_visits_csv.split(",") if fv.strip()]
    if not field_visits:
        return

    #! FETCH ALL START AND END DATETIMES
    visit_times = frappe.get_all(
        "Field Visit",
        filters={"name": ["in", field_visits]},
        fields=["visit_started", "visit_ended"]
    )

    #! INITIALIZE EARLIEST/LATEST
    earliest_start = None
    latest_end = None

    for vt in visit_times:
        if vt.visit_started and (earliest_start is None or vt.visit_started < earliest_start):
            earliest_start = vt.visit_started
        if vt.visit_ended and (latest_end is None or vt.visit_ended > latest_end):
            latest_end = vt.visit_ended

    #? PARSE GIVEN RANGE
    given_start = get_datetime(f"{start_date} {start_time or '00:00:00'}")
    given_end = get_datetime(f"{end_date} {end_time or '23:59:59'}")

    #! VALIDATE
    if not (earliest_start and latest_end):
        return "One or more Field Visits have missing start or end times."

    if not (earliest_start <= given_start <= latest_end) or not (earliest_start <= given_end <= latest_end):
        return (
            f"The provided time range ({given_start} to {given_end}) "
            f"is not within the bounds of the linked Field Visits:\n"
            f"Earliest Start: {earliest_start}, Latest End: {latest_end}"
        )

    return None

def parse_date_safely(date_value):
    """
    SAFELY PARSES A DATE STRING OR OBJECT USING GETDATE.
    RETURNS A DEFAULT CURRENT DATE IF PARSING FAILS.
    """
    if not date_value:
        return getdate()

    try:
        return getdate(date_value)
    except Exception:
        return getdate()

def sort_expense_claim_data(doc, method=None):
    if not doc.expenses:
        return

    sorted_expenses = sorted(
        doc.expenses,
        key=lambda x: parse_date_safely(x.expense_date)
    )

    doc.expenses = []
    for i, row in enumerate(sorted_expenses, start=1):
        row.idx = i
        doc.append("expenses", row)


def build_expense_notification_messages(
    added_da_dates=None,
    added_travel_entries=None,
    already_exists_dates=None,
    duplicates=None
):
    """
    BUILDS NOTIFICATION MESSAGES FOR EXPENSE CLAIM OPERATIONS.

    Args:
        added_da_dates (list): Dates where DA was successfully added.
        added_travel_entries (list): Dates where travel entries were successfully added.
        already_exists_dates (list): Dates where DA already existed and was skipped.
        duplicates (list): Travel entries that already existed and were skipped.

    Returns:
        list: A list of HTML-formatted notification strings.
    """

    #! INITIALIZE MESSAGE LIST
    messages = []

    #? ENSURE NONE ARE NULL
    added_da_dates = added_da_dates or []
    added_travel_entries = added_travel_entries or []
    already_exists_dates = already_exists_dates or []
    duplicates = duplicates or []

    #? SUCCESSFUL DA ENTRIES
    if added_da_dates:
        messages.append(
            "Daily Allowance (DA) has been successfully added for the following dates:<br><b>{}</b>".format(
                ", ".join(added_da_dates)
            )
        )

    #? SUCCESSFUL LOCAL COMMUTE ENTRIES
    if added_travel_entries:
        messages.append(
            "Local Commute travel entries have been added for the following dates:<br><b>{}</b>".format(
                "<br>".join(added_travel_entries)
            )
        )

    #? ALREADY PRESENT DA ENTRIES
    if already_exists_dates:
        messages.append(
            "DA was already recorded for the following dates and was not added again:<br><b>{}</b>".format(
                ", ".join(already_exists_dates)
            )
        )

    #? DUPLICATE LOCAL COMMUTE ENTRIES
    if duplicates:
        messages.append(
            "Local Commute entries already existed for the following and were not added again:<br><br>{}".format(
                "<br>".join(duplicates)
            )
        )

    return messages

@frappe.whitelist()
def get_tour_visit_details(tour_visits):
    """
    RETURNS:
    - CUSTOM_TOUR_VISITS (COMMA-SEPARATED)
    - HTML_TABLE: ROWSPAN-BASED TOUR-VISIT TABLE
    """

    if isinstance(tour_visits, str):
        tour_visits = json.loads(tour_visits)

    base_url = frappe.utils.get_url()
    tour_visit_map = {}

    for visit in tour_visits:
        # ? FETCH CUSTOMER LINKED TO THIS TOUR VISIT
        customer = frappe.db.get_value("Tour Visit", visit, "customer")
        if not customer:
            continue

        customer_name = frappe.db.get_value("Customer", customer, "customer_name") or "-"

        # ? STORE TOUR VISIT MAPPING (NO LIST, JUST DICT)
        tour_visit_map[visit] = {
            "tour_visit": visit,
            "customer": customer,
            "customer_name": customer_name
        }

    tour_table_rows = ""
    tour_html_table = ""

    if tour_visit_map:
        tour_table_rows = ""

        for tour_visit, row in sorted(tour_visit_map.items()):
            tour_name = row["tour_visit"]
            customer = row["customer"]
            customer_name = row["customer_name"]

            tour_table_rows += f"""
                <tr>
                    <td style="border: 1px solid #000; padding: 6px; text-align: left; white-space: nowrap;">
                        <a href="{base_url}/app/tour-visit/{tour_name}" target="_blank">{tour_name}</a>
                    </td>
                    <td style="border: 1px solid #000; padding: 6px; text-align: left; white-space: nowrap;">
                        <a href="{base_url}/app/customer/{customer}" target="_blank">{customer_name}</a>
                    </td>
                </tr>
            """

        # ? CREATE FULL HTML TABLE IF ANY ROWS EXIST
        if tour_table_rows:
            tour_html_table = f"""
            <div class="ql-editor read-mode">
                <table style="width: 100%; border-collapse: collapse; font-size: 13px; table-layout: auto;">
                    <thead>
                        <tr style="background-color: #f5f5f5;">
                            <th style="border: 1px solid #000; padding: 6px; text-align: left;">Tour Visit</th>
                            <th style="border: 1px solid #000; padding: 6px; text-align: left;">Customer</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tour_table_rows}
                    </tbody>
                </table>
            </div>
            """


    return {
        "custom_tour_visits": ", ".join(tour_visits),
        "custom_tour_visit_details": tour_html_table
    }


@frappe.whitelist()
def process_tour_visit_da(employee, company, from_date, to_date, expense_claim_name=None, type=None):
    """
    #! PROCESS DAILY ALLOWANCE (DA) FOR A GIVEN TOUR VISIT

    This function calculates eligible Daily Allowance (DA) hours for an employee's Tour Visit,
    excludes time within configured thresholds, checks eligibility for full/half DA based on duration,
    and prepares expense claim entries accordingly.

    Args:
        employee (str): The employee ID for whom DA is to be processed.
        company (str): The company name of the employee.
        tour_visit_name (str): The name of the Tour Visit DocType record.
        expense_claim_name (str, optional): If provided, adds DA to an existing Expense Claim.

    Returns:
        dict: Contains a list of DA expense rows and an HTML summary of the entries added or skipped.
    """
    try:

        #? FETCH LATEST DA AMOUNT AND LOCAL COMMUTE RATE FROM TRAVEL BUDGET
        da_amount, private_service_rate = get_latest_travel_budget_and_rates(employee, company)

        #? FETCH FIELD VISIT RECORDS WITHIN THE GIVEN DATE RANGE
        tour_visits = frappe.db.get_all(
            "Tour Visit",
            filters={
                "person": employee,
                "status": "Completed",
            },
            or_filters=[
                ["tour_start_date", "between", [from_date, to_date]],
                ["tour_end_date", "between", [from_date, to_date]],
            ],
            fields=["name", "tour_start_date", "tour_end_date", "customer", "tour_start_date_time", "tour_end_date_time"]
        )
        #? CALCULATE ELIGIBLE HOURS PER DAY AFTER APPLYING EXCLUDE TIME RANGE
        date_wise_da_hours = calculate_date_wise_hours(
            visits=tour_visits,
            from_date=getdate(from_date),
            to_date=getdate(to_date),
            start_key="tour_start_date",
            end_key="tour_end_date",
            start_time_key = "tour_start_date_time",
            end_time_key = "tour_end_date_time"
        )

        #? BUILD EXPENSE CLAIM ROWS BASED ON ELIGIBLE HOURS AND THRESHOLDS
        expense_claim_doc, da_expense_rows, already_exists_dates, added_da_dates = build_da_expense_rows(
            date_wise_da_hours=date_wise_da_hours,
            da_amount=da_amount,
            employee=employee,
            expense_claim_name=expense_claim_name,
            visit_type="Tour Visit"
        )

        #? PREPARE HTML MESSAGES TO SUMMARIZE WHAT WAS ADDED OR SKIPPED
        messages = build_expense_notification_messages(
            added_da_dates=added_da_dates,
            added_travel_entries=[],
            already_exists_dates=already_exists_dates,
            duplicates=[]
        )

        #? RETURN FINAL OUTPUT
        return {
            "da_expense_rows": da_expense_rows,
            "summary_html": "<br><br>".join(messages) if messages else "No entries were added."
        }

    except Exception as e:
        frappe.throw(str(e))


def get_allowance_budgets(employee_grade, company, expense_type, metro):
    """
    FETCHES THE LATEST ALLOWANCE BUDGET FOR THE GIVEN EMPLOYEE GRADE, COMPANY, AND EXPENSE TYPE.
    """
    #! FETCH LATEST SUBMITTED TRAVEL BUDGET DOCUMENT FOR THE GIVEN COMPANY
    travel_budget_docs = frappe.get_all(
        "Travel Budget",
        filters={"docstatus": 1, "company": company},
        fields=["name"],
        order_by="creation desc",
        limit=1
    )

    if not travel_budget_docs:
        return 0  # ! NO TRAVEL BUDGET FOUND

    travel_budget_name = travel_budget_docs[0].name

    #! FETCH BUDGET ALLOCATION FOR GIVEN GRADE
    budget_allocations = frappe.get_all(
        "Budget Allocation",
        filters={
            "parent": travel_budget_name,  # ! CORRECT FIELD
            "parenttype": "Travel Budget",
            "grade": employee_grade
        },
        fields=["*"],
        order_by="creation desc",
        limit=1
    )

    if not budget_allocations:
        return 0  # ! NO ALLOCATION FOUND

    budget = budget_allocations[0]

    #! DETERMINE FIELD KEY BASED ON EXPENSE TYPE
    if expense_type == "DA":
        key = "da_allowance"
    elif expense_type == "Local Commute":
        key = "local_commute_limit_monthly"
    elif expense_type == "Food":
        key = "meal_allowance_metro" if metro else "meal_allowance_non_metro"
    elif expense_type == "Lodging":
        key = "lodging_allowance_metro" if metro else "lodging_allowance_non_metro"
    else:
        return 0  # ! EXPENSE TYPE NOT RECOGNIZED

    return budget.get(key, 0)

@frappe.whitelist()
def get_travel_request_details(employee):
    """
    Fetches travel request details for the given employee and date range.
    Each parent record includes travel itinerary, costing, and workflow state.
    """
    # Get all travel requests avoiding rejected states
    travel_requests = frappe.get_all(
        "Travel Request",
        filters={
            "employee": employee,
            "workflow_state": ["not in", ["Rejected by Reporting Manager", "Rejected by BU Head"]],
        },
        fields=["name", "workflow_state"]
    )

    result = []
    # Get only fields allowed in list view for itinerary and costing
    itinerary_meta = frappe.get_meta("Travel Itinerary")
    itinerary_fields = [
        df.fieldname
        for df in itinerary_meta.fields
        if df.fieldname and getattr(df, "in_list_view", 0) == 1
    ]
    # Get corresponding labels for each field
    travel_itineraries_label = [
        df.label
        for df in itinerary_meta.fields
        if df.fieldname in itinerary_fields
    ]

    costing_meta = frappe.get_meta("Travel Request Costing")
    costing_fields = [
        df.fieldname
        for df in costing_meta.fields
        if df.fieldname and getattr(df, "in_list_view", 0) == 1
    ]


    # Get corresponding labels for each field
    cost_data_label = [
        df.label
        for df in costing_meta.fields
        if df.fieldname in costing_fields
    ]

    for request in travel_requests:
        # Get itineraries for current parent request in range
        itineraries = frappe.get_all(
            "Travel Itinerary",
            filters={
                "parent": request["name"],
            },
            fields=itinerary_fields
        )
        # Get costings for current parent request
        costings = frappe.get_all(
            "Travel Request Costing",
            filters={"parent": request["name"]},
            fields=costing_fields
        )
        # Structure parent dict
        parent_dict = {
            "parent": request["name"],
            "travel_itinerary_data": itineraries,
            "travel_itinerary_label": travel_itineraries_label,
            "cost_data_label":cost_data_label,
            "cost_data": costings,
            "workflow_state": request["workflow_state"]
        }
        result.append(parent_dict)

    # Return the list of parent dicts
    return result

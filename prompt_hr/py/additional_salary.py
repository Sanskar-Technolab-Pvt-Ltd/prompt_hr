import frappe
from datetime import datetime, date
import calendar

# ?  BEFORE SAVE HOOK
def before_save(doc, method):
     
    # ? EXTRACT DAY OF THE WEEK FROM PAYROLL DATE
    if doc.custom_recurring == 1 and doc.custom_recurring_frequency == "Weekly":
        doc.custom_weekly_frequency_day = get_day_from_date(doc.payroll_date)


# ? FUNCTION TO EXTRACT DAY OF THE WEEK FROM PAYROLL DATE
def get_day_from_date(payroll_date):
    # ? ENSURE PAYROLL_DATE IS A DATETIME OBJECT
    if isinstance(payroll_date, str):
        payroll_date = datetime.strptime(payroll_date, "%Y-%m-%d")
    
    # ? GET DAY OF THE WEEK (0 = Monday, 6 = Sunday)
    day_of_week = payroll_date.weekday()
    
    # ? OPTIONAL: CONVERT DAY OF WEEK TO A HUMAN-READABLE FORMAT (e.g., "Monday", "Tuesday")
    day_name = payroll_date.strftime("%A")
    
    # ? PRINT THE DAY FOR DEBUGGING (REMOVE IN PRODUCTION)
    print(f"Payroll date: {payroll_date}, Day of the week: {day_name} ({day_of_week})")
    
    return day_name  


# ! prompt_hr.py.additional_salary.get_recurring_salaries
# ? FUNCTION TO FETCH RECURRING ADDITIONAL SALARY RECORDS MARKED AS CUSTOM RECURRING
@frappe.whitelist()
def get_recurring_salaries():
    
    return frappe.get_all(
        "Additional Salary",
        filters={"custom_recurring": 1},
        fields=[
            "name",
            "employee",
            "company",
            "salary_component",
            "payroll_date",
            "deduct_full_tax_on_selected_payroll_date",
            "overwrite_salary_structure_amount",
            "amount",
            "custom_recurring_frequency",
        ],
    )

# ? FUNCTION TO CALCULATE ELIGIBLE DATE BASED ON FREQUENCY
def get_eligible_date(payroll_date, custom_recurring_frequency, custom_weekly_frequency_day=None):
    
    # ? CONVERT STRING TO DATETIME IF NEEDED
    if isinstance(payroll_date, str):
        payroll_date = datetime.strptime(payroll_date, "%Y-%m-%d")
    
    # ? GET CURRENT YEAR AND MONTH
    today = datetime.now()
    current_year = today.year
    current_month = today.month

    # ? GET PAYROLL MONTH AND YEAR
    payroll_year = payroll_date.year
    payroll_month = payroll_date.month

    # ? FUNCTION TO CALCULATE MONTH DIFFERENCE BETWEEN TWO DATES
    def months_elapsed(start_year, start_month, end_year, end_month):
        return (end_year - start_year) * 12 + (end_month - start_month)

    # ? MONTHLY FREQUENCY
    if custom_recurring_frequency.lower() == "monthly":
        target_day = payroll_date.day
        _, last_day = calendar.monthrange(current_year, current_month)
        actual_day = min(target_day, last_day)
        return date(current_year, current_month, actual_day)

    # ? WEEKLY FREQUENCY
    elif custom_recurring_frequency.lower() == "weekly":
        if custom_weekly_frequency_day is None:
            custom_weekly_frequency_day = payroll_date.weekday()
        today_weekday = today.weekday()
        days_to_add = (custom_weekly_frequency_day - today_weekday) % 7
        return (today + timedelta(days=days_to_add)).date()

    # ? QUARTERLY FREQUENCY
    elif custom_recurring_frequency.lower() == "quarterly":
        if months_elapsed(payroll_year, payroll_month, current_year, current_month) % 3 == 0:
            target_day = payroll_date.day
            _, last_day = calendar.monthrange(current_year, current_month)
            actual_day = min(target_day, last_day)
            return date(current_year, current_month, actual_day)
        else:
            return None

    # ? HALF-YEARLY FREQUENCY
    elif custom_recurring_frequency.lower() in ["half-yearly", "half yearly"]:
        if months_elapsed(payroll_year, payroll_month, current_year, current_month) % 6 == 0:
            target_day = payroll_date.day
            _, last_day = calendar.monthrange(current_year, current_month)
            actual_day = min(target_day, last_day)
            return date(current_year, current_month, actual_day)
        else:
            return None

    # ? YEARLY FREQUENCY
    elif custom_recurring_frequency.lower() in ["yearly", "annual"]:
        if months_elapsed(payroll_year, payroll_month, current_year, current_month) % 12 == 0:
            target_day = payroll_date.day
            _, last_day = calendar.monthrange(current_year, current_month)
            actual_day = min(target_day, last_day)
            return date(current_year, current_month, actual_day)
        else:
            return None

    # ? NO MATCHING FREQUENCY
    return None



# ? FUNCTION TO CREATE A UNIQUE STRING KEY FROM AN ADDITIONAL SALARY RECORD
def make_additional_salary_key(
    employee,
    company,
    salary_component,
    payroll_date,
    deduct_full_tax,
    overwrite_amount,
    amount,
):
    # ? COMBINE FIELDS AND CREATE A UNIQUE STRING KEY FROM ADDITIONAL SALARY RECORD
    return f"{employee}-{company}-{salary_component}-{payroll_date}-{deduct_full_tax}-{overwrite_amount}-{amount}"


# ? FUNCTION TO FETCH EXISTING ADDITIONAL SALARY KEYS
def get_additional_salary_keys():

    # ? FETCH EXISTING ADDITIONAL SALARY RECORDS TO AVOID DUPLICATES
    additional_salaries = frappe.get_all(
        "Additional Salary",
        filters={"custom_recurring": 0},
        fields=[
            "employee",
            "company",
            "salary_component",
            "payroll_date",
            "deduct_full_tax_on_selected_payroll_date",
            "overwrite_salary_structure_amount",
            "amount",
        ],
    )

    # ? CREATE KEYS FOR EXISTING ADDITIONAL SALARY RECORDS
    return [
        make_additional_salary_key(
            row["employee"],
            row["company"],
            row["salary_component"],
            row["payroll_date"],
            row["deduct_full_tax_on_selected_payroll_date"],
            row["overwrite_salary_structure_amount"],
            row["amount"],
        )
        for row in additional_salaries
    ]


# ? FUNCTION TO CREATE ADDITIONAL SALARY DOCS FROM RECURRING RECORDS
@frappe.whitelist()
def create_additional_salaries_from_recurring():
    # ? LOOP THROUGH RECURRING RECORDS, CALCULATE ELIGIBLE DATE, AND CREATE ADDITIONAL SALARY DOCS IF NOT EXISTING

    # ? FETCH RECURRING SALARY RECORDS
    recurring_salaries = get_recurring_salaries()

    # ? FETCH EXISTING SALARY KEYS TO AVOID DUPLICATES
    existing_salary_keys = get_additional_salary_keys()

    for salary in recurring_salaries:
        eligible_date = get_eligible_date(
            salary["payroll_date"], salary["custom_recurring_frequency"]
        )

        if eligible_date:
            # ? CREATE A KEY FOR THE NEW ROW BASED ON THE SALARY DATA
            key = make_additional_salary_key(
                salary["employee"],
                salary["company"],
                salary["salary_component"],
                eligible_date,
                salary["deduct_full_tax_on_selected_payroll_date"],
                salary["overwrite_salary_structure_amount"],
                salary["amount"],
            )

            print("Exisiting_Keys", existing_salary_keys, " Key:", key)

            # ? CHECK IF THE KEY EXISTS IN THE EXISTING SALARY KEYS
            if key not in existing_salary_keys:

                # ? CREATE A NEW ADDITIONAL SALARY DOCUMENT WITH CUSTOM_RECURRING SET TO 0
                
                new_salary = frappe.get_doc(
                    {
                        "doctype": "Additional Salary",
                        "employee": salary["employee"],
                        "company": salary["company"],
                        "salary_component": salary["salary_component"],
                        "payroll_date": eligible_date,
                        "deduct_full_tax_on_selected_payroll_date": salary[
                            "deduct_full_tax_on_selected_payroll_date"
                        ],
                        "overwrite_salary_structure_amount": salary[
                            "overwrite_salary_structure_amount"
                        ],
                        "amount": salary["amount"],
                        "custom_recurring": 0,
                    }
                )
                new_salary.insert(ignore_permissions=True)
                frappe.db.commit()

                # ? OPTIONALLY, UPDATE THE EXISTING KEYS
                existing_salary_keys.append(key)

    frappe.msgprint(
        "Additional Salary records have been created from recurring entries successfully."
    )

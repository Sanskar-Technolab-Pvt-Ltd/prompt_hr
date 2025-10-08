import frappe

import frappe.commands
import calendar

from frappe.utils import (
    date_diff,
    today,
    add_to_date,
    getdate,
    get_datetime,
    add_months,
    add_days,
)
from prompt_hr.py.utils import fetch_company_name, send_notification_email, get_employee_email
from prompt_hr.py.auto_mark_attendance import mark_attendance, is_holiday_or_weekoff
from datetime import timedelta, datetime
from prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process import (
    raise_exit_checklist,
    raise_exit_interview,
)
from datetime import datetime, timedelta


def auto_attendance():
    frappe.log_error("custom_auto_attendance_start", "Auto Attendance Scheduler Started")
    mark_attendance(is_scheduler=1, attendance_date=add_days(today(), -1))
    frappe.log_error("custom_auto_attendance_end", "Auto Attendance Scheduler Finished")
    


@frappe.whitelist()
def create_probation_feedback_form():
    """Scheduler method to create probation feedback form based on the days after when employee joined mentioned in the HR Settings.
    - And Also notify the employee's reporting manager if the remarks are not added to the form.
    """

    try:
        probation_feedback_for_prompt()
        # probation_feedback_for_indifoss()

    except Exception as e:
        frappe.log_error(
            "Error while creating probation feedback form", frappe.get_traceback()
        )


# *CREATING PROBATION FEEDBACK FOR PROMPT EMPLOYEES
def probation_feedback_for_prompt():
    """Method to create probation feedback form for Prompt employees"""
    
    frappe.log_error("probation_feedback_for_prompt_start", "Scheduler Started")
    first_feedback_days = frappe.db.get_single_value(
        "HR Settings", "custom_first_feedback_after"
    )
    second_feedback_days = frappe.db.get_single_value(
        "HR Settings", "custom_second_feedback_after"
    )
        
    if first_feedback_days or second_feedback_days:

            # employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": "Prompt Equipments PVT LTD", "custom_probation_status": "Pending"}, "name")
            employees_list = frappe.db.get_all(
                "Employee",
                {
                    "status": "Active",
                    "custom_probation_status": "In Probation",
                    "custom_probation_status": "Pending",
                },
                ["name", "employee_name"],
            )
            for employee in employees_list:
                if employee.get("name"):
                    emp_joining_date = frappe.db.get_value(
                        "Employee", employee.get("name"), "date_of_joining"
                    )

                    first_feedback_form_id = (
                        frappe.db.get_value(
                            "Employee",
                            employee.get("name"),
                            "custom_first_probation_feedback",
                        )
                        or None
                    )
                    second_feedback_form_id = (
                        frappe.db.get_value(
                            "Employee",
                            employee.get("name"),
                            "custom_second_probation_feedback",
                        )
                        or None
                    )

                    create_only_one = (
                        True
                        if not first_feedback_form_id
                        and not second_feedback_form_id
                        else False
                    )

                    if emp_joining_date:
                        date_difference = date_diff(today(), emp_joining_date)
                        frappe.log_error("probation_feedback_for_prompt_date_diff", f"Date Diff {date_difference}")
                        if first_feedback_days <= date_difference:
                            if not first_feedback_form_id:
                                employee_doc = frappe.get_doc(
                                    "Employee", employee.get("name")
                                )
                                first_probation_form = frappe.get_doc(
                                    {
                                        "doctype": "Probation Feedback Form",
                                        "employee": employee.get("name"),
                                        "employee_name": employee_doc.get(
                                            "employee_name"
                                        ),
                                        "department": employee_doc.get(
                                            "department"
                                        ),
                                        "designation": employee_doc.get(
                                            "designation"
                                        ),
                                        "company": employee_doc.get("company"),
                                        "product_line": employee_doc.get(
                                            "custom_product_line"
                                        ),
                                        "business_unit": employee_doc.get(
                                            "custom_business_unit"
                                        ),
                                        "reporting_manager": employee_doc.get(
                                            "reports_to"
                                        ),
                                        "probation_feedback_for": "30 Days",
                                        "evaluation_date": today(),
                                    }
                                )

                                question_list = frappe.db.get_all(
                                    "Probation Question",
                                    {
                                        "probation_feedback_for": "30 Days",
                                    },
                                    "name",
                                )

                                if question_list:

                                    for question in question_list:
                                        first_probation_form.append(
                                            "probation_feedback_prompt",
                                            {
                                                "question": question.get("name"),
                                                "frequency": "30 Days",
                                            },
                                        )

                                first_probation_form.insert(ignore_permissions=True)
                                employee_doc.custom_first_probation_feedback = (
                                    first_probation_form.name
                                )
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()
                            else:
                                remarks_added = frappe.db.exists(
                                    "Probation Feedback Prompt",
                                    {
                                        "parenttype": "Probation Feedback Form",
                                        "parent": first_feedback_form_id,
                                        "rating": ["not in", ["0", ""]],
                                    },
                                    "name",
                                )

                                if not remarks_added:
                                    reporting_manager_emp_id = (
                                        frappe.db.get_value(
                                            "Probation Feedback Form",
                                            first_feedback_form_id,
                                            "reporting_manager",
                                        )
                                        or None
                                    )

                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                employee.get("name"),
                                                "reports_to",
                                            )
                                            or None
                                        )

                                    if reporting_manager_emp_id:

                                        reporting_manager_user_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                reporting_manager_emp_id,
                                                "user_id",
                                            )
                                            or None
                                        )

                                        if reporting_manager_user_id:
                                            reporting_manager_email = (
                                                frappe.db.get_value(
                                                    "User",
                                                    reporting_manager_user_id,
                                                    "email",
                                                )
                                            )
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(
                                                    reporting_manager_email,
                                                    reporting_manager_user_id,
                                                    first_feedback_form_id,
                                                    employee.get("employee_name"),
                                                )

                        if second_feedback_days <= date_difference:
                            if not second_feedback_form_id and not create_only_one:

                                employee_doc = frappe.get_doc(
                                    "Employee", employee.get("name")
                                )
                                second_probation_form = frappe.get_doc(
                                    {
                                        "doctype": "Probation Feedback Form",
                                        "employee": employee.get("name"),
                                        "employee_name": employee_doc.get(
                                            "employee_name"
                                        ),
                                        "department": employee_doc.get(
                                            "department"
                                        ),
                                        "designation": employee_doc.get(
                                            "designation"
                                        ),
                                        "company": employee_doc.get("company"),
                                        "product_line": employee_doc.get(
                                            "custom_product_line"
                                        ),
                                        "business_unit": employee_doc.get(
                                            "custom_business_unit"
                                        ),
                                        "reporting_manager": employee_doc.get(
                                            "reports_to"
                                        ),
                                        "probation_feedback_for": "60 Days",
                                        "evaluation_date": today(),
                                    }
                                )

                                question_list = frappe.db.get_all(
                                    "Probation Question",
                                    {
                                        "probation_feedback_for": "60 Days",
                                    },
                                    "name",
                                )

                                if question_list:
                                    for question in question_list:
                                        second_probation_form.append(
                                            "probation_feedback_prompt",
                                            {
                                                "question": question.get("name"),
                                                "frequency": "60 Days",
                                            },
                                        )

                                second_probation_form.insert(
                                    ignore_permissions=True
                                )
                                employee_doc.custom_second_probation_feedback = (
                                    second_probation_form.name
                                )
                                employee_doc.save(ignore_permissions=True)

                                frappe.db.commit()
                            elif second_feedback_form_id:

                                remarks_added = frappe.db.exists(
                                    "Probation Feedback Prompt",
                                    {
                                        "parenttype": "Probation Feedback Form",
                                        "parent": second_feedback_form_id,
                                        "rating": ["not in", ["0", ""]],
                                    },
                                )
                                if not remarks_added:
                                    reporting_manager_emp_id = (
                                        frappe.db.get_value(
                                            "Probation Feedback Form",
                                            second_feedback_form_id,
                                            "reporting_manager",
                                        )
                                        or None
                                    )
                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                employee.get("name"),
                                                "reports_to",
                                            )
                                            or None
                                        )

                                    if reporting_manager_emp_id:
                                        reporting_manager_user_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                reporting_manager_emp_id,
                                                "user_id",
                                            )
                                            or None
                                        )
                                        if reporting_manager_user_id:
                                            reporting_manager_email = (
                                                frappe.db.get_value(
                                                    "User",
                                                    reporting_manager_user_id,
                                                    "email",
                                                )
                                            )
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(
                                                    reporting_manager_email,
                                                    reporting_manager_user_id,
                                                    second_feedback_form_id,
                                                    employee.get("employee_name"),
                                                )
    else:
        frappe.log_error(
            "Issue while check for probation feedback form for Prompt",
            "Please set abbreviation in HR Settings FOR Prompt",
        )
    frappe.log_error("probation_feedback_for_prompt_ended", "Scheduler Ended")
    


# *CREATING PROBATION FEEDBACK FOR INDIFOSS EMPLOYEES
# ! THIS METHOD IS FOR INDIFOSS
def probation_feedback_for_indifoss():
    """Method to create probation feedback form for Indifoss employees"""

    first_feedback_days_for_indifoss = frappe.db.get_single_value(
        "HR Settings", "custom_first_feedback_after_for_indifoss"
    )
    second_feedback_days_for_indifoss = frappe.db.get_single_value(
        "HR Settings", "custom_second_feedback_after_for_indifoss"
    )
    confirmation_days_for_indifoss = frappe.db.get_single_value(
        "HR Settings", "custom_release_confirmation_form_for_indifoss"
    )

    company_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
    if company_abbr:

        if (
            first_feedback_days_for_indifoss
            or second_feedback_days_for_indifoss
            or confirmation_days_for_indifoss
        ):
            company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
            indifoss_employees_list = frappe.db.get_all(
                "Employee",
                {
                    "status": "Active",
                    "company": company_id,
                    "custom_probation_status": "Pending",
                },
                "name",
            )

            if indifoss_employees_list:
                for employee in indifoss_employees_list:
                    emp_joining_date = frappe.db.get_value(
                        "Employee", employee.get("name"), "date_of_joining"
                    )

                    probation_feedback_form_id = (
                        frappe.db.get_value(
                            "Employee",
                            employee.get("name"),
                            "custom_probation_review_form",
                        )
                        or None
                    )
                    if emp_joining_date:
                        date_difference = date_diff(today(), emp_joining_date)

                        if (
                            first_feedback_days_for_indifoss
                            <= date_difference
                            < second_feedback_days_for_indifoss
                        ):

                            if not probation_feedback_form_id:
                                probation_form = frappe.get_doc(
                                    {
                                        "doctype": "Probation Feedback Form",
                                        "employee": employee.get("name"),
                                        "evaluation_date": today(),
                                    }
                                )

                                general_sub_category_list = [
                                    "Common Parameters",
                                    "Communication",
                                    "Interpersonal Relationships and Interactions",
                                    "Commitment",
                                ]

                                factor_category_general_list = frappe.db.get_all(
                                    "Factor Category Parameters",
                                    {
                                        "parent_category": [
                                            "in",
                                            general_sub_category_list,
                                        ]
                                    },
                                    ["name", "parent_category", "description"],
                                )

                                if factor_category_general_list:
                                    for factor_category in factor_category_general_list:
                                        probation_form.append(
                                            "probation_feedback_indifoss",
                                            {
                                                "category": "General",
                                                "sub_category": factor_category.get(
                                                    "parent_category"
                                                ),
                                                "factor_category": factor_category.get(
                                                    "name"
                                                ),
                                                "description_of_assessment_category": factor_category.get(
                                                    "description"
                                                ),
                                            },
                                        )

                                probation_form.insert(ignore_permissions=True)
                                if probation_form.name:
                                    print(f"\n\n {probation_form.name}\n\n")
                                    frappe.db.set_value(
                                        "Employee",
                                        employee.get("name"),
                                        "custom_probation_review_form",
                                        probation_form.name,
                                    )

                                # if probation_form.reporting_manager:
                                #     reporting_manager_emp_id = probation_form.reporting_manager
                                #     if not reporting_manager_emp_id:
                                #         reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                #     reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")

                                #     if reporting_manager_user_id:
                                #         reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                #         if reporting_manager_email:
                                #             send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_form.name, employee.get("name"))
                                frappe.db.commit()
                            else:
                                remarks_added = frappe.db.exists(
                                    "Probation Feedback IndiFOSS",
                                    {
                                        "parenttype": "Probation Feedback Form",
                                        "parent": probation_feedback_form_id,
                                        "45_days": ["not in", ["0", ""]],
                                    },
                                )

                                if not remarks_added:
                                    reporting_manager_emp_id = (
                                        frappe.db.get_value(
                                            "Probation Feedback Form",
                                            probation_feedback_form_id,
                                            "reporting_manager",
                                        )
                                        or None
                                    )

                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                employee.get("name"),
                                                "reports_to",
                                            )
                                            or None
                                        )

                                    if reporting_manager_emp_id:
                                        reporting_manager_user_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                reporting_manager_emp_id,
                                                "user_id",
                                            )
                                            or None
                                        )

                                        if reporting_manager_user_id:
                                            reporting_manager_email = (
                                                frappe.db.get_value(
                                                    "User",
                                                    reporting_manager_user_id,
                                                    "email",
                                                )
                                            )
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(
                                                    reporting_manager_email,
                                                    reporting_manager_user_id,
                                                    probation_feedback_form_id,
                                                    employee.get("name"),
                                                )

                        if (
                            second_feedback_days_for_indifoss
                            <= date_difference
                            < confirmation_days_for_indifoss
                        ):
                            if not probation_feedback_form_id:
                                probation_form = frappe.get_doc(
                                    {
                                        "doctype": "Probation Feedback Form",
                                        "employee": employee.get("name"),
                                        "evaluation_date": today(),
                                    }
                                )

                                general_sub_category_list = [
                                    "Common Parameters",
                                    "Communication",
                                    "Interpersonal Relationships and Interactions",
                                    "Commitment",
                                ]

                                factor_category_general_list = frappe.db.get_all(
                                    "Factor Category Parameters",
                                    {
                                        "parent_category": [
                                            "in",
                                            general_sub_category_list,
                                        ]
                                    },
                                    ["name", "parent_category", "description"],
                                )

                                if factor_category_general_list:
                                    for factor_category in factor_category_general_list:
                                        probation_form.append(
                                            "probation_feedback_indifoss",
                                            {
                                                "category": "General",
                                                "sub_category": factor_category.get(
                                                    "parent_category"
                                                ),
                                                "factor_category": factor_category.get(
                                                    "name"
                                                ),
                                                "description_of_assessment_category": factor_category.get(
                                                    "description"
                                                ),
                                            },
                                        )

                                probation_form.insert(ignore_permissions=True)
                                if probation_form.name:
                                    frappe.db.set_value(
                                        "Employee",
                                        employee.get("name"),
                                        "custom_probation_review_form",
                                        probation_form.name,
                                    )
                                frappe.db.commit()
                                # if probation_form.reporting_manager:
                                #     reporting_manager_emp_id = probation_form.reporting_manager
                                #     if not reporting_manager_emp_id:
                                #         reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                #     reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")

                                #     if reporting_manager_user_id:
                                #         reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                #         if reporting_manager_email:
                                #             send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_form.name, employee.get("name"))

                            else:
                                remarks_added = frappe.db.exists(
                                    "Probation Feedback IndiFOSS",
                                    {
                                        "parenttype": "Probation Feedback Form",
                                        "parent": probation_feedback_form_id,
                                        "90_days": ["not in", ["0", ""]],
                                    },
                                )

                                if not remarks_added:
                                    reporting_manager_emp_id = (
                                        frappe.db.get_value(
                                            "Probation Feedback Form",
                                            probation_feedback_form_id,
                                            "reporting_manager",
                                        )
                                        or None
                                    )

                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                employee.get("name"),
                                                "reports_to",
                                            )
                                            or None
                                        )

                                    if reporting_manager_emp_id:
                                        reporting_manager_user_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                reporting_manager_emp_id,
                                                "user_id",
                                            )
                                            or None
                                        )

                                        if reporting_manager_user_id:
                                            reporting_manager_email = (
                                                frappe.db.get_value(
                                                    "User",
                                                    reporting_manager_user_id,
                                                    "email",
                                                )
                                            )
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(
                                                    reporting_manager_email,
                                                    reporting_manager_user_id,
                                                    probation_feedback_form_id,
                                                    employee.get("name"),
                                                )

                        if confirmation_days_for_indifoss <= date_difference:
                            if not probation_feedback_form_id:
                                probation_form = frappe.get_doc(
                                    {
                                        "doctype": "Probation Feedback Form",
                                        "employee": employee.get("name"),
                                        # "employee_name": employee.get("employee_name"),
                                        # "department": employee.get("department"),
                                        # "designation": employee.get("designation"),
                                        # "company": employee.get("company"),
                                        # "product_line": employee.get("custom_product_line"),
                                        # "business_unit": employee.get("custom_business_unit"),
                                        # "reporting_manager": employee.get("reports_to"),
                                        "evaluation_date": today(),
                                    }
                                )

                                general_sub_category_list = [
                                    "Common Parameters",
                                    "Communication",
                                    "Interpersonal Relationships and Interactions",
                                    "Commitment",
                                ]

                                factor_category_general_list = frappe.db.get_all(
                                    "Factor Category Parameters",
                                    {
                                        "parent_category": [
                                            "in",
                                            general_sub_category_list,
                                        ]
                                    },
                                    ["name", "parent_category", "description"],
                                )

                                if factor_category_general_list:
                                    for factor_category in factor_category_general_list:
                                        probation_form.append(
                                            "probation_feedback_indifoss",
                                            {
                                                "category": "General",
                                                "sub_category": factor_category.get(
                                                    "parent_category"
                                                ),
                                                "factor_category": factor_category.get(
                                                    "name"
                                                ),
                                                "description_of_assessment_category": factor_category.get(
                                                    "description"
                                                ),
                                            },
                                        )

                                probation_form.insert(ignore_permissions=True)
                                if probation_form:
                                    frappe.db.set_value(
                                        "Employee",
                                        employee.get("name"),
                                        "custom_probation_review_form",
                                        probation_form.name,
                                    )
                                frappe.db.commit()
                                # if probation_form.reporting_manager:
                                #     reporting_manager_emp_id = probation_form.reporting_manager
                                #     if not reporting_manager_emp_id:
                                #         reporting_manager_emp_id = frappe.db.get_value("Employee", employee.get("name"), "reports_to") or None
                                #     reporting_manager_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")

                                #     if reporting_manager_user_id:
                                #         reporting_manager_email = frappe.db.get_value("User", reporting_manager_user_id, "email")
                                #         if reporting_manager_email:
                                #             send_reminder_mail_to_reporting_manager(reporting_manager_email, reporting_manager_user_id, probation_form.name, employee.get("name"))

                            else:
                                remarks_added = frappe.db.exists(
                                    "Probation Feedback IndiFOSS",
                                    {
                                        "parenttype": "Probation Feedback Form",
                                        "parent": probation_feedback_form_id,
                                        "180_days": ["not in", ["0", ""]],
                                    },
                                )

                                if not remarks_added:
                                    reporting_manager_emp_id = (
                                        frappe.db.get_value(
                                            "Probation Feedback Form",
                                            probation_feedback_form_id,
                                            "reporting_manager",
                                        )
                                        or None
                                    )

                                    if not reporting_manager_emp_id:
                                        reporting_manager_emp_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                employee.get("name"),
                                                "reports_to",
                                            )
                                            or None
                                        )

                                    if reporting_manager_emp_id:
                                        reporting_manager_user_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                reporting_manager_emp_id,
                                                "user_id",
                                            )
                                            or None
                                        )

                                        if reporting_manager_user_id:
                                            reporting_manager_email = (
                                                frappe.db.get_value(
                                                    "User",
                                                    reporting_manager_user_id,
                                                    "email",
                                                )
                                            )
                                            if reporting_manager_email:
                                                send_reminder_mail_to_reporting_manager(
                                                    reporting_manager_email,
                                                    reporting_manager_user_id,
                                                    probation_feedback_form_id,
                                                    employee.get("name"),
                                                )


# *SENDING MAIL TO REPORTING MANAGER*
def send_reminder_mail_to_reporting_manager(
    reporting_manager_email,
    reporting_manager_user_id,
    probation_feedback_form_id,
    employee_id,
):
    """Method to send a reminder email to the reporting manager"""

    try:
        notification = frappe.get_doc(
            {
                "doctype": "Notification Log",
                "subject": "Add Remarks to Feedback Form",
                "for_user": reporting_manager_user_id,
                "type": "Energy Point",
                "document_type": "Probation Feedback Form",
                "document_name": probation_feedback_form_id,
            }
        )
        notification.insert(ignore_permissions=True)

        frappe.sendmail(
            recipients=[
                reporting_manager_email,
            ],
            subject="Feedback Form Reminder",
            content=f"Reminder: Add Remarks to Feedback Form {probation_feedback_form_id} for {employee_id}",
            # now = True
        )
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            "Error while sending second feedback mail", frappe.get_traceback()
        )


# * CREATING CONFIRMATION EVALUATION FORM AND IF ALREADY CREATED THEN, SENDING MAIL TO REPORTING MANAGER OR HEAD OF DEPARTMENT BASED ON THE RATING ADDED OR NOT
# @frappe.whitelist()
def create_confirmation_evaluation_form_for_prompt():
    try:

        frappe.log_error("create_confirmation_evaluation_form_for_prompt_start", "Scheduler Started")
        # company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
        create_cff_before_days = (
            frappe.db.get_single_value(
                "HR Settings", "custom_release_confirmation_form"
            )
            or 15
        )

        # if company_abbr:
            # company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
            # if company_id:
        employees_list = frappe.db.get_all(
            "Employee",
            {
                "status": "Active",
                "custom_probation_status": "In Probation",
                # "custom_probation_status": "Pending",
            },
            ["name", "custom_probation_period", "custom_probation_end_date", "date_of_joining"],
        )

        if employees_list:
            for employee_id in employees_list:
                # probation_days = frappe.db.get_value(
                #     "Employee",
                #     employee_id.get("name"),
                #     "custom_probation_period",
                # )
                probation_days = employee_id.get("custom_probation_period")
                
                # extended_period = frappe.db.get_value(
                #     "Employee",
                #     employee_id.get("name"),
                #     "custom_extended_period",
                # )
                result =  frappe.db.get_all("Probation Extension", {"parenttype": "Employee", "parent": employee_id.get("name")}, "extended_period", pluck="extended_period", order_by="idx desc")
                                
                extended_period = result[0] if result else 0
                                                
                if probation_days:
                    # probation_end_date = frappe.db.get_value(
                    #     "Employee", employee_id.get("name"), "custom_probation_end_date"
                    # )
                    probation_end_date = employee_id.get("custom_probation_end_date")
                    
                    # joining_date = frappe.db.get_value(
                    #     "Employee", employee_id.get("name"), "date_of_joining"
                    # )
                    joining_date = employee_id.get("date_of_joining")
                    
                    if not probation_end_date:
                        if extended_period:
                            probation_end_date = getdate(
                                add_to_date(joining_date, days=probation_days + extended_period)
                            )
                        else:
                            probation_end_date = getdate(
                                add_to_date(joining_date, days=probation_days)
                            )

                    today_date = getdate()
                    days_remaining = (probation_end_date - today_date).days
                    frappe.log_error(f"info_confirmation_evaluation_form_for_prompt_end_{employee_id.get('name')}", f"days remaining {days_remaining}")
                    if 0 <= days_remaining <= create_cff_before_days:
                        confirmation_eval_form = frappe.db.get_value(
                            "Employee",
                            employee_id.get("name"),
                            "custom_confirmation_evaluation_form",
                        )
                        try:
                            if not confirmation_eval_form:
                                employee_doc = frappe.get_doc(
                                    "Employee", employee_id.get("name")
                                )
                                confirmation_eval_doc = frappe.get_doc(
                                    {
                                        "doctype": "Confirmation Evaluation Form",
                                        "employee": employee_id.get("name"),
                                        "evaluation_date": today(),
                                        # "probation_status": "Pending",
                                    }
                                )

                                category_list = [
                                    "Functional/ Technical Skills",
                                    "Behavioural Skills",
                                ]

                                parameters_list = frappe.db.get_all(
                                    "Confirmation Evaluation Parameter",
                                    {"category": ["in", category_list]},
                                    ["name", "category"],
                                )

                                for parameter in parameters_list:

                                    confirmation_eval_doc.append(
                                        "table_txep",
                                        {
                                            "category": parameter.get(
                                                "category"
                                            ),
                                            "parameters": parameter.get("name"),
                                        },
                                    )

                                confirmation_eval_doc.insert(
                                    ignore_permissions=True
                                )
                                employee_doc.custom_confirmation_evaluation_form = (
                                    confirmation_eval_doc.name
                                )
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()
                                # frappe.db.set_value("Employee", employee_id.get("name"), "custom_confirmation_evaluation_form", confirmation_eval_doc.name)
                            elif confirmation_eval_form:
                                
                                confirmation_eval_form_doc = frappe.get_doc(
                                    "Confirmation Evaluation Form",
                                    confirmation_eval_form,
                                )

                                if (confirmation_eval_form_doc.confirmed_by_rh == "No" and confirmation_eval_form_doc.further_to_by_rh == "Extend") or (confirmation_eval_form_doc.confirmed_by_dh == "No" and confirmation_eval_form_doc.further_to_by_dh == "Extend"): 
                                    employee_doc = frappe.get_doc(
                                    "Employee", employee_id.get("name")
                                    )
                                    confirmation_eval_doc = frappe.get_doc(
                                        {
                                            "doctype": "Confirmation Evaluation Form",
                                            "employee": employee_id.get("name"),
                                            "evaluation_date": today(),
                                            # "probation_status": "Pending",
                                        }
                                    )

                                    category_list = [
                                        "Functional/ Technical Skills",
                                        "Behavioural Skills",
                                    ]

                                    parameters_list = frappe.db.get_all(
                                        "Confirmation Evaluation Parameter",
                                        {"category": ["in", category_list]},
                                        ["name", "category"],
                                    )

                                    for parameter in parameters_list:

                                        confirmation_eval_doc.append(
                                            "table_txep",
                                            {
                                                "category": parameter.get(
                                                    "category"
                                                ),
                                                "parameters": parameter.get("name"),
                                            },
                                        )

                                    confirmation_eval_doc.insert(
                                        ignore_permissions=True
                                    )
                                    employee_doc.custom_confirmation_evaluation_form = (
                                        confirmation_eval_doc.name
                                    )
                                    employee_doc.save(ignore_permissions=True)
                                    frappe.db.commit()
                                else:
                                    rh_rating_added = (
                                        confirmation_eval_form_doc.rh_rating_added
                                    )
                                    dh_rating_added = (
                                        confirmation_eval_form_doc.dh_rating_added
                                    )
                                    context = {
                                        "doc": confirmation_eval_form_doc,
                                        "doctype": "Confirmation Evaluation Form",
                                        "docname": confirmation_eval_form_doc.name,
                                    }
                                    notification_template = frappe.get_doc(
                                        "Notification",
                                        "Confirmation Evaluation Form Remarks Reminder",
                                    )
                                    subject = frappe.render_template(
                                        notification_template.subject, context
                                    )
                                    message = frappe.render_template(
                                        notification_template.message, context
                                    )

                                    if not rh_rating_added:
                                        reporting_head = (
                                            confirmation_eval_form_doc.reporting_manager
                                        )
                                        reporting_head_user_id = (
                                            frappe.db.get_value(
                                                "Employee",
                                                reporting_head,
                                                "user_id",
                                            )
                                            if reporting_head
                                            else None
                                        )
                                        reporting_head_email = (
                                            frappe.db.get_value(
                                                "User",
                                                reporting_head_user_id,
                                                "email",
                                            )
                                            if reporting_head_user_id
                                            else None
                                        )

                                        if reporting_head_email:

                                            try:
                                                frappe.sendmail(
                                                    recipients=[
                                                        reporting_head_email
                                                    ],
                                                    subject=subject,
                                                    message=message,
                                                    reference_doctype="Confirmation Evaluation Form",
                                                    reference_name=confirmation_eval_form_doc.name,
                                                    now=True,
                                                )
                                            except Exception as e:
                                                frappe.log_error(
                                                    "Error while sending confirmation evaluation form reminder mail",
                                                    frappe.get_traceback(),
                                                )
                                                continue

                                    elif rh_rating_added and not dh_rating_added:

                                        head_of_department = (
                                            confirmation_eval_form_doc.hod
                                        )
                                        head_of_department_employee = (
                                            frappe.db.get_value(
                                                "Employee",
                                                head_of_department,
                                                "user_id",
                                            )
                                            if head_of_department
                                            else None
                                        )
                                        head_of_department_email = (
                                            frappe.db.get_value(
                                                "User",
                                                head_of_department_employee,
                                                "email",
                                            )
                                            if head_of_department_employee
                                            else None
                                        )

                                        if head_of_department_email:
                                            frappe.sendmail(
                                                recipients=[
                                                    head_of_department_email
                                                ],
                                                subject=subject,
                                                message=message,
                                                reference_doctype="Confirmation Evaluation Form",
                                                reference_name=confirmation_eval_form_doc.name,
                                                now=True,
                                            )
                                        
                        except Exception as e:
                            frappe.log_error(
                                "Error while creating confirmation evaluation form",
                                frappe.get_traceback(),
                            )
                            continue
                    else:
                        frappe.log_error("error_confirmation_evaluation_form_for_prompt_end", "Not")
            # else:
            #     frappe.log_error(
            #         "Issue while creating confirmation form for prompt",
            #         f"Company Not found for abbreviation {company_abbr}",
            #     )
        # else:
        #     frappe.log_error(
        #         "Issue while creating confirmation form for prompt",
        #         "Company abbreviation Not Found Please Set Company abbreviation for Prompt in HR Settings",
        #     )
        frappe.log_error("create_confirmation_evaluation_form_for_prompt_end", "Scheduler End")
    except Exception as e:
        frappe.log_error(
            "error_confirmation_evaluation_form_for_prompt_end", frappe.get_traceback()
        )


# !THIS METHOD IS FOR INDIFOSS
# def inform_employee_for_confirmation_process():
#     """Method to inform employee about confirmation process  before the days set user in HR Settings probation period is over
#     FOR INDIFOSS
#     """
#     try:

#         company_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
#         company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
#         employee_list = frappe.db.get_all(
#             "Employee",
#             {
#                 "status": "Active",
#                 "company": company_id,
#                 "custom_probation_status": "Pending",
#             },
#             "name",
#         )

#         inform_days_before_confirmation = frappe.db.get_single_value(
#             "HR Settings", "custom_inform_employees_probation_end_for_indifoss"
#         )
#         if inform_days_before_confirmation:
#             final_inform_days = -abs(inform_days_before_confirmation)
#         else:
#             final_inform_days = -5
#         if employee_list:

#             for employee in employee_list:
#                 employee_doc = frappe.get_doc("Employee", employee.get("name"))
#                 extended_period = employee_doc.custom_probation_extension_details[-1].get("extended_period") if employee_doc.custom_probation_extension_details else 0
                    
                
#                 probation_period = (
#                     employee_doc.custom_probation_period
#                     or 0 + extended_period
#                 )

#                 if probation_period:
#                     joining_date = employee_doc.date_of_joining
#                     if joining_date:

#                         probation_end_date = add_to_date(
#                             joining_date, days=probation_period
#                         )
#                         if probation_end_date:
#                             five_days_before_date = add_to_date(
#                                 probation_end_date,
#                                 days=final_inform_days,
#                                 as_string=True,
#                             )
#                             if (
#                                 five_days_before_date
#                                 and five_days_before_date == today()
#                             ):

#                                 employee_email = (
#                                     frappe.db.get_value(
#                                         "User", employee_doc.user_id, "email"
#                                     )
#                                     if employee_doc.user_id
#                                     else None
#                                 )

#                                 if employee_email:
#                                     notification_template = frappe.get_doc(
#                                         "Notification",
#                                         "Inform Employee about Confirmation Process",
#                                     )
#                                     if notification_template:
#                                         subject = frappe.render_template(
#                                             notification_template.subject,
#                                             {"doc": employee_doc},
#                                         )
#                                         message = frappe.render_template(
#                                             notification_template.message,
#                                             {"doc": employee_doc},
#                                         )

#                                         frappe.sendmail(
#                                             recipients=[employee_email],
#                                             subject=subject,
#                                             message=message,
#                                             now=True,
#                                         )
#                                     else:
#                                         frappe.sendmail(
#                                             recipients=[employee_email],
#                                             subject="Confirmation Process Reminder",
#                                             message=f"Dear {employee_doc.employee_name or 'Employee'}, your probation period is ending soon. Please check with your reporting manager for the confirmation process.",
#                                             now=True,
#                                         )
#     except Exception as e:
#         frappe.log_error(
#             "Error while sending confirmation process reminder email",
#             frappe.get_traceback(),
#         )


@frappe.whitelist()
def validate_employee_holiday_list():
    """checking if are there any weeklyoff assignment or not if there are then assigning them based on from and to date and updating employee holiday list if required"""
    try:
        employee_list = frappe.db.get_all("Employee", {"status": "Active"}, "name")

        if not employee_list:
            frappe.log_error(
                "No Employee Found",
                "No Employees are found to check for weeklyoff assignment",
            )

        today_date = getdate(today())

        for employee_id in employee_list:
            weeklyoff_assignment_list = frappe.db.get_all(
                "WeeklyOff Assignment",
                {"employee": employee_id.get("name"), "docstatus": 1},
                "name",
            )

            if weeklyoff_assignment_list:

                for weeklyoff_assignment_id in weeklyoff_assignment_list:
                    weeklyoff_assignment_doc = frappe.get_doc(
                        "WeeklyOff Assignment", weeklyoff_assignment_id.get("name")
                    )

                    if not weeklyoff_assignment_doc:
                        frappe.log_error(
                            "Not able to fetch Weekoff assignment",
                            f"Weekoff Assignment not found {weeklyoff_assignment_id}",
                        )

                    if weeklyoff_assignment_doc.start_date <= today_date:
                        start_date = weeklyoff_assignment_doc.start_date
                        end_date = weeklyoff_assignment_doc.end_date

                        employee_doc = frappe.get_doc(
                            "Employee", employee_id.get("name")
                        )

                        if (start_date and end_date) and (
                            start_date <= today_date < end_date
                        ):
                            # * SETTING NEW WEEKLYOFF TYPE FOR EMPLOYEE IF THE CURRENT DATE IS WITHIN THE WEEKOFF ASSIGNMENT PERIOD
                            if (
                                weeklyoff_assignment_doc.new_weeklyoff_type
                                != employee_doc.custom_weeklyoff
                            ):
                                employee_doc.custom_weeklyoff = (
                                    weeklyoff_assignment_doc.new_weeklyoff_type
                                )
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()

                        elif end_date and end_date < today_date:
                            # * SETTING BACK THE OLD WEEKLYOFF TYPE ONCE THE WEEKOFF ASSIGNMENT PERIOD IS OVER
                            if (
                                weeklyoff_assignment_doc.old_weeklyoff_type
                                != employee_doc.custom_weeklyoff
                            ):
                                employee_doc.custom_weeklyoff = (
                                    weeklyoff_assignment_doc.old_weeklyoff_type
                                )
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()

                        elif not end_date and (start_date and start_date <= today_date):
                            # * PERMANENTLY SETTING NEW WEEKLYOFF TYPE FOR EMPLOYEE IF END DATE IS NOT DEFINED
                            if (
                                weeklyoff_assignment_doc.new_weeklyoff_type
                                != employee_doc.custom_weeklyoff
                            ):
                                frappe.db.set_value(
                                    "WeeklyOff Assignment",
                                    {"employee": employee_id.get("name")},
                                    "old_weeklyoff_type",
                                    weeklyoff_assignment_doc.new_weeklyoff_type,
                                )
                                employee_doc.custom_weeklyoff = (
                                    weeklyoff_assignment_doc.new_weeklyoff_type
                                )
                                employee_doc.save(ignore_permissions=True)
                                frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            "Error while checking for weeklyoff assignment", frappe.get_traceback()
        )

def user_has_role(user, role):
    """Method to check if the user has the given role or not"""
    return frappe.db.exists("Has Role", {"parent": user, "role": role})


@frappe.whitelist()
def penalize_prompt_employee():
    """Method to to check for late coming or daily hours criteria and apply penalty"""
    try:
        hr_settings_doc = frappe.get_doc("HR Settings")

        allowed_late_entries = hr_settings_doc.custom_late_coming_allowed_per_month_for_prompt or 0

        leave_penalty_buffer_days = hr_settings_doc.custom_buffer_days_for_penalty
        working_hours_buffer_days = hr_settings_doc.custom_buffer_days_for_penalty
        no_attendance_buffer_days = hr_settings_doc.custom_buffer_days_for_penalty

        expected_work_hours = hr_settings_doc.custom_daily_hours_criteria_for_penalty_for_prompt

        # Determine dates for each penalty type
        leave_penalty_check_attendance_date = getdate(
            add_to_date(today(), days=-(leave_penalty_buffer_days + 1))
        ) if leave_penalty_buffer_days else getdate(today())

        daily_hours_attendance_date = getdate(
            add_to_date(today(), days=-(working_hours_buffer_days + 1))
        ) if working_hours_buffer_days else getdate(add_to_date(today(), days=-1))

        no_attendance_date = getdate(
            add_to_date(today(), days=-(no_attendance_buffer_days + 1))
        ) if no_attendance_buffer_days else getdate(add_to_date(today(), days=-1))

        company_id = fetch_company_name(prompt=1)
        if company_id.get("error"):
            frappe.log_error("Error in penalize_prompt_employee", frappe.get_traceback())
            return

        prompt_employee_list = frappe.db.get_all(
            "Employee",
            {"status": "Active", "company": company_id.get("company_id")},
            ["name", "holiday_list"],
        )

        no_attendance_leave_type = frappe.db.get_value(
            "Leave Type",
            {"is_lwp": 1, "custom_company": company_id.get("company_id")},
            "name",
        )
        no_attendance_deduct_leave = 1.0  # Can be modified as needed
        is_lwp_for_no_attendance = 1

        # Fetch Daily Hours penalty config (First record from HR Settings child table)
        daily_hour_configs = frappe.db.get_all(
            "Leave Penalty Configuration",
            filters={
                "parent": "HR Settings",
                "parenttype": "HR Settings",
                "parentfield": "custom_daily_hour_leave_penalty_configuration",
            },
            fields=["penalty_deduction_type", "leave_type_for_penalty", "deduction_of_leave"],
            order_by="idx asc",
        )

        daily_hours_leave_type = daily_hour_configs[0].leave_type_for_penalty if daily_hour_configs else None
        deduction_type = daily_hour_configs[0].deduction_of_leave if daily_hour_configs else "Full Day"

        insufficient_hours_deduct_leave = 0.5 if deduction_type == "Half Day" else 1.0
        is_lwp_for_insufficient_hours = 1 if daily_hour_configs[0].penalty_deduction_type == "Deduct Leave Without Pay" else 0

        month_first_date = leave_penalty_check_attendance_date.replace(day=1)
        next_month = add_months(month_first_date, 1)
        month_last_date = next_month - timedelta(days=1)

        leave_period_data = frappe.db.get_value(
            "Leave Period",
            {"is_active": 1, "company": company_id.get("company_id")},
            ["name", "from_date", "to_date"],
            as_dict=True,
        )

        for emp_id in prompt_employee_list:
            args = {"employee": emp_id, "company": company_id.get("company_id")}
            penalize_employee_for_attendance_mispunch_prompt(args)

            employee_scheduled_for_late_entry_penalty = penalize_employee_for_late_entry_for_prompt(
                emp_id,
                company_id.get("company_id"),
                month_first_date,
                month_last_date,
                allowed_late_entries,
                leave_penalty_check_attendance_date,
                leave_period_data,
            )

            if employee_scheduled_for_late_entry_penalty:
                send_penalty_warnings(employee_scheduled_for_late_entry_penalty, "Late Entry")

            employee_scheduled_for_incomplete_day_penalty = penalize_incomplete_day_for_prompt(
                emp_id,
                daily_hours_attendance_date,
                expected_work_hours,
                leave_period_data,
                is_lwp_for_insufficient_hours,
                daily_hours_leave_type,
                insufficient_hours_deduct_leave,
                company_id.get("company_id"),
            )

            if employee_scheduled_for_incomplete_day_penalty:
                send_penalty_warnings(employee_scheduled_for_incomplete_day_penalty, "Incomplete Day")

            employee_scheduled_for_no_attendance_penalty = penalization_for_no_attendance_for_prompt(
                emp_id,
                no_attendance_date,
                leave_period_data,
                no_attendance_leave_type,
                no_attendance_deduct_leave,
                company_id.get("company_id"),
            )

            if employee_scheduled_for_no_attendance_penalty:
                send_penalty_warnings(employee_scheduled_for_no_attendance_penalty, "No Attendance")

    except Exception as e:
        frappe.log_error("Error in penalize_prompt_employee", frappe.get_traceback())


import frappe
from frappe.utils import getdate, add_to_date
import traceback


# ! METHOD: PENALIZE EMPLOYEE FOR LATE ENTRY BASED ON CONFIGURATION
# ? CALLED FROM SCHEDULER OR FORM - PROCESSES PENALTY LOGIC FOR ONE EMPLOYEE FOR A MONTH
@frappe.whitelist()
def penalize_employee_for_late_entry_for_prompt(
    emp_id,
    company_id,
    month_first_date,
    month_last_date,
    allowed_late_entries,
    check_attendance_date,
    leave_period_data,
):
    """
    CHECKS IF EMPLOYEE HAS EXCEEDED ALLOWED LATE ENTRIES IN THE GIVEN MONTH.
    DEDUCTS LEAVES BASED ON HR SETTINGS CONFIGURATION TABLE AND CREATES PENALTY IF NEEDED.
    """
    try:
        emp_name = emp_id.get("name")
        print(f"\n\n===== PENALTY CHECK STARTED FOR: {emp_name} =====")

        # ! STEP 1: VALIDATE EMPLOYEE ELIGIBILITY
        print(f"[STEP 1] Validating eligibility for late entry penalty...")
        if not check_employee_penalty_criteria(emp_name, "For Late Arrival"):
            print(f"[INFO] {emp_name} is NOT eligible for late entry penalty.")
            return

        print(f"[INFO] {emp_name} is eligible for late entry penalty.")

        # ! STEP 2: FETCH LATE ATTENDANCE ENTRIES
        print(f"[STEP 2] Fetching late attendance entries between {month_first_date} and {month_last_date}...")
        late_attendance_list = frappe.db.get_all(
            "Attendance",
            filters={
                "docstatus": 1,
                "employee": emp_name,
                "attendance_date": ["between", [month_first_date, month_last_date]],
                "late_entry": 1,
            },
            fields=["name", "attendance_date"],
            order_by="attendance_date asc",
        )

        print(f"[INFO] Total late entries found: {len(late_attendance_list)}")
        print(f"[INFO] Allowed late entries: {allowed_late_entries}")

        if not late_attendance_list:
            print(f"[INFO] No late attendance entries for {emp_name}")
            return None

        # ! STEP 3: DETERMINE PENALIZABLE ENTRIES
        penalizable_entries = late_attendance_list[allowed_late_entries:]
        print(f"[STEP 3] Entries exceeding threshold (to penalize): {len(penalizable_entries)}")

        if not penalizable_entries:
            print(f"[INFO] No penalizable entries for {emp_name}")
            return None

        # ! STEP 4: FETCH HR SETTINGS CONFIGURATION
        print(f"[STEP 4] Fetching late entry penalty configurations from HR Settings...")
        penalty_configurations = get_late_entry_penalty_configurations()
        print(f"[INFO] Total configurations fetched: {len(penalty_configurations)}")

        if not penalty_configurations:
            print(f"[ERROR] No penalty configurations found. Skipping penalty.")
            return None

        # ! Determine deduction amount from first config
        first_config = penalty_configurations[0]
        deduction_type = first_config.get("deduction_of_leave", "Full Day")
        deduct_leave_value = 0.5 if deduction_type == "Half Day" else 1.0
        is_lwp_for_late_entry = 0  # Assuming config forces LWP is handled elsewhere

        print(f"[CONFIG] Deduction Type: {deduction_type} | Deduction Value: {deduct_leave_value}")

        # ! STEP 5: LOOP OVER EACH PENALIZABLE ENTRY
        employee_scheduled_for_penalty_tomorrow = None

        for attendance_id in penalizable_entries:
            att_date = attendance_id.get("attendance_date")
            att_name = attendance_id.get("name")
            print(f"\n[ENTRY CHECK] Attendance: {att_name} | Date: {att_date}")

            leave_exists = frappe.db.exists(
                "Leave Application",
                {
                    "employee": emp_name,
                    "docstatus": 1,
                    "from_date": ["<=", att_date],
                    "to_date": [">=", att_date],
                },
            )

            regularization_exists = frappe.db.exists(
                "Attendance Regularization",
                {
                    "employee": emp_name,
                    "attendance": att_name,
                    "regularization_date": att_date,
                },
            )

            penalty_exists = frappe.db.exists(
                "Employee Penalty",
                {
                    "employee": emp_name,
                    "attendance": att_name,
                    "for_late_coming": 1,
                },
            )

            print(f"[CHECK] Leave Exists: {bool(leave_exists)} | Regularization Exists: {bool(regularization_exists)} | Existing Penalty: {bool(penalty_exists)}")

            if not (leave_exists or regularization_exists or penalty_exists):
                att_date_obj = getdate(att_date)

                if att_date_obj <= check_attendance_date:
                    print(f"[ACTION] Creating penalty for {emp_name} on {att_date}...")

                    leave_deductions_list = calculate_leave_deductions_for_late_entry(
                        emp_name,
                        company_id,
                        deduct_leave_value,
                        is_lwp_for_late_entry,
                        penalty_configurations,
                    )

                    print(f"[INFO] Final leave deductions to apply: {leave_deductions_list}")

                    create_employee_penalty(
                        emp_name,
                        att_date,
                        deduct_leave_value,
                        attendance_id=att_name,
                        leave_deductions=leave_deductions_list,
                        leave_period_data=leave_period_data,
                        is_lwp_for_late_entry=is_lwp_for_late_entry,
                        for_late_coming=1,
                    )

                elif att_date_obj == add_to_date(check_attendance_date, days=1):
                    print(f"[INFO] Penalty scheduled for tomorrow for: {emp_name}")
                    employee_scheduled_for_penalty_tomorrow = emp_name

        print(f"[RESULT] Penalty scheduling complete for {emp_name}")
        return employee_scheduled_for_penalty_tomorrow

    except Exception as e:
        frappe.log_error("Error in penalize_employee_for_late_entry", frappe.get_traceback())
        print(f"[ERROR] Exception occurred during penalty processing: {str(e)}")
        return None

# ! METHOD: PENALIZE EMPLOYEE FOR LATE ENTRY BASED ON CONFIGURATION
# ? CALLED FROM SCHEDULER OR FORM - PROCESSES PENALTY LOGIC FOR ONE EMPLOYEE FOR A MONTH
@frappe.whitelist()
def penalize_employee_for_late_entry_for_prompt(
    emp_id,
    company_id,
    month_first_date,
    month_last_date,
    allowed_late_entries,
    check_attendance_date,
    leave_period_data,
):
    """
    CHECKS IF EMPLOYEE HAS EXCEEDED ALLOWED LATE ENTRIES IN THE GIVEN MONTH.
    DEDUCTS LEAVES BASED ON HR SETTINGS CONFIGURATION TABLE AND CREATES PENALTY IF NEEDED.
    """
    try:
        emp_name = emp_id.get("name")
        print(f"\n\n===== PENALTY CHECK STARTED FOR: {emp_name} =====")

        # ! STEP 1: VALIDATE EMPLOYEE ELIGIBILITY
        print(f"[STEP 1] Validating eligibility for late entry penalty...")
        if not check_employee_penalty_criteria(emp_name, "For Late Arrival"):
            print(f"[INFO] {emp_name} is NOT eligible for late entry penalty.")
            return

        print(f"[INFO] {emp_name} is eligible for late entry penalty.")

        # ! STEP 2: FETCH LATE ATTENDANCE ENTRIES
        print(f"[STEP 2] Fetching late attendance entries between {month_first_date} and {month_last_date}...")
        late_attendance_list = frappe.db.get_all(
            "Attendance",
            filters={
                "docstatus": 1,
                "employee": emp_name,
                "attendance_date": ["between", [month_first_date, month_last_date]],
                "late_entry": 1,
            },
            fields=["name", "attendance_date"],
            order_by="attendance_date asc",
        )

        print(f"[INFO] Total late entries found: {len(late_attendance_list)}")
        print(f"[INFO] Allowed late entries: {allowed_late_entries}")

        if not late_attendance_list:
            print(f"[INFO] No late attendance entries for {emp_name}")
            return None

        # ! STEP 3: DETERMINE PENALIZABLE ENTRIES
        penalizable_entries = late_attendance_list[allowed_late_entries:]
        print(f"[STEP 3] Entries exceeding threshold (to penalize): {len(penalizable_entries)}")

        if not penalizable_entries:
            print(f"[INFO] No penalizable entries for {emp_name}")
            return None

        # ! STEP 4: FETCH HR SETTINGS CONFIGURATION
        print(f"[STEP 4] Fetching late entry penalty configurations from HR Settings...")
        penalty_configurations = get_late_entry_penalty_configurations()
        print(f"[INFO] Total configurations fetched: {len(penalty_configurations)}")

        if not penalty_configurations:
            print(f"[ERROR] No penalty configurations found. Skipping penalty.")
            return None

        # ! Determine deduction amount from first config
        first_config = penalty_configurations[0]
        deduction_type = first_config.get("deduction_of_leave", "Full Day")
        deduct_leave_value = 0.5 if deduction_type == "Half Day" else 1.0
        is_lwp_for_late_entry = 0  # Default to no LWP unless config forces it

        print(f"[CONFIG] Deduction Type: {deduction_type} | Deduction Value: {deduct_leave_value}")

        # ! STEP 5: LOOP OVER EACH PENALIZABLE ENTRY
        employee_scheduled_for_penalty_tomorrow = None

        for attendance_id in penalizable_entries:
            att_date = attendance_id.get("attendance_date")
            att_name = attendance_id.get("name")
            print(f"\n[ENTRY CHECK] Attendance: {att_name} | Date: {att_date}")

            leave_exists = frappe.db.exists(
                "Leave Application",
                {
                    "employee": emp_name,
                    "docstatus": 1,
                    "from_date": ["<=", att_date],
                    "to_date": [">=", att_date],
                },
            )

            regularization_exists = frappe.db.exists(
                "Attendance Regularization",
                {
                    "employee": emp_name,
                    "attendance": att_name,
                    "regularization_date": att_date,
                },
            )

            penalty_exists = frappe.db.exists(
                "Employee Penalty",
                {
                    "employee": emp_name,
                    "attendance": att_name,
                    "for_late_coming": 1,
                },
            )

            print(f"[CHECK] Leave Exists: {bool(leave_exists)} | Regularization Exists: {bool(regularization_exists)} | Existing Penalty: {bool(penalty_exists)}")

            if not (leave_exists or regularization_exists or penalty_exists):
                att_date_obj = getdate(att_date)

                if att_date_obj <= check_attendance_date:
                    print(f"[ACTION] Creating penalty for {emp_name} on {att_date}...")

                    leave_deductions_list = calculate_leave_deductions_for_late_entry(
                        emp_name,
                        company_id,
                        deduct_leave_value,
                        is_lwp_for_late_entry,
                        penalty_configurations,
                    )

                    print(f"[INFO] Final leave deductions to apply: {leave_deductions_list}")

                    create_employee_penalty(
                        emp_name,
                        att_date,
                        deduct_leave_value,
                        attendance_id=att_name,
                        leave_deductions=leave_deductions_list,
                        leave_period_data=leave_period_data,
                        is_lwp_for_late_entry=is_lwp_for_late_entry,
                        for_late_coming=1,
                    )

                elif att_date_obj == add_to_date(check_attendance_date, days=1):
                    print(f"[INFO] Penalty scheduled for tomorrow for: {emp_name}")
                    employee_scheduled_for_penalty_tomorrow = emp_name

        print(f"[RESULT] Penalty scheduling complete for {emp_name}")
        return employee_scheduled_for_penalty_tomorrow

    except Exception as e:
        frappe.log_error("Error in penalize_employee_for_late_entry", frappe.get_traceback())
        print(f"[ERROR] Exception occurred during penalty processing: {str(e)}")
        return None


# ! FUNCTION: FETCH PENALTY CONFIGURATION FROM HR SETTINGS
# ? RETURNS CONFIGS ORDERED BY IDX INCLUDING DEDUCTION OF LEAVE TYPE
def get_late_entry_penalty_configurations():
    print(f"[FETCH] Getting penalty configurations from Leave Penalty Configuration child table...")
    config_data = frappe.db.get_all(
        "Leave Penalty Configuration",
        filters={
            "parent": "HR Settings",
            "parenttype": "HR Settings",
            "parentfield": "custom_late_coming_leave_penalty_configuration",
        },
        fields=["penalty_deduction_type", "leave_type_for_penalty", "deduction_of_leave", "idx"],
        order_by="idx asc",
    )
    print(f"[FETCHED] {len(config_data)} configurations retrieved.")
    return config_data


# ! FUNCTION: COMPUTE LEAVE DEDUCTIONS BASED ON CONFIGURATION PRIORITY
def calculate_leave_deductions_for_late_entry(
    employee, company_id, total_deduction, is_lwp_for_late_entry, config_data
):
    print(f"[CALCULATE] Starting leave deduction calculation for {employee}...")
    deductions = []
    remaining = total_deduction

    if is_lwp_for_late_entry:
        print(f"[LWP MODE] Full penalty as LWP: {remaining}")
        deductions.append(
            {
                "leave_type": "Leave Without Pay",
                "deducted": remaining,
                "allocation_id": None,
            }
        )
        return deductions

    for config in config_data:
        deduction_type = config.penalty_deduction_type
        leave_type = config.leave_type_for_penalty
        print(f"[CHECK CONFIG] Type: {deduction_type} | Leave Type: {leave_type} | Remaining: {remaining}")

        if deduction_type == "Deduct Earned Leave":
            balance = get_remaining_leaves(leave_type, employee, company_id)
            print(f"[BALANCE] {leave_type} balance for {employee}: {balance}")

            if balance > 0:
                deduct_now = min(balance, remaining)
                allocation_id = frappe.db.get_value(
                    "Leave Allocation",
                    {
                        "employee": employee,
                        "leave_type": leave_type,
                        "docstatus": 1,
                    },
                    "name",
                )
                print(f"[DEDUCT] Deducting {deduct_now} from {leave_type} | Allocation ID: {allocation_id}")
                deductions.append(
                    {
                        "leave_type": leave_type,
                        "deducted": deduct_now,
                        "allocation_id": allocation_id,
                    }
                )
                remaining -= deduct_now

        elif deduction_type == "Deduct Leave Without Pay" and remaining > 0:
            print(f"[LWP FALLBACK] Applying LWP for remaining: {remaining}")
            deductions.append(
                {
                    "leave_type": "Leave Without Pay",
                    "deducted": remaining,
                    "allocation_id": None,
                }
            )
            remaining = 0

        if remaining <= 0:
            print(f"[DONE] Total deduction completed.")
            break

    print(f"[CALCULATE COMPLETE] Final Deductions List: {deductions}")
    return deductions

# ! METHOD: CREATE EMPLOYEE PENALTY ENTRY AND APPLY LEAVE DEDUCTIONS
# ? NOW SUPPORTS MULTIPLE LEAVE TYPES USING leave_deductions LIST
def create_employee_penalty(
    employee,
    penalty_date,
    deduct_leave,
    attendance_id=None,
    leave_deductions=None,  # ? List of dicts: leave_type, deducted, allocation_id
    leave_balance_before_application=0.0,
    leave_period_data=None,
    is_lwp_for_insufficient_hours=0,
    is_lwp_for_late_entry=0,
    is_lwp_for_no_attendance=0,
    for_late_coming=0,
    for_insufficient_hours=0,
    for_no_attendance=0,
    for_mispunch=0,
):
    """
    CREATES EMPLOYEE PENALTY DOCUMENT, UPDATES ATTENDANCE STATUS,
    SENDS NOTIFICATION, AND CREATES LEAVE LEDGER ENTRIES IF EARNED LEAVE DEDUCTED.
    """

    # ! DEBUG: LOG INPUT DATA
    print(f"\n\n[DEBUG] --- CREATE EMPLOYEE PENALTY START ---")
    print(f"[DEBUG] Employee: {employee}")
    print(f"[DEBUG] Penalty Date: {penalty_date}")
    print(f"[DEBUG] Total Leave Deducted: {deduct_leave}")
    print(f"[DEBUG] Attendance ID: {attendance_id}")
    print(f"[DEBUG] Leave Deductions: {leave_deductions}")
    print(
        f"[DEBUG] Leave Balance Before Application: {leave_balance_before_application}"
    )
    print(
        f"[DEBUG] Flags - LWP Late Entry: {is_lwp_for_late_entry}, Insufficient: {is_lwp_for_insufficient_hours}, No Attendance: {is_lwp_for_no_attendance}"
    )
    print(
        f"[DEBUG] Flags - Reason - Late: {for_late_coming}, Hours: {for_insufficient_hours}, No Attendance: {for_no_attendance}, Mispunch: {for_mispunch}"
    )

    # ! 1. CREATE EMPLOYEE PENALTY DOCUMENT
    penalty_doc = frappe.new_doc("Employee Penalty")
    penalty_doc.employee = employee
    penalty_doc.penalty_date = penalty_date
    penalty_doc.total_leave_penalty = deduct_leave
    penalty_doc.leave_balance_before_application = leave_balance_before_application

    # ? PROCESS LEAVE DEDUCTIONS LIST - SUM LWP AND EARNED LEAVE
    earned_leave_total = 0.0
    lwp_total = 0.0
    leave_type_used = None  # ? For info only

    for deduction in leave_deductions or []:
        lt = deduction["leave_type"]
        amt = deduction["deducted"]
        if lt == "Leave Without Pay":
            lwp_total += amt
        else:
            earned_leave_total += amt
            leave_type_used = lt  # ? Store first non-LWP type

    penalty_doc.deduct_earned_leave = earned_leave_total
    penalty_doc.deduct_leave_without_pay = lwp_total
    penalty_doc.leave_type = leave_type_used

    print(
        f"[DEBUG] Earned Leave Deducted: {earned_leave_total}, LWP Deducted: {lwp_total}, Leave Type Used: {leave_type_used}"
    )

    # ! 2. UPDATE ATTENDANCE STATUS BASED ON DEDUCTION
    if attendance_id:
        penalty_doc.attendance = attendance_id
        attendance_status = frappe.db.get_value("Attendance", attendance_id, "status")
        print(f"[DEBUG] Attendance Status Before Update: {attendance_status}")

        if deduct_leave == 0.5:
            if attendance_status == "Present":
                frappe.db.set_value("Attendance", attendance_id, "status", "Half Day")
                print(f"[DEBUG] Attendance Status Updated to Half Day")
            elif attendance_status == "Half Day":
                frappe.db.set_value("Attendance", attendance_id, "status", "Absent")
                print(f"[DEBUG] Attendance Status Updated to Absent")
        elif deduct_leave > 0.5:
            frappe.db.set_value("Attendance", attendance_id, "status", "Absent")
            print(f"[DEBUG] Attendance Status Updated to Absent")

    # ! 3. SET PENALTY REASON FLAGS AND REMARKS
    if for_late_coming:
        penalty_doc.for_late_coming = 1
        penalty_doc.remarks = f"Penalty for Late Entry on {penalty_date}"
    if for_insufficient_hours:
        penalty_doc.for_insufficient_hours = 1
        penalty_doc.remarks = f"Penalty for Insufficient Hours on {penalty_date}"
    if for_no_attendance:
        penalty_doc.for_no_attendance = 1
        penalty_doc.remarks = f"Penalty for No Attendance on {penalty_date}"
    if for_mispunch:
        penalty_doc.for_mispunch = 1
        penalty_doc.remarks = f"Penalty for Mispunch on {penalty_date}"

    print(f"[DEBUG] Remarks Set: {penalty_doc.remarks}")

    # ! 4. INSERT PENALTY DOCUMENT
    penalty_doc.insert(ignore_permissions=True)
    print(f"[DEBUG] Penalty Document Created: {penalty_doc.name}")

    # ! 5. LINK PENALTY ID TO ATTENDANCE
    if attendance_id:
        frappe.db.set_value(
            "Attendance", attendance_id, "custom_employee_penalty_id", penalty_doc.name
        )
        print(f"[DEBUG] Penalty Linked to Attendance: {attendance_id}")

    # ! 6. SEND EMAIL NOTIFICATION TO EMPLOYEE (ONLY FOR PROMPT COMPANY)
    try:
        company = fetch_company_name(prompt=1)
        employee_doc = frappe.get_doc("Employee", employee)

        if company:
            company_id = company.get("company_id")
            if company_id and employee_doc.company == company_id:
                notification = frappe.get_doc("Notification", "Employee Penalty Alert")
                if notification and employee_doc.user_id:
                    user_doc = frappe.get_doc("User", employee_doc.user_id)
                    email_id = getattr(user_doc, "email", None)

                    if email_id:
                        reason = ""
                        if penalty_doc.for_late_coming:
                            reason = "Late Entry"
                        elif penalty_doc.for_insufficient_hours:
                            reason = "Insufficient Working Hours"
                        elif penalty_doc.for_no_attendance:
                            reason = "No Attendance"

                        subject = frappe.render_template(
                            notification.subject, {"reason": reason, "doc": penalty_doc}
                        )
                        message = frappe.render_template(
                            notification.message, {"reason": reason, "doc": penalty_doc}
                        )
                        frappe.sendmail(
                            recipients=[email_id], subject=subject, message=message
                        )
                        print(f"[DEBUG] Notification sent to {email_id}")
                    else:
                        print(
                            f"[DEBUG] Email not found for user: {employee_doc.user_id}"
                        )
                else:
                    print(f"[DEBUG] Notification or user ID missing")
    except Exception as e:
        frappe.log_error("Penalty Email Error", frappe.get_traceback())
        print(f"[ERROR] Exception in sending email: {str(e)}")

    # ! 7. CREATE LEAVE LEDGER ENTRY FOR EACH EARNED LEAVE DEDUCTION
    if earned_leave_total > 0:
        print(f"[DEBUG] Creating Leave Ledger Entries for Earned Leaves...")
        for deduction in leave_deductions or []:
            if deduction["leave_type"] != "Leave Without Pay":
                try:
                    print(
                        f"[DEBUG] Creating Ledger Entry | Leave Type: {deduction['leave_type']} | Amount: {deduction['deducted']}"
                    )
                    add_leave_ledger_entry(
                        employee,
                        deduction["leave_type"],
                        deduction["allocation_id"],
                        leave_period_data,
                        deduction["deducted"],
                    )
                except Exception as le:
                    frappe.log_error(
                        "Ledger Entry Creation Failed", frappe.get_traceback()
                    )
                    print(
                        f"[ERROR] Failed to create ledger entry for {deduction['leave_type']}: {str(le)}"
                    )

    # ! 8. FINAL COMMIT
    frappe.db.commit()
    print(f"[DEBUG] Penalty {penalty_doc.name} committed to DB.")
    print(f"[DEBUG] --- CREATE EMPLOYEE PENALTY END ---\n\n")



@frappe.whitelist()
def penalize_incomplete_day_for_prompt(
      emp,
    check_attendance_date,
    expected_work_hours,
    leave_period_data,
    is_lwp_for_insufficient_hours,
    daily_hours_leave_type,
    insufficient_hours_deduct_leave,
    company_id,
):
    """
    Method to penalize employee if daily working hours are below expected threshold.
    Supports leave priority configuration from HR Settings -> custom_daily_hour_leave_penalty_configuration.
    """
    import json

    try:
        print(f"\n[DEBUG] --- PENALIZE INCOMPLETE DAY START ---")
        print(f"[DEBUG] Employee: {emp.get('name')}, Date: {check_attendance_date}, Expected Hours: {expected_work_hours}")
        print(f"[DEBUG] LWP Flag: {is_lwp_for_insufficient_hours}, Deduct Leave: {insufficient_hours_deduct_leave}, Company: {company_id}")
        
        if not check_employee_penalty_criteria(emp.get("name"), "For Work Hours"):
            print(f"[DEBUG] Penalty criteria failed for employee {emp.get('name')}. Skipping...")
            return

        # 1. FETCH ATTENDANCE RECORDS FOR DATE
        attendance_list = frappe.db.get_all(
            "Attendance",
            filters={
                "docstatus": 1,
                "employee": emp.get("name"),
                "attendance_date": check_attendance_date,
            },
            fields=["name", "attendance_date", "working_hours"],
            order_by="attendance_date asc",
        )

        print(f"[DEBUG] Attendance Records Found: {len(attendance_list)}")

        attendance_list = [
            a for a in attendance_list if 0 < a.working_hours < expected_work_hours
        ]

        print(f"[DEBUG] Filtered for Incomplete Work Hours: {len(attendance_list)}")

        if not attendance_list:
            print(f"[DEBUG] No eligible attendance entries for penalty.")
            return None

        employee_scheduled_for_penalty_tomorrow = None

        # 2. FETCH LEAVE PRIORITY CONFIGURATION
        leave_priority_raw = frappe.db.get_all(
            "Leave Penalty Configuration",
            filters={
                "parent": "HR Settings",
                "parenttype": "HR Settings",
                "parentfield": "custom_daily_hour_leave_penalty_configuration",
            },
            fields=["penalty_deduction_type", "leave_type_for_penalty", "idx"],
            order_by="idx asc",
        )
        print(f"[DEBUG] Raw Leave Priority Records: {leave_priority_raw}")

        leave_priority = [rec["leave_type_for_penalty"] for rec in leave_priority_raw]

        print(f"[DEBUG] Leave Deduction Priority Order: {leave_priority}")

        # 3. DETERMINE LEAVE DEDUCTIONS
        earned_leave = 0.0
        lwp_leave = 0.0
        leave_deductions = []

        if not is_lwp_for_insufficient_hours:
            print(f"[DEBUG] Starting Earned Leave Deduction Calculation...")

            for leave_type in leave_priority:
                balance = get_remaining_leaves(leave_type, emp.get("name"), company_id)
                print(f"[DEBUG] Leave Type: {leave_type} | Remaining Balance: {balance}")

                if balance > 0:
                    deduction = min(balance, insufficient_hours_deduct_leave - earned_leave)
                    earned_leave += deduction

                    leave_allocation_id = frappe.db.get_value(
                        "Leave Allocation",
                        {
                            "employee": emp.get("name"),
                            "leave_type": leave_type,
                            "docstatus": 1,
                        },
                        "name",
                    )

                    leave_deductions.append(
                        {
                            "leave_type": leave_type,
                            "deducted": deduction,
                            "allocation_id": leave_allocation_id,
                        }
                    )
                    print(f"[DEBUG] Deducting {deduction} from {leave_type} | Allocation ID: {leave_allocation_id}")

                if earned_leave >= insufficient_hours_deduct_leave:
                    break

            if earned_leave < insufficient_hours_deduct_leave:
                lwp_leave = insufficient_hours_deduct_leave - earned_leave
                leave_deductions.append(
                    {
                        "leave_type": "Leave Without Pay",
                        "deducted": lwp_leave,
                        "allocation_id": None,
                    }
                )
                print(f"[DEBUG] Remaining Leave Shortfall {lwp_leave}, Deducting as LWP")

        else:
            lwp_leave = insufficient_hours_deduct_leave
            leave_deductions.append(
                {
                    "leave_type": "Leave Without Pay",
                    "deducted": lwp_leave,
                    "allocation_id": None,
                }
            )
            print(f"[DEBUG] Full Penalty Deducted as LWP: {lwp_leave}")

        print(f"[DEBUG] Final Leave Deductions: {leave_deductions}")

        # 4. APPLY PENALTY FOR EACH ATTENDANCE RECORD
        for attendance in attendance_list:
            print(f"\n[DEBUG] Processing Attendance: {attendance.get('name')} | Date: {attendance.get('attendance_date')}")

            leave_application_exists = frappe.db.exists(
                "Leave Application",
                {
                    "employee": emp.get("name"),
                    "docstatus": 1,
                    "from_date": ["<=", attendance.get("attendance_date")],
                    "to_date": [">=", attendance.get("attendance_date")],
                },
            )

            attendance_regularization_exists = frappe.db.get_all(
                "Attendance Regularization",
                {
                    "employee": emp.get("name"),
                    "attendance": attendance.get("name"),
                    "regularization_date": attendance.get("attendance_date"),
                },
                "name",
            )

            employee_penalty_exists = frappe.db.exists(
                "Employee Penalty",
                {
                    "employee": emp.get("name"),
                    "attendance": attendance.get("name"),
                    "for_insufficient_hours": 1,
                },
            )

            print(f"[DEBUG] Leave Exists: {leave_application_exists} | Regularization Exists: {bool(attendance_regularization_exists)} | Penalty Exists: {employee_penalty_exists}")

            if not (
                leave_application_exists
                or attendance_regularization_exists
                or employee_penalty_exists
            ):
                print(f"[DEBUG] Applying Penalty for Attendance {attendance.get('name')}")
                create_employee_penalty(
                    emp.get("name"),
                    attendance.get("attendance_date"),
                    insufficient_hours_deduct_leave,
                    attendance_id=attendance.get("name"),
                    leave_deductions=leave_deductions,
                    leave_balance_before_application=earned_leave,
                    leave_period_data=leave_period_data,
                    is_lwp_for_insufficient_hours=is_lwp_for_insufficient_hours,
                    for_insufficient_hours=1,
                )
            else:
                print(f"[DEBUG] Skipping Penalty for Attendance {attendance.get('name')}")

            if getdate(attendance.get("attendance_date")) == add_to_date(check_attendance_date, days=1):
                employee_scheduled_for_penalty_tomorrow = emp.get("name")

        print(f"[DEBUG] --- PENALIZE INCOMPLETE DAY END ---\n")
        return employee_scheduled_for_penalty_tomorrow

    except Exception as e:
        frappe.log_error("Error in penalize_incomplete_day scheduler", frappe.get_traceback())
        print("[ERROR] Exception occurred. See error log for traceback.")

@frappe.whitelist()
def penalization_for_no_attendance_for_prompt(
    emp,
    check_attendance_date,
    leave_period_data,
    no_attendance_leave_type,
    no_attendance_deduct_leave,
    company_id,
):
    """
    Penalize employee for no attendance on a given date.
    Applies penalty based on leave priority configuration for no attendance.
    """
    import json

    try:
        print(f"\n\n[DEBUG] penalization_for_no_attendance_for_prompt CALLED --- Employee: {emp.get('name')} | Date: {check_attendance_date}\n\n")

        if not check_employee_penalty_criteria(emp.get("name"), "For No Attendance"):
            print(f"[DEBUG] Penalty Criteria Failed. Exiting.")
            return

        # ? CHECK ATTENDANCE EXISTS FOR DATE
        if frappe.db.exists(
            "Attendance",
            {
                "employee": emp.get("name"),
                "attendance_date": check_attendance_date,
                "docstatus": 1,
            },
        ):
            print(f"[DEBUG] Attendance Exists. No Penalty Applied.\n")
            return None

        print(f"[DEBUG] No Attendance Found. Checking for leave/regularization/penalty on {check_attendance_date}")

        employee_scheduled_for_penalty_tomorrow = None

        # ? EXISTING CHECKS FOR LEAVE OR REGULARIZATION ON THE SAME DAY
        leave_application_exists = frappe.db.exists(
            "Leave Application",
            {
                "employee": emp.get("name"),
                "docstatus": 1,
                "from_date": ["<=", check_attendance_date],
                "to_date": [">=", check_attendance_date],
            },
        )

        attendance_regularization_exists = frappe.db.exists(
            "Attendance Regularization",
            {
                "employee": emp.get("name"),
                "regularization_date": check_attendance_date,
            },
            "name",
        )

        employee_penalty_exists = frappe.db.exists(
            "Employee Penalty",
            {
                "employee": emp.get("name"),
                "penalty_date": check_attendance_date,
                "for_no_attendance": 1,
            },
        )

        # ? FETCH LEAVE PRIORITY CONFIGURATION FROM HR SETTINGS
        leave_priority_raw = frappe.db.get_all(
            "Leave Penalty Configuration",
            filters={
                "parent": "HR Settings",
                "parenttype": "HR Settings",
                "parentfield": "custom_no_attendance_leave_penalty_configuration",
            },
            fields=["penalty_deduction_type", "leave_type_for_penalty", "idx"],
            order_by="idx asc",
        )
        print(f"[DEBUG] Leave Priority Raw Config: {leave_priority_raw}")

        leave_priority = [rec["leave_type_for_penalty"] for rec in leave_priority_raw]
        print(f"[DEBUG] Leave Deduction Priority Order: {leave_priority}")

        # DETERMINE LEAVE DEDUCTIONS
        earned_leave = 0.0
        lwp_leave = 0.0
        leave_deductions = []

        for leave_type in leave_priority:
            balance = get_remaining_leaves(leave_type, emp.get("name"), company_id)
            print(f"[DEBUG] Leave Type: {leave_type} | Balance: {balance}")

            if balance > 0:
                deduction = min(balance, no_attendance_deduct_leave - earned_leave)
                earned_leave += deduction

                leave_allocation_id = frappe.db.get_value(
                    "Leave Allocation",
                    {
                        "employee": emp.get("name"),
                        "leave_type": leave_type,
                        "docstatus": 1,
                    },
                    "name",
                )

                leave_deductions.append(
                    {
                        "leave_type": leave_type,
                        "deducted": deduction,
                        "allocation_id": leave_allocation_id,
                    }
                )

                print(f"[DEBUG] Deducted {deduction} from {leave_type} | Allocation ID: {leave_allocation_id}")

            if earned_leave >= no_attendance_deduct_leave:
                break

        if earned_leave < no_attendance_deduct_leave:
            lwp_leave = no_attendance_deduct_leave - earned_leave
            leave_deductions.append(
                {
                    "leave_type": "Leave Without Pay",
                    "deducted": lwp_leave,
                    "allocation_id": None,
                }
            )
            print(f"[DEBUG] Remaining Leave Shortfall {lwp_leave}, Deducted as LWP")

        print(f"[DEBUG] Final Leave Deductions: {leave_deductions}")

        if not (
            leave_application_exists
            or attendance_regularization_exists
            or employee_penalty_exists
        ):
            print(f"[DEBUG] Creating Absent Attendance and Applying Penalty")

            # Create Absent Attendance
            att = frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "employee": emp.get("name"),
                    "attendance_date": check_attendance_date,
                    "status": "Absent",
                    "company": emp.get("company"),
                    "docstatus": 0,
                }
            )
            att.insert(ignore_permissions=True)
            att.submit()
            frappe.db.commit()

            # Apply Penalty with leave_deductions
            create_employee_penalty(
                emp.get("name"),
                check_attendance_date,
                no_attendance_deduct_leave,
                attendance_id=att.name,
                leave_deductions=leave_deductions,
                leave_balance_before_application=earned_leave,
                leave_period_data=leave_period_data,
                is_lwp_for_no_attendance=1,
                for_no_attendance=1,
            )
        else:
            print(f"[DEBUG] Penalty Skipped due to existing Leave/Regularization/Penalty")

        # CHECK FOR NEXT-DAY PENALTY REMINDER
        next_day = add_days(check_attendance_date, 1)

        leave_application_exists_next_day = frappe.db.exists(
            "Leave Application",
            {
                "employee": emp.get("name"),
                "docstatus": 1,
                "from_date": ["<=", next_day],
                "to_date": [">=", next_day],
            },
        )

        attendance_regularization_exists_next_day = frappe.db.exists(
            "Attendance Regularization",
            {
                "employee": emp.get("name"),
                "regularization_date": next_day,
            },
            "name",
        )

        employee_penalty_exists_next_day = frappe.db.exists(
            "Employee Penalty",
            {
                "employee": emp.get("name"),
                "penalty_date": next_day,
                "for_no_attendance": 1,
            },
        )

        if not (
            leave_application_exists_next_day
            or attendance_regularization_exists_next_day
            or employee_penalty_exists_next_day
        ):
            employee_scheduled_for_penalty_tomorrow = emp.get("name")
            print(f"[DEBUG] Scheduled Penalty Reminder for Tomorrow: {employee_scheduled_for_penalty_tomorrow}")

        print(f"[DEBUG] --- END ---\n\n")
        return employee_scheduled_for_penalty_tomorrow

    except Exception as e:
        frappe.log_error(
            "Error in penalization_for_no_attendance_for_prompt", frappe.get_traceback()
        )
        print("[ERROR] Exception occurred. See error log for traceback.")


def get_week_off_days(weekly_off_type):
    """Method to get the week off days based on the weekly off type"""
    days = frappe.db.get_all(
        "WeekOff Multiselect",
        {"parenttype": "WeeklyOff Type", "parent": weekly_off_type},
        "weekoff",
        pluck="weekoff",
    )
    return days or []


def get_last_full_work_week(ref_date, weekly_off_days, expected_work_days):
    """Method to get the last full work week based on the reference date and weekly off days and expected work days"""
    day = ref_date
    while True:
        # * GOING BACKWARDS FORM THE REFERENCE DATE TO LOCATE THE LAST CONTINUOUS BLOCK OF WEEKLY OFF DAYS.

        if day.strftime("%A") in weekly_off_days:
            prev_day = day - timedelta(days=1)
            if prev_day.strftime("%A") in weekly_off_days:
                day = prev_day  # * CONTINUE GOING BACKWARDS IF THE PREVIOUS DAY IS ALSO A WEEKOFF
                continue
            break
        day -= timedelta(days=1)  # * KEEP MOVING BACK UNTIL WE FIND A WEEKOFF DAY

    # * DEPENDING ON THE FIRST WEEKOFF DAY WE ARE GOING BACKWARDS TO FIND THE LAST FULL WORK WEEK
    start = day - timedelta(days=1)
    working_days = []
    current = start
    while len(working_days) < expected_work_days:
        if current.strftime("%A") not in weekly_off_days:
            working_days.insert(0, current)  # prepend to maintain chronological order
        current -= timedelta(days=1)
    return working_days[0], working_days[-1]
    # print(f"\n\n {day} \n\n")
    # start = day + timedelta(days=1)
    # working_days = []
    # current = start

    # print(f"\n\n {current} \n\n")
    # while len(working_days) < expected_work_days:
    #     if current.strftime("%A") not in weekly_off_days:
    #         working_days.append(current)
    #     current += timedelta(days=1)
    # return working_days[0], working_days[-1]


def get_next_working_day_after_weekoffs(start_date, weekly_off_days):

    current = start_date
    while current.strftime("%A") in weekly_off_days:
        current += timedelta(days=1)
    print(f"\n\n current {current} \n\n")
    return current


def get_next_work_week(last_eval_date, weekly_off_days, expected_work_days):

    current = last_eval_date
    working_days = []
    while len(working_days) < expected_work_days:
        if current.strftime("%A") not in weekly_off_days:
            working_days.append(current)
        current += timedelta(days=1)
    return working_days[0], working_days[-1]


def get_working_days(start_date, end_date, weekly_off_days):
    days = []
    current = start_date
    while current <= end_date:
        if current.strftime("%A") not in weekly_off_days:
            days.append(current)
        current += timedelta(days=1)
    return days


def get_total_working_hours(employee, dates):
    hours = 0
    for day in dates:
        attendance = frappe.get_all(
            "Attendance",
            filters={
                "employee": employee,
                "attendance_date": day,
                "status": ["in", ["Present", "Work From Home", "Half Day"]],
            },
            fields=["working_hours"],
        )
        hours += sum([i.working_hours for i in attendance])
    return hours


# def calculate_daily_hours(checkins):
#     times = sorted([c.time for c in checkins])
#     if len(times) < 2:
#         return 0
#     total = 0
#     for i in range(0, len(times)-1, 2):
#         diff = (times[i+1] - times[i]).total_seconds() / 3600
#         total += diff
#     return total


def get_remaining_leaves(leave_type, employee, company_id):
    """Method to get the remaining leave balance for the employee"""

    leave_ledger_entry_id = frappe.db.get_all(
        "Leave Ledger Entry",
        {
            "docstatus": 1,
            "employee": employee,
            "leave_type": leave_type,
            "company": company_id,
        },
        ["name", "leaves"],
    )

    if leave_ledger_entry_id:
        leave_balance = sum(i.leaves for i in leave_ledger_entry_id)
    else:
        leave_balance = 0.0
    return leave_balance


# ! METHOD: ADD LEAVE LEDGER ENTRY FOR PENALTY DEDUCTION
# ? CREATES NEGATIVE ENTRY AGAINST ALLOCATION BASED ON PENALTY
@frappe.whitelist()
def add_leave_ledger_entry(
    employee, leave_type, leave_allocation_id, leave_period_data, earned_leave
):
    """
    CREATES A LEAVE LEDGER ENTRY DEDUCTING earned_leave AMOUNT FROM THE GIVEN LEAVE TYPE.
    ASSOCIATED TO leave_allocation_id FOR REFERENCE.
    """
    try:
        # ! 1. VALIDATE INPUT
        if not leave_period_data:
            print(
                f"[ERROR] leave_period_data is None. Cannot create leave ledger entry."
            )
            return  # Prevent exception due to missing dates

        from_date = leave_period_data.get("from_date")
        to_date = leave_period_data.get("to_date")

        print(f"\n[DEBUG] Creating Leave Ledger Entry")
        print(f"[DEBUG] Employee: {employee}")
        print(f"[DEBUG] Leave Type: {leave_type}")
        print(f"[DEBUG] Allocation ID: {leave_allocation_id}")
        print(f"[DEBUG] From Date: {from_date} | To Date: {to_date}")
        print(f"[DEBUG] Deduction (Negative): {-abs(earned_leave)}")

        # ! 2. CREATE LEAVE LEDGER ENTRY DOCUMENT
        leave_ledger_entry_doc = frappe.new_doc("Leave Ledger Entry")
        leave_ledger_entry_doc.employee = employee
        leave_ledger_entry_doc.leave_type = leave_type
        leave_ledger_entry_doc.transaction_type = "Leave Allocation"
        leave_ledger_entry_doc.transaction_name = leave_allocation_id
        leave_ledger_entry_doc.from_date = getdate(today())
        leave_ledger_entry_doc.to_date = to_date
        leave_ledger_entry_doc.leaves = -abs(earned_leave)  # Always deduct as negative

        # ! 3. INSERT AND SUBMIT ENTRY
        leave_ledger_entry_doc.insert(ignore_permissions=True)
        leave_ledger_entry_doc.submit()
        frappe.db.commit()
        return leave_ledger_entry_doc.name
        print(f"[DEBUG] Leave Ledger Entry Created: {leave_ledger_entry_doc.name}")

    except Exception as e:
        print(
            f"[ERROR] Failed to create leave ledger entry for {employee} | {leave_type}"
        )
        frappe.log_error(
            "Error in add_leave_ledger_entry scheduler method", frappe.get_traceback()
        )


# @frappe.whitelist()
# def generate_attendance():
#     """Generate Employee Attendance and Check the weekoff
#     """
#     try:
#         employee_list = frappe.db.get_all("Employee", {"status": "Active"}, "name")

#         yesterday_date = add_to_date(days=-1, as_string=True)

#         start = get_datetime(yesterday_date + " 00:00:00")
#         end = get_datetime(yesterday_date + " 23:59:59")
#         if employee_list:
#             for employee_id in employee_list:
#                 emp_check_in = frappe.db.get_all("Employee Checkin", {"employee": employee_id.get("name"), "log_type": "IN", "time": ["between", [start, end]]}, "name", group_by="time asc")
#                 print(f"\n\n {emp_check_in} \n\n")

#     except Exception as e:
#         frappe.log_error("Error While Generating Attendance", frappe.get_traceback())

# @frappe.whitelist()
# def allow_checkin_from_website_to_employee():
#     """Method to check if the current date is between the from and to date of attendance request then allow the employee to checkin from website for the time period
#     """
#     try:
#         attendance_request = frappe.db.get_all("Attendance Request", {"docstatus": 1, "custom_status": "Approved"})
#     except Exception as e:
#         frappe.log_error("Error in allow_checkin_from_website_to_employee schedular method", frappe.get_traceback())


def check_employee_penalty_criteria(employee=None, penalization_type=None):
    employee = frappe.get_doc("Employee", employee)
    company_abbr = frappe.db.get_value("Company", employee.company, "abbr")
    hr_settings = frappe.get_single("HR Settings")

    # Field mapping
    criteria = {
        "Business Unit": "custom_business_unit",
        "Department": "department",
        "Address": "custom_work_location",
        "Employment Type": "employment_type",
        "Employee Grade": "grade",
        "Designation": "designation",
        "Product Line": "custom_product_line",
    }

    # Abbreviations
    prompt_abbr = hr_settings.custom_prompt_abbr
    indifoss_abbr = hr_settings.custom_indifoss_abbr

    # Determine which table to use based on company
    if company_abbr == prompt_abbr:
        table = hr_settings.custom_penalization_criteria_table_for_prompt
    elif company_abbr == indifoss_abbr:
        table = hr_settings.custom_penalization_criteria_table_for_indifoss
    else:
        return True  # Default allow if company doesn't match

    if not table:
        return True  # Allow if table is not configured

    is_penalisation = False
    for row in table:
        if row.penalization_type != penalization_type:
            continue

        is_penalisation = True
        if row.select_doctype == "Department" and row.is_sub_department:
            if employee.custom_subdepartment == row.value:
                return True
        else:
            employee_fieldname = criteria.get(row.select_doctype)
            if (
                employee_fieldname
                and getattr(employee, employee_fieldname, None) == row.value
            ):
                return True

    return not is_penalisation or False


# ? DAILY SCHEDULER TO HANDLE EXIT CHECKLIST & INTERVIEW AUTOMATICALLY
def process_exit_approvals():
    today_date = getdate(today())
    print(f"\n=== Running Exit Approval Scheduler on {today_date} ===\n")

    records = frappe.get_all(
        "Exit Approval Process",
        filters={"resignation_approval": "Approved"},
        fields=[
            "name",
            "employee",
            "company",
            "custom_exit_checklist_notification_date",
            "custom_exit_questionnaire_notification_date",
            "employee_separation",
            "exit_interview",
        ],
    )
    print(f"Found {len(records)} approved exit approvals to process.\n")

    for r in records:
        try:
            print(
                f"> Processing: {r.name} | Employee: {r.employee} | Company: {r.company}"
            )

            # ? PROCESS CHECKLIST IF DUE AND NOT YET CREATED
            checklist_due = (
                r.custom_exit_checklist_notification_date
                and getdate(r.custom_exit_checklist_notification_date) <= today_date
                and not r.employee_separation
            )
            if checklist_due:
                print("  - Raising Exit Checklist...")
                result = raise_exit_checklist(r.employee, r.company, r.name)
                print(f"  ✔ Checklist Result: {result.get('message')}")

            # ? PROCESS EXIT INTERVIEW IF DUE AND NOT YET CREATED
            interview_due = (
                r.custom_exit_questionnaire_notification_date
                and getdate(r.custom_exit_questionnaire_notification_date) <= today_date
                and not r.exit_interview
            )
            if interview_due:
                print("  - Raising Exit Interview...")
                result = raise_exit_interview(r.employee, r.company, r.name)
                print(f"  ✔ Interview Result: {result.get('message')}")

        except Exception as e:
            print(f"  ✖ ERROR while processing {r.name}: {str(e)}")
            frappe.log_error(
                title="Auto Exit Process Error",
                message=frappe.get_traceback()
                + f"\n\nEmployee: {r.employee}, Company: {r.company}",
            )

    print("\n=== Scheduler Execution Complete ===\n")


def send_penalty_warnings(emp_id, penalization_data, penalization_date=None):
    try:
        if not penalization_date:
            penalization_date = add_days(today(), 1)

        notification = frappe.get_doc("Notification", "Alert For Penalization")

        # Fetch employee
        employee = frappe.get_doc("Employee", emp_id)

        # Fetch user email
        email_id = get_employee_email(employee.name)
        if not email_id:
            frappe.log_error(f"Email not found for Employee {employee.name}")
            return

        email_details = {}
        if notification:
            # Render and send email
            attendance_link = None
            for data in penalization_data.values():
                try:
                    if data.get("attendance"):
                        attendance_link = f"{frappe.utils.get_url()}/app/attendance/{data.get('attendance')}"
                        break
                except Exception as e:
                    frappe.log_error("Error in Getting Attendance Link", str(e))
                    continue

            subject = frappe.render_template(
                notification.subject, {"employee_name": employee.name}
            )
            message = frappe.render_template(
                notification.message,
                {
                    "employee_name": employee.name,
                    "penalization_date": penalization_date,
                    "penalization_data": penalization_data,
                    "company": employee.company,
                    "attendance_link": attendance_link
                },
            )
            # frappe.sendmail(
            #     recipients=[email_id],
            #     subject=subject,
            #     message=message,
            # )
            email_details["email"] = email_id
            email_details["subject"] = subject
            email_details["message"] = message
        
        return email_details
    except Exception as e:
        frappe.log_error(f"Error in send_penalty_warnings:",{str(e)})



@frappe.whitelist()
def send_attendance_issue_mail_check(attendance_check_date):
    frappe.log_error("send_attendance_issue_check_started", f"Started")
    send_attendance_issue(attendance_check_date)
    frappe.log_error("send_attendance_issue_check_ended", f"Ended")
    

def send_attendance_issue(attendance_check_date=None):
    try:
        frappe.log_error("send_attendance_issue called", "send_attendance_issue")
        # * Set the date to check (1 day before today)
        if not attendance_check_date:
            attendance_check_date = add_days(today(), -1)

        add_to_penalty_email = frappe.db.get_single_value("HR Settings", "custom_add_emails_to_penalty_emails_for_prompt")
        # * Fetch PROMPT Company ID
        company_id = fetch_company_name(prompt=1)

        # * Load the notification template
        notification = frappe.get_doc("Notification", "Attendance Issue Reminder")

        # ! Handle company fetch failure
        if company_id.get("error"):
            frappe.log_error(
                "Error in penalize_employee_for_late_entry", frappe.get_traceback()
            )
            return

        prompt_employee_list = []
        penalty_emails = []
        
        # * Proceed if company_id exists
        if company_id.get("company_id"):
            prompt_employee_list = frappe.db.get_all(
                "Employee",
                filters={"status": "Active", "company": company_id.get("company_id")},
                fields=["name", "holiday_list", "user_id", "company"],
            )

            if prompt_employee_list:
                frappe.log_error(f"Found {len(prompt_employee_list)} active employees in PROMPT", "send_attendance_issue")
                
                for emp in prompt_employee_list:
                    
                    # * Use date range for creation field, or use attendance_date if available
                    date_start = attendance_check_date + " 00:00:00"
                    date_end = (
                        datetime.strptime(attendance_check_date, "%Y-%m-%d")
                        + timedelta(days=1)
                    ).strftime("%Y-%m-%d 00:00:00")

                    # * GET ATTENDANCE OF EMPLOYEE
                    attendance = frappe.get_all(
                        "Attendance",
                        filters=[
                            ["employee", "=", emp.get("name")],
                            ["creation", ">=", date_start],
                            ["creation", "<", date_end],
                            ["docstatus", "=", 1],
                        ],
                        fields=["*"],
                        limit=1,
                    ) or []
                    
                    frappe.log_error(f"Attendance for {emp.get('name')} on {attendance_check_date}", f"send_attendance_issue {attendance}")
                    # * Check if it's a holiday or weekly off
                    holiday_or_weekoff = is_holiday_or_weekoff(
                        emp.get("name"), attendance_check_date
                    )

                    if holiday_or_weekoff.get("is_holiday"):
                        
                        frappe.log_error(f"Skipping {emp.get('name')} for {attendance_check_date} as it's a holiday/weekoff", "send_attendance_issue")
                        continue  # ! Skip if it's a holiday
                    
                    # ? CASE 1: No attendance found
                    if not attendance:
                    # if not attendance:
                        if is_send_mail_check(emp.get("name"), is_no_attendance=1, attendance_date=attendance_check_date):
                            
                            frappe.log_error(f"No attendance found for {emp.get('name')} on {attendance_check_date}", "send_attendance_issue")
                            
                            employee_name = frappe.db.get_value(
                                "Employee", emp.get("name"), "employee_name"
                            )
                            # * Render subject & message for "No Attendance"
                            subject = frappe.render_template(
                                notification.subject,
                                {
                                    "issue_type": "No Attendance",
                                    "doc": {
                                        "employee_name": employee_name,
                                        "attendance_date": attendance_check_date,
                                    },
                                },
                            )
                            message = frappe.render_template(
                                notification.message,
                                {
                                    "issue_type": "No Attendance",
                                    "doc": {
                                        "employee_name": employee_name,
                                        "attendance_date": attendance_check_date,
                                        "company": emp.get("company"),
                                    },
                                },
                            )
                            
                            if add_to_penalty_email:
                                penalty_emails.append({
                                    "email": emp.user_id,
                                    "subject": subject,
                                    "message": message
                                })
                            else:
                                if emp.user_id:
                                    frappe.sendmail(
                                        recipients=[emp.user_id],
                                        subject=subject,
                                        message=message,
                                    )

                    # ? CASE 2: Attendance found, check for issues
                    else:
                        frappe.log_error(f"Attendance found for {emp.get('name')} on {attendance_check_date}", f"{attendance} send_attendance_issue")
                        att = attendance[0]

                        if att.status == "Mispunch" or att.late_entry:
                        # if (att.status == "Mispunch" and mispunch_penalty_enabled) or (att.late_entry and late_coming_penalty_enabled):

                            send_mail = 0
                            # * Determine attendance issue type
                            if att.status == "Mispunch":
                                attendance_issue = "Attendance Mispunch"
                                send_mail = is_send_mail_check(emp.get("name"), is_mispunch=1, attendance_date=attendance_check_date)
                            elif att.late_entry:
                                attendance_issue = "Late Entry"
                                send_mail = is_send_mail_check(emp.get("name"), is_later_entry=1, attendance_date=attendance_check_date)
                            
                                
                            if not send_mail:
                                continue
                            # * Render subject & message based on issue
                            subject = frappe.render_template(
                                notification.subject,
                                {"issue_type": attendance_issue, "doc": att},
                            )
                            message = frappe.render_template(
                                notification.message,
                                {"issue_type": attendance_issue, "doc": att},
                            )
                            
                            if add_to_penalty_email:
                                penalty_emails.append({
                                    "email": emp.user_id,
                                    "subject": subject,
                                    "message": message
                                })
                            else:
                                if emp.user_id:
                                    frappe.sendmail(
                                        recipients=[emp.user_id],
                                        subject=subject,
                                        message=message,
                                    )

            frappe.log_error("send_attendance_issue_penalty_emails", f"{penalty_emails}")
            
            if penalty_emails and add_to_penalty_email:
                try:
                    penalty_emails_doc = frappe.get_doc({
                        "doctype": "Penalty Emails",
                        "status": "Not Sent",
                        "email_details": penalty_emails
                    })
                
                    penalty_emails_doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                except Exception as e:
                    frappe.log_error("Error_while_creating_penalty_emails", frappe.get_traceback())
    except Exception as e:
        frappe.log_error("Error in send_attendance_issue", frappe.get_traceback())


def is_send_mail_check(emp_id, is_no_attendance=0, is_mispunch=0, is_later_entry=0, attendance_date=None):
    try:
        hr_settings_doc = frappe.get_single("HR Settings")
        
        if not is_no_attendance and not is_mispunch and not is_later_entry:
            return 0
        
        frappe.log_error("checking_send mail", "")
        if is_no_attendance:
            frappe.log_error("checking_send mail", "No Attendance")
            if hr_settings_doc.custom_enable_no_attendance_penalty:
                for row in hr_settings_doc.custom_penalization_criteria_table_for_prompt:
                    if row.penalization_type == "For No Attendance" and row.get("value") == frappe.db.get_value("Employee", emp_id, row.get("employee_field_name")):
                        frappe.log_error("checking_send mail", "No attendance criteria matched")
                        return 1
                    frappe.log_error("checking_send mail", "No attendance criteria not matched")
                    
                return 0
            else:
                frappe.log_error("checking_send mail", "No attendance penalty not enabled")
                return 0
        else:
            if is_mispunch:
                frappe.log_error(f"checking_send mail for {emp_id}", "Mispunch")
                if hr_settings_doc.custom_enable_mispunch_penalty:
                    frappe.log_error(f"checking_send mail for {emp_id}", "Mispunch Enabled")
                    
                    for row in hr_settings_doc.custom_penalization_criteria_table_for_prompt:
                        
                        if emp_id == "PE0051":
                            frappe.log_error(f"checking_send mail for{emp_id}", f"row {row.penalization_type} {row.get('value')} {frappe.db.get_value('Employee', emp_id, row.get('employee_field_name'))}")
                        if row.penalization_type == "For Mispunch" and row.get("value") == frappe.db.get_value("Employee", emp_id, row.get("employee_field_name")):
                            frappe.log_error(f"checking_send mail for{emp_id}", "Mispunch criteria matched")
                            return 1
                    frappe.log_error(f"checking_send mail{emp_id}", "Mispunch criteria not matched")
                    return 0                                        
                else:
                    return 0
            elif is_later_entry:
                attendance_date = getdate(attendance_date)
                first_day = attendance_date.replace(day=1)
                last_day = attendance_date.replace(day=calendar.monthrange(attendance_date.year, attendance_date.month)[1])
                
                late_count = len(frappe.db.get_all("Attendance", {"employee": emp_id, "late_entry": 1, "creation": ["between", [first_day, last_day]] , "docstatus": 1}))
                
                frappe.log_error(f"send", "checking_send  mail inside late entry ")
                
                if hr_settings_doc.custom_late_coming_allowed_per_month_for_prompt >= late_count:
                    return 0
                else:
                    frappe.log_error("check_mail send", "checking_send  mail inside late entry ")
                    if hr_settings_doc.custom_enable_late_coming_penalty:
                        for row in hr_settings_doc.custom_penalization_criteria_table_for_prompt:
                            if row.penalization_type == "For Late Arrival" and row.get("value") == frappe.db.get_value("Employee", emp_id, row.get("employee_field_name")):
                                return 1
                        return 0                                        
                    else:
                        return 0
    except Exception as e:
        frappe.log_error(f"is_send_mail_check{emp_id}", f"For emp {emp_id} \n{frappe.get_traceback()}")
        



# @frappe.whitelist()
# def assign_checkin_role():
#     """Method to assign create checkin role to the employee if that employee has attendance request and the current date falls within the from and to date of that attendance request"""

#     try:

#         today_date = getdate(today())
#         checkin_role = "Create Checkin"
#         attendance_request_list = frappe.db.get_all(
#             "Attendance Request",
#             {
#                 "docstatus": 1,
#                 "custom_status": "Approved",
#                 "from_date": ["<=", today_date],
#                 "to_date": [">=", today_date],
#             },
#             ["name", "employee"],
#         )

#         frappe.log_error(f"assign_checkin_role_on{today_date}", f"{attendance_request_list}")

#         valid_users = set()

#         if attendance_request_list:
#             for attendance_request_data in attendance_request_list:
#                 emp_user_id = frappe.db.get_value(
#                     "Employee", attendance_request_data.get("employee"), "user_id"
#                 )
#                 valid_users.add(emp_user_id)
#                 if not user_has_role(emp_user_id, checkin_role):
#                     frappe.log_error(f"assign_checkin_role_to{emp_user_id}", "assigning user create checkin role")
#                     user_doc = frappe.get_doc("User", emp_user_id)
#                     user_doc.append("roles", {"role": checkin_role})
#                     user_doc.save(ignore_permissions=True)

#             frappe.db.commit()
#         # print(f"\n\n valid users {valid_users} \n\n")
#         # * REMOVING CHECKIN ROLE IF THE USER IS NOT QUALIFIED
#         all_employee_list = frappe.db.get_all(
#             "Employee",
#             {"status": "Active", "user_id": ["is", "set"]},
#             ["name", "user_id"],
#         )

#         if all_employee_list:
#             print(f"\n\n all employee list {all_employee_list} \n\n")
#             for employee_id in all_employee_list:

#                 if (
#                     employee_id.get("user_id")
#                     and employee_id.get("user_id") not in valid_users
#                     and user_has_role(employee_id.get("user_id"), checkin_role)
#                 ):
#                     # frappe.remove_role(employee_id.get("user_id", checkin_role))
#                     user_doc = frappe.get_doc("User", employee_id.get("user_id"))

#                     for role in user_doc.get("roles"):
#                         if role.role == checkin_role:
#                             print(
#                                 f"\n\n removing checkin role {employee_id.get('user_id')} \n\n"
#                             )
#                             user_doc.remove(role)

#                             break

#                     user_doc.save(ignore_permissions=True)
#             frappe.db.commit()
#     except Exception as e:
#         frappe.log_error(
#             "Error in assign_checkin_role scheduler method", frappe.get_traceback()
#         )
# ! DAILY SCHEDULER TO HANDLE ATTENDANCE REQUEST RITUALS
@frappe.whitelist()
def daily_attendance_request_rituals():
    
    try:
        
        all_employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=["name", "custom_attendance_capture_scheme", "custom_default_attendance_capture_scheme"],
        )

        # ? ATTENDANCE CAPTURE SCHEME MAP BASED ON WORK MODE
        attendance_capture_scheme_map = {
            "Work From Home": "Mobile-Web Checkin-Checkout",
            "On Duty": "Mobile-Web Checkin-Checkout",
        }

        # ? EMPLOYEE -> current scheme
        employee_map = {
            emp.name: {
                "current": emp.custom_attendance_capture_scheme,
                "default": emp.custom_default_attendance_capture_scheme,
            } for emp in all_employees
        }

        all_attendance_requests = frappe.get_all(
            "Attendance Request",
            filters={
                "custom_status": ["in", ["Approved", "Pending"]],
                "employee": ["in", list(employee_map.keys())],
            },
            fields=["name", "employee", "reason", "from_date", "to_date", "custom_old_attendance_capture_scheme"],
            order_by="from_date asc",
        )

        request_map = {}
        for req in all_attendance_requests:
            request_map.setdefault(req.employee, []).append(req)


        for employee, requests in request_map.items():

            current_scheme = employee_map[employee]["current"]
            default_scheme = employee_map[employee]["default"]
            
            active_request = None
            last_expired_request = None
            
            for req in requests:
                if getdate(req.from_date) <= getdate(today()) <= getdate(req.to_date):
                    active_request = req
                    break
                elif getdate(req.to_date) < getdate(today()):
                    last_expired_request = req

            # * FOR CUURENT ONE
            if active_request:
                if active_request.reason in attendance_capture_scheme_map:
                    
                    new_scheme = attendance_capture_scheme_map.get(active_request.reason)
                    
                    if new_scheme and current_scheme != new_scheme:
                        # Save old scheme only once
                        if not active_request.custom_old_attendance_capture_scheme:
                            frappe.db.set_value(
                                "Attendance Request",
                                active_request.name,
                                "custom_old_attendance_capture_scheme",
                                current_scheme,
                            )

                        emp_doc = frappe.get_doc("Employee", employee) or None
                        emp_doc.custom_attendance_capture_scheme = new_scheme
                        emp_doc.flags.ignore_mandatory = True
                        
                        try:
                            emp_doc.save(ignore_permissions=True)
                        except Exception as e:
                            frappe.log_error(f"attendance_rituals_error_for_{employee}", frappe.get_traceback())
                            continue
                        # frappe.db.set_value(
                        #     "Employee", employee, "custom_attendance_capture_scheme", new_scheme
                        # )
                        employee_map[employee] = new_scheme
                            
            # * FOR THE EXPIRED
            # elif last_expired_request and last_expired_request.custom_old_attendance_capture_scheme:
            elif last_expired_request:
            
                # if current_scheme != last_expired_request.custom_old_attendance_capture_scheme:
                if current_scheme != default_scheme and default_scheme:
                    emp_doc = frappe.get_doc("Employee", employee)
                    # emp_doc.custom_attendance_capture_scheme = last_expired_request.custom_old_attendance_capture_scheme
                    emp_doc.custom_attendance_capture_scheme = default_scheme
                    emp_doc.flags.ignore_mandatory = True
                    
                    try:
                        emp_doc.save(ignore_permissions=True)
                    except Exception as e:
                        frappe.log_error(f"attendance_rituals_error_for_{employee}", frappe.get_traceback())
                        continue
                    # frappe.db.set_value(
                    #     "Employee", employee, "custom_attendance_capture_scheme", last_expired_request.custom_old_attendance_capture_scheme
                    # )
                    # employee_map[employee] = last_expired_request.custom_old_attendance_capture_scheme
                    employee_map[employee]["current"] = default_scheme
                    
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("daily_attendance_request_rituals_error", frappe.get_traceback())
    
# *OLD CODE
    # all_employees = frappe.get_all(
    #     "Employee",
    #     filters={"status": "Active"},
    #     fields=["name", "custom_attendance_capture_scheme"],
    # )
    
    
    
        
    # # ? ATTENDANCE CAPTURE SCHEME MAP BASED ON WORK MODE
    # attendance_capture_scheme_map = {
    #     "Work From Home": "Mobile-Web Checkin-Checkout",
    #     "On Duty": "Mobile-Web Checkin-Checkout",
    # }

    # # ? CREATE EMPLOYEE HASHMAP FOR QUICK ACCESS (NAME AS KEY AND SCHEME AS VALUE)
    # employee_map = {
    #     emp.name: emp.custom_attendance_capture_scheme for emp in all_employees
    # }

    # all_attendance_requests = frappe.get_all(
    #     "Attendance Request",
    #     filters={
    #         "custom_status": ["in", ["Approved", "Pending"]],
    #         "employee": ["in", list(employee_map.keys())],
    #         "from_date": ["<=", today()],
    #         "to_date": [">=", today()],
    #     },
    #     fields=["name", "employee", "reason"],
    # )

    # attendance_request_hashmap = {}
            
    # for request in all_attendance_requests:
    #     employee_name = request.employee
    #     if employee_name not in attendance_request_hashmap:
    #         attendance_request_hashmap[employee_name] = []
    #     attendance_request_hashmap[employee_name].append(request)            

    # for employee, scheme in employee_map.items():
    #     attendance_request = attendance_request_hashmap.get(employee)
    #     if attendance_request:
    #         reason = attendance_request[0].get("reason")
    #         scheme = attendance_capture_scheme_map.get(reason)
    #         if employee_map.get(employee) != scheme:
    #             # ? UPDATE EMPLOYEE SCHEME IF IT DOES NOT MATCH
    #             frappe.db.set_value(
    #                 "Employee", employee, "custom_attendance_capture_scheme", scheme
    #             )
    #             frappe.db.commit()

    

"""
# ! THIS WILL CREATE EMPLOYEE PENALTY EVEN IF EMPLOYEE PENALTY IS MARKED 0, IT WILL CHECK IF THE ATTENDANCE STATUS IS 'MISPUNCH'
# ? DAILY SCHEDULER TO PENALIZE EMPLOYEES FOR ATTENDANCE MISPUNCH,
# ? FETCHING ALL THE ATTENDANCES WITH STATUS AS MISPUNCH OF THE APPLICABLE DATE (TODAY'S DATE - BUFFER DAYS FROM HR SETTINGS)
"""
def penalize_employee_for_attendance_mispunch_prompt(args):
    import json

    try:
        emp = args.get("employee")
        print(f"\n\n[DEBUG] Starting mispunch penalization for employee: {emp.get('name')}\n")

        # ? FETCH BUFFER DAYS CONFIGURATION FROM HR SETTINGS
        buffer_days_for_mispunch_penalty = frappe.db.get_single_value(
            "HR Settings", "custom_buffer_days_for_penalty"
        )
        print(f"[DEBUG] Buffer days fetched: {buffer_days_for_mispunch_penalty}")

        if not buffer_days_for_mispunch_penalty:
            print("[DEBUG] No buffer days configured. Exiting.\n")
            return



        # ? DETERMINE APPLICABLE ATTENDANCE DATE
        attendace_date = add_days(today(), -int(buffer_days_for_mispunch_penalty) - 1)
        attendace_date = getdate(attendace_date)
        print(f"[DEBUG] Applicable attendance date for mispunch penalty: {attendace_date}")

        # ? FETCH ATTENDANCE RECORDS WITH STATUS 'MISPUNCH'
        filters = {
            "employee": emp.get("name"),
            "status": "Mispunch",
            "attendance_date": str(attendace_date),
            "docstatus": 1,
        }

        attendance_list = frappe.get_all(
            "Attendance", filters=filters, fields=["name", "attendance_date"]
        )
        print(f"[DEBUG] Attendance list fetched: {attendance_list}")
        print(f"[DEBUG] Found {len(attendance_list)} mispunch attendance(s): {[i.name for i in attendance_list]}")

        if not attendance_list:
            print("[DEBUG] No mispunch attendances found. Exiting.\n")
            return

        # ? CHECK PENALTY CRITERIA FOR EMPLOYEE
        if not check_employee_penalty_criteria(emp.get("name"), "For Attendance Mispunch"):
            print("[DEBUG] Employee does not meet penalty criteria. Skipping penalty.\n")
            return

        # ? CHECK FOR EXISTING PENALTY FOR SAME ATTENDANCE(S)
        existing_penalty = frappe.db.exists(
            "Employee Penalty",
            {
                "employee": emp.get("name"),
                "attendance": ["in", [i.name for i in attendance_list]],
                "for_mispunch": 1,
            },
        )
        print(f"[DEBUG] Existing penalty check: {'Found' if existing_penalty else 'Not found'}")

        if existing_penalty:
            print("[DEBUG] Penalty already exists for mispunch. Skipping creation.\n")
            return

        # ? FETCH LEAVE DEDUCTION PRIORITY CONFIGURATION FOR MISPUNCH
        leave_priority_raw = frappe.db.get_all(
            "Leave Penalty Configuration",
            filters={
                "parent": "HR Settings",
                "parenttype": "HR Settings",
                "parentfield": "custom_attendance_mispunch_leave_penalty_configuration",
            },
            fields=["penalty_deduction_type", "leave_type_for_penalty", "idx"],
            order_by="idx asc",
        )
        print(f"[DEBUG] Leave Priority Raw Config: {leave_priority_raw}")

        leave_priority = [rec["leave_type_for_penalty"] for rec in leave_priority_raw]
        print(f"[DEBUG] Leave Deduction Priority Order: {leave_priority}")

        # ? DETERMINE LEAVE DEDUCTIONS BASED ON CONFIGURED PRIORITY
        earned_leave = 0.0
        lwp_leave = 0.0
        leave_deductions = []

        for leave_type in leave_priority:
            balance = get_remaining_leaves(leave_type, emp.get("name"), emp.get("company"))
            print(f"[DEBUG] Leave Type: {leave_type} | Balance: {balance}")

            if balance > 0:
                deduction = min(balance, required_deduction - earned_leave)
                earned_leave += deduction

                leave_allocation_id = frappe.db.get_value(
                    "Leave Allocation",
                    {
                        "employee": emp.get("name"),
                        "leave_type": leave_type,
                        "docstatus": 1,
                    },
                    "name",
                )

                leave_deductions.append(
                    {
                        "leave_type": leave_type,
                        "deducted": deduction,
                        "allocation_id": leave_allocation_id,
                    }
                )

                print(f"[DEBUG] Deducted {deduction} from {leave_type} | Allocation ID: {leave_allocation_id}")

            if earned_leave >= required_deduction:
                break

        if earned_leave < required_deduction:
            lwp_leave = required_deduction - earned_leave
            leave_deductions.append(
                {
                    "leave_type": "Leave Without Pay",
                    "deducted": lwp_leave,
                    "allocation_id": None,
                }
            )
            print(f"[DEBUG] Remaining Leave Shortfall {lwp_leave}, Deducted as LWP")

        print(f"[DEBUG] Final Leave Deductions: {leave_deductions}")

        # ? CREATE EMPLOYEE PENALTY
        print("[DEBUG] Creating employee penalty for mispunch...")
        create_employee_penalty(
            employee=emp.get("name"),
            penalty_date=attendace_date,
            deduct_leave=required_deduction,
            attendance_id=[i.name for i in attendance_list],
            leave_deductions=leave_deductions,
            leave_balance_before_application=earned_leave,
            is_lwp_for_mispunch=1 if lwp_leave > 0 else 0,
            for_mispunch=1,
        )
        print("[DEBUG] Penalty successfully created for mispunch.\n")

    except Exception as e:
        frappe.log_error(
            title="Error in penalize_employee_for_attendance_mispunch_prompt",
            message=frappe.get_traceback()
        )
        print(f"[ERROR] Exception occurred: {str(e)}\n")


import frappe
from datetime import date
from frappe.utils import getdate, today
from frappe.utils import (
    date_diff,
    today,
    add_to_date,
    getdate,
    get_datetime,
    add_months,
    get_first_day,
    get_last_day,
    add_days,
    formatdate,
)
from prompt_hr.py.utils import fetch_company_name
from prompt_hr.py.auto_mark_attendance import mark_attendance
from datetime import timedelta, datetime
from prompt_hr.prompt_hr.doctype.exit_approval_process.exit_approval_process import (
    raise_exit_checklist,
    raise_exit_interview,
)
from prompt_hr.py.utils import get_indifoss_company_name


def auto_attendance():
    mark_attendance(is_scheduler=1)


@frappe.whitelist()
def create_probation_feedback_form():
    """Scheduler method to create probation feedback form based on the days after when employee joined mentioned in the HR Settings.
    - And Also notify the employee's reporting manager if the remarks are not added to the form.
    """

    try:
        # probation_feedback_for_prompt()
        probation_feedback_for_indifoss()

    except Exception as e:
        frappe.log_error(
            "Error while creating probation feedback form", frappe.get_traceback()
        )


# # *CREATING PROBATION FEEDBACK FOR PROMPT EMPLOYEES
# def probation_feedback_for_prompt():
#     """Method to create probation feedback form for Prompt employees"""
#     print("jsfdjsfdndksfdnsfdnknsfd\n\n\n\n")
#     first_feedback_days = frappe.db.get_single_value(
#         "HR Settings", "custom_first_feedback_after"
#     )
#     second_feedback_days = frappe.db.get_single_value(
#         "HR Settings", "custom_second_feedback_after"
#     )
#     company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")

#     if company_abbr:
#         if first_feedback_days or second_feedback_days:
#             company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")

#             if company_id:
#                 # employees_list = frappe.db.get_all("Employee", {"status": "Active", "company": "Prompt Equipments PVT LTD", "custom_probation_status": "Pending"}, "name")
#                 employees_list = frappe.db.get_all(
#                     "Employee",
#                     {
#                         "status": "Active",
#                         "company": company_id,
#                         "custom_probation_status": "Pending",
#                     },
#                     "name",
#                 )
#                 print(f"\n\n\n\n\n\n\n\n\n\n {employees_list} \n\n\n\n")
#                 for employee in employees_list:
#                     if employee.get("name"):
#                         emp_joining_date = frappe.db.get_value(
#                             "Employee", employee.get("name"), "date_of_joining"
#                         )

#                         first_feedback_form_id = (
#                             frappe.db.get_value(
#                                 "Employee",
#                                 employee.get("name"),
#                                 "custom_first_probation_feedback",
#                             )
#                             or None
#                         )
#                         second_feedback_form_id = (
#                             frappe.db.get_value(
#                                 "Employee",
#                                 employee.get("name"),
#                                 "custom_second_probation_feedback",
#                             )
#                             or None
#                         )

#                         create_only_one = (
#                             True
#                             if not first_feedback_form_id
#                             and not second_feedback_form_id
#                             else False
#                         )

#                         if emp_joining_date:
#                             date_difference = date_diff(today(), emp_joining_date)

#                             if first_feedback_days <= date_difference:
#                                 if not first_feedback_form_id:
#                                     employee_doc = frappe.get_doc(
#                                         "Employee", employee.get("name")
#                                     )
#                                     first_probation_form = frappe.get_doc(
#                                         {
#                                             "doctype": "Probation Feedback Form",
#                                             "employee": employee.get("name"),
#                                             "employee_name": employee_doc.get(
#                                                 "employee_name"
#                                             ),
#                                             "department": employee_doc.get(
#                                                 "department"
#                                             ),
#                                             "designation": employee_doc.get(
#                                                 "designation"
#                                             ),
#                                             "company": employee_doc.get("company"),
#                                             "product_line": employee_doc.get(
#                                                 "custom_product_line"
#                                             ),
#                                             "business_unit": employee_doc.get(
#                                                 "custom_business_unit"
#                                             ),
#                                             "reporting_manager": employee_doc.get(
#                                                 "reports_to"
#                                             ),
#                                             "probation_feedback_for": "30 Days",
#                                             "evaluation_date": today(),
#                                         }
#                                     )

#                                     question_list = frappe.db.get_all(
#                                         "Probation Question",
#                                         {
#                                             "company": company_id,
#                                             "probation_feedback_for": "30 Days",
#                                         },
#                                         "name",
#                                     )

#                                     if question_list:

#                                         for question in question_list:
#                                             first_probation_form.append(
#                                                 "probation_feedback_prompt",
#                                                 {
#                                                     "question": question.get("name"),
#                                                     "frequency": "30 Days",
#                                                 },
#                                             )

#                                     first_probation_form.insert(ignore_permissions=True)
#                                     employee_doc.custom_first_probation_feedback = (
#                                         first_probation_form.name
#                                     )
#                                     employee_doc.save(ignore_permissions=True)
#                                     frappe.db.commit()
#                                 else:
#                                     remarks_added = frappe.db.exists(
#                                         "Probation Feedback Prompt",
#                                         {
#                                             "parenttype": "Probation Feedback Form",
#                                             "parent": first_feedback_form_id,
#                                             "rating": ["not in", ["0", ""]],
#                                         },
#                                         "name",
#                                     )

#                                     if not remarks_added:
#                                         reporting_manager_emp_id = (
#                                             frappe.db.get_value(
#                                                 "Probation Feedback Form",
#                                                 first_feedback_form_id,
#                                                 "reporting_manager",
#                                             )
#                                             or None
#                                         )

#                                         if not reporting_manager_emp_id:
#                                             reporting_manager_emp_id = (
#                                                 frappe.db.get_value(
#                                                     "Employee",
#                                                     employee.get("name"),
#                                                     "reports_to",
#                                                 )
#                                                 or None
#                                             )

#                                         if reporting_manager_emp_id:

#                                             reporting_manager_user_id = (
#                                                 frappe.db.get_value(
#                                                     "Employee",
#                                                     reporting_manager_emp_id,
#                                                     "user_id",
#                                                 )
#                                                 or None
#                                             )

#                                             if reporting_manager_user_id:
#                                                 reporting_manager_email = (
#                                                     frappe.db.get_value(
#                                                         "User",
#                                                         reporting_manager_user_id,
#                                                         "email",
#                                                     )
#                                                 )
#                                                 if reporting_manager_email:
#                                                     send_reminder_mail_to_reporting_manager(
#                                                         reporting_manager_email,
#                                                         reporting_manager_user_id,
#                                                         first_feedback_form_id,
#                                                         employee.get("employee_name"),
#                                                     )

#                             if second_feedback_days <= date_difference:
#                                 if not second_feedback_form_id and not create_only_one:

#                                     employee_doc = frappe.get_doc(
#                                         "Employee", employee.get("name")
#                                     )
#                                     second_probation_form = frappe.get_doc(
#                                         {
#                                             "doctype": "Probation Feedback Form",
#                                             "employee": employee.get("name"),
#                                             "employee_name": employee_doc.get(
#                                                 "employee_name"
#                                             ),
#                                             "department": employee_doc.get(
#                                                 "department"
#                                             ),
#                                             "designation": employee_doc.get(
#                                                 "designation"
#                                             ),
#                                             "company": employee_doc.get("company"),
#                                             "product_line": employee_doc.get(
#                                                 "custom_product_line"
#                                             ),
#                                             "business_unit": employee_doc.get(
#                                                 "custom_business_unit"
#                                             ),
#                                             "reporting_manager": employee_doc.get(
#                                                 "reports_to"
#                                             ),
#                                             "probation_feedback_for": "60 Days",
#                                             "evaluation_date": today(),
#                                         }
#                                     )

#                                     question_list = frappe.db.get_all(
#                                         "Probation Question",
#                                         {
#                                             "company": company_id,
#                                             "probation_feedback_for": "60 Days",
#                                         },
#                                         "name",
#                                     )

#                                     if question_list:
#                                         for question in question_list:
#                                             second_probation_form.append(
#                                                 "probation_feedback_prompt",
#                                                 {
#                                                     "question": question.get("name"),
#                                                     "frequency": "60 Days",
#                                                 },
#                                             )

#                                     second_probation_form.insert(
#                                         ignore_permissions=True
#                                     )
#                                     employee_doc.custom_second_probation_feedback = (
#                                         second_probation_form.name
#                                     )
#                                     employee_doc.save(ignore_permissions=True)

#                                     frappe.db.commit()
#                                 elif second_feedback_form_id:

#                                     remarks_added = frappe.db.exists(
#                                         "Probation Feedback Prompt",
#                                         {
#                                             "parenttype": "Probation Feedback Form",
#                                             "parent": second_feedback_form_id,
#                                             "rating": ["not in", ["0", ""]],
#                                         },
#                                     )
#                                     if not remarks_added:
#                                         reporting_manager_emp_id = (
#                                             frappe.db.get_value(
#                                                 "Probation Feedback Form",
#                                                 second_feedback_form_id,
#                                                 "reporting_manager",
#                                             )
#                                             or None
#                                         )
#                                         if not reporting_manager_emp_id:
#                                             reporting_manager_emp_id = (
#                                                 frappe.db.get_value(
#                                                     "Employee",
#                                                     employee.get("name"),
#                                                     "reports_to",
#                                                 )
#                                                 or None
#                                             )

#                                         if reporting_manager_emp_id:
#                                             reporting_manager_user_id = (
#                                                 frappe.db.get_value(
#                                                     "Employee",
#                                                     reporting_manager_emp_id,
#                                                     "user_id",
#                                                 )
#                                                 or None
#                                             )
#                                             if reporting_manager_user_id:
#                                                 reporting_manager_email = (
#                                                     frappe.db.get_value(
#                                                         "User",
#                                                         reporting_manager_user_id,
#                                                         "email",
#                                                     )
#                                                 )
#                                                 if reporting_manager_email:
#                                                     send_reminder_mail_to_reporting_manager(
#                                                         reporting_manager_email,
#                                                         reporting_manager_user_id,
#                                                         second_feedback_form_id,
#                                                         employee.get("employee_name"),
#                                                     )
#             else:
#                 frappe.log_error(
#                     "Issue while checking for probation feedback form for Prompt",
#                     f"No Company found for abbreviation {company_abbr}",
#                 )
#     else:
#         frappe.log_error(
#             "Issue while check for probation feedback form for Prompt",
#             "Please set abbreviation in HR Settings FOR Prompt",
#         )


# *CREATING PROBATION FEEDBACK FOR INDIFOSS EMPLOYEES
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
                    "custom_probation_status": "In Probation",
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
# def create_confirmation_evaluation_form_for_prompt():
#     try:

#         company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
#         create_cff_before_days = (
#             frappe.db.get_single_value(
#                 "HR Settings", "custom_release_confirmation_form"
#             )
#             or 15
#         )

#         if company_abbr:
#             company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
#             if company_id:
#                 employees_list = frappe.db.get_all(
#                     "Employee",
#                     {
#                         "status": "Active",
#                         "company": company_id,
#                         "custom_probation_status": "In Probation",
#                     },
#                     "name",
#                 )

#                 if employees_list:
#                     for employee_id in employees_list:
#                         probation_days = frappe.db.get_value(
#                             "Employee",
#                             employee_id.get("name"),
#                             "custom_probation_period",
#                         )

#                         if probation_days:

#                             joining_date = frappe.db.get_value(
#                                 "Employee", employee_id.get("name"), "date_of_joining"
#                             )

#                             probation_end_date = getdate(
#                                 add_to_date(joining_date, days=probation_days)
#                             )

#                             today_date = getdate()
#                             days_remaining = (probation_end_date - today_date).days

#                             if 0 <= days_remaining <= create_cff_before_days:
#                                 confirmation_eval_form = frappe.db.get_value(
#                                     "Employee",
#                                     employee_id.get("name"),
#                                     "custom_confirmation_evaluation_form",
#                                 )
#                                 try:
#                                     if not confirmation_eval_form:
#                                         employee_doc = frappe.get_doc(
#                                             "Employee", employee_id.get("name")
#                                         )
#                                         confirmation_eval_doc = frappe.get_doc(
#                                             {
#                                                 "doctype": "Confirmation Evaluation Form",
#                                                 "employee": employee_id.get("name"),
#                                                 "evaluation_date": today(),
#                                                 "probation_status": "Pending",
#                                             }
#                                         )

#                                         category_list = [
#                                             "Functional/ Technical Skills",
#                                             "Behavioural Skills",
#                                         ]

#                                         parameters_list = frappe.db.get_all(
#                                             "Confirmation Evaluation Parameter",
#                                             {"category": ["in", category_list]},
#                                             ["name", "category"],
#                                         )

#                                         for parameter in parameters_list:

#                                             confirmation_eval_doc.append(
#                                                 "table_txep",
#                                                 {
#                                                     "category": parameter.get(
#                                                         "category"
#                                                     ),
#                                                     "parameters": parameter.get("name"),
#                                                 },
#                                             )

#                                         confirmation_eval_doc.insert(
#                                             ignore_permissions=True
#                                         )
#                                         employee_doc.custom_confirmation_evaluation_form = (
#                                             confirmation_eval_doc.name
#                                         )
#                                         employee_doc.save(ignore_permissions=True)
#                                         frappe.db.commit()

#                                         # frappe.db.set_value("Employee", employee_id.get("name"), "custom_confirmation_evaluation_form", confirmation_eval_doc.name)
#                                     elif confirmation_eval_form:

#                                         confirmation_eval_form_doc = frappe.get_doc(
#                                             "Confirmation Evaluation Form",
#                                             confirmation_eval_form,
#                                         )

#                                         rh_rating_added = (
#                                             confirmation_eval_form_doc.rh_rating_added
#                                         )
#                                         dh_rating_added = (
#                                             confirmation_eval_form_doc.dh_rating_added
#                                         )
#                                         context = {
#                                             "doc": confirmation_eval_form_doc,
#                                             "doctype": "Confirmation Evaluation Form",
#                                             "docname": confirmation_eval_form_doc.name,
#                                         }
#                                         notification_template = frappe.get_doc(
#                                             "Notification",
#                                             "Confirmation Evaluation Form Remarks Reminder",
#                                         )
#                                         subject = frappe.render_template(
#                                             notification_template.subject, context
#                                         )
#                                         message = frappe.render_template(
#                                             notification_template.message, context
#                                         )

#                                         if not rh_rating_added:
#                                             reporting_head = (
#                                                 confirmation_eval_form_doc.reporting_manager
#                                             )
#                                             reporting_head_user_id = (
#                                                 frappe.db.get_value(
#                                                     "Employee",
#                                                     reporting_head,
#                                                     "user_id",
#                                                 )
#                                                 if reporting_head
#                                                 else None
#                                             )
#                                             reporting_head_email = (
#                                                 frappe.db.get_value(
#                                                     "User",
#                                                     reporting_head_user_id,
#                                                     "email",
#                                                 )
#                                                 if reporting_head_user_id
#                                                 else None
#                                             )

#                                             if reporting_head_email:

#                                                 try:
#                                                     frappe.sendmail(
#                                                         recipients=[
#                                                             reporting_head_email
#                                                         ],
#                                                         subject=subject,
#                                                         message=message,
#                                                         reference_doctype="Confirmation Evaluation Form",
#                                                         reference_name=confirmation_eval_form_doc.name,
#                                                         now=True,
#                                                     )
#                                                 except Exception as e:
#                                                     frappe.log_error(
#                                                         "Error while sending confirmation evaluation form reminder mail",
#                                                         frappe.get_traceback(),
#                                                     )

#                                         elif rh_rating_added and not dh_rating_added:

#                                             head_of_department = (
#                                                 confirmation_eval_form_doc.hod
#                                             )
#                                             head_of_department_employee = (
#                                                 frappe.db.get_value(
#                                                     "Employee",
#                                                     head_of_department,
#                                                     "user_id",
#                                                 )
#                                                 if head_of_department
#                                                 else None
#                                             )
#                                             head_of_department_email = (
#                                                 frappe.db.get_value(
#                                                     "User",
#                                                     head_of_department_employee,
#                                                     "email",
#                                                 )
#                                                 if head_of_department_employee
#                                                 else None
#                                             )

#                                             if head_of_department_email:
#                                                 frappe.sendmail(
#                                                     recipients=[
#                                                         head_of_department_email
#                                                     ],
#                                                     subject=subject,
#                                                     message=message,
#                                                     reference_doctype="Confirmation Evaluation Form",
#                                                     reference_name=confirmation_eval_form_doc.name,
#                                                     now=True,
#                                                 )
#                                 except Exception as e:
#                                     frappe.log_error(
#                                         "Error while creating confirmation evaluation form",
#                                         frappe.get_traceback(),
#                                     )

#             else:
#                 frappe.log_error(
#                     "Issue while creating confirmation form for prompt",
#                     f"Company Not found for abbreviation {company_abbr}",
#                 )
#         else:
#             frappe.log_error(
#                 "Issue while creating confirmation form for prompt",
#                 "Company abbreviation Not Found Please Set Company abbreviation for Prompt in HR Settings",
#             )
#     except Exception as e:
#         frappe.log_error(
#             "Error while creating confirmation evaluation form", frappe.get_traceback()
#         )


def inform_employee_for_confirmation_process():
    """Method to inform employee about confirmation process  before the days set user in HR Settings probation period is over
    FOR INDIFOSS
    """
    try:

        company_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
        company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
        employee_list = frappe.db.get_all(
            "Employee",
            {
                "status": "Active",
                "company": company_id,
                "custom_probation_status": "In Probation",
            },
            "name",
        )

        inform_days_before_confirmation = frappe.db.get_single_value(
            "HR Settings", "custom_inform_employees_probation_end_for_indifoss"
        )
        if inform_days_before_confirmation:
            final_inform_days = -abs(inform_days_before_confirmation)
        else:
            final_inform_days = -5
        if employee_list:

            for employee in employee_list:
                employee_doc = frappe.get_doc("Employee", employee.get("name"))
                probation_period = (
                    employee_doc.custom_probation_period
                    or 0 + employee_doc.custom_extended_period
                    or 0
                )

                if probation_period:
                    joining_date = employee_doc.date_of_joining
                    if joining_date:

                        probation_end_date = add_to_date(
                            joining_date, days=probation_period
                        )
                        if probation_end_date:
                            five_days_before_date = add_to_date(
                                probation_end_date,
                                days=final_inform_days,
                                as_string=True,
                            )
                            if (
                                five_days_before_date
                                and five_days_before_date == today()
                            ):

                                employee_email = (
                                    frappe.db.get_value(
                                        "User", employee_doc.user_id, "email"
                                    )
                                    if employee_doc.user_id
                                    else None
                                )

                                if employee_email:
                                    notification_template = frappe.get_doc(
                                        "Notification",
                                        "Inform Employee about Confirmation Process",
                                    )
                                    if notification_template:
                                        subject = frappe.render_template(
                                            notification_template.subject,
                                            {"doc": employee_doc},
                                        )
                                        message = frappe.render_template(
                                            notification_template.message,
                                            {"doc": employee_doc},
                                        )

                                        frappe.sendmail(
                                            recipients=[employee_email],
                                            subject=subject,
                                            message=message,
                                            now=True,
                                        )
                                    else:
                                        frappe.sendmail(
                                            recipients=[employee_email],
                                            subject="Confirmation Process Reminder",
                                            message=f"Dear {employee_doc.employee_name or 'Employee'}, your probation period is ending soon. Please check with your reporting manager for the confirmation process.",
                                            now=True,
                                        )
    except Exception as e:
        frappe.log_error(
            "Error while sending confirmation process reminder email",
            frappe.get_traceback(),
        )


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


@frappe.whitelist()
def assign_checkin_role():
    """Method to assign create checkin role to the employee if that employee has attendance request and the current date falls within the from and to date of that attendance request"""

    try:

        today_date = getdate(today())
        checkin_role = "Create Checkin"
        attendance_request_list = frappe.db.get_all(
            "Attendance Request",
            {
                "docstatus": 1,
                "custom_status": "Approved",
                "from_date": ["<=", today_date],
                "to_date": [">=", today_date],
            },
            ["name", "employee"],
        )

        print(f"\n\n attendance request list {attendance_request_list} \n\n")

        valid_users = set()

        if attendance_request_list:
            for attendance_request_data in attendance_request_list:
                emp_user_id = frappe.db.get_value(
                    "Employee", attendance_request_data.get("employee"), "user_id"
                )
                valid_users.add(emp_user_id)
                if not user_has_role(emp_user_id, checkin_role):
                    print(f"\n\n applying checkin role {emp_user_id} \n\n")
                    user_doc = frappe.get_doc("User", emp_user_id)
                    user_doc.append("roles", {"role": checkin_role})
                    user_doc.save(ignore_permissions=True)

            frappe.db.commit()
        print(f"\n\n valid users {valid_users} \n\n")
        # * REMOVING CHECKIN ROLE IF THE USER IS NOT QUALIFIED
        all_employee_list = frappe.db.get_all(
            "Employee",
            {"status": "Active", "user_id": ["is", "set"]},
            ["name", "user_id"],
        )

        if all_employee_list:
            print(f"\n\n all employee list {all_employee_list} \n\n")
            for employee_id in all_employee_list:

                if (
                    employee_id.get("user_id")
                    and employee_id.get("user_id") not in valid_users
                    and user_has_role(employee_id.get("user_id"), checkin_role)
                ):
                    # frappe.remove_role(employee_id.get("user_id", checkin_role))
                    user_doc = frappe.get_doc("User", employee_id.get("user_id"))

                    for role in user_doc.get("roles"):
                        if role.role == checkin_role:
                            print(
                                f"\n\n removing checkin role {employee_id.get('user_id')} \n\n"
                            )
                            user_doc.remove(role)

                            break

                    user_doc.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            "Error in assign_checkin_role scheduler method", frappe.get_traceback()
        )


def user_has_role(user, role):
    """Method to check if the user has the given role or not"""
    return frappe.db.exists("Has Role", {"parent": user, "role": role})


# ! METHOD: APPLY LATE ENTRY PENALTY BASED ON CUSTOM MONTHLY WINDOW (16TH-LAST MONTH to 15TH-THIS MONTH)
@frappe.whitelist()
def penalize_employee_for_late_entry_for_indifoss(run_now=0):
    """
    APPLIES MONTHLY LATE ENTRY PENALTIES TO EMPLOYEES OF INDIFOSS BASED ON A CUSTOM EVALUATION WINDOW.

    @PARAMETERS
    - run_now: Integer (0 or 1)
        • 0 (default): Process only if today is cutoff_day + 1 (automatic scheduled mode)
        • 1: Process the previous cycle immediately, regardless of today's date

    @EVALUATION WINDOW
    - CUSTOM CUT-OFF DAY IS FETCHED FROM HR SETTINGS (e.g., 15)
    - EVALUATION RANGE: START = CUTOFF DAY OF PREVIOUS MONTH + 1
                        END   = CUTOFF DAY OF CURRENT MONTH
      e.g., if cutoff is 15th July, range is 16th June to 15th July

    @PENALTY RULES
    - ALLOWED LATE ENTRIES: custom_late_coming_allowed_per_month_for_indifoss
    - PENALTY FREQUENCY: custom_number_of_late_entries_per_leave_penalty_for_indifoss
    - EXAMPLE: If allowed=1 and frequency=3:
        • First 3 late entries = ALLOWED (no penalty)
        • 6th late entry = 1st PENALTY
        • 9th late entry = 2nd PENALTY
        • 12th late entry = 3rd PENALTY, etc.

    @SCHEDULING
    - TO BE TRIGGERED ONCE A MONTH (preferably on cutoff_day + 1)
    """

    from frappe.utils import getdate, add_months, add_days

    # Convert run_now to integer if passed as string
    run_now = int(run_now) if run_now else 0

    print("\n" + "=" * 80)
    print("🚀 STARTING LATE ENTRY PENALTY PROCESS")
    print(
        f"⚙️  MODE: {'MANUAL RUN (run_now=1)' if run_now else 'SCHEDULED RUN (run_now=0)'}"
    )
    print("=" * 80)

    try:
        # ─────────────────────────────────────────────
        # STEP 1: FETCH HR SETTINGS
        # ─────────────────────────────────────────────
        print("\n📋 STEP 1: FETCHING HR SETTINGS")
        print("-" * 40)

        # Fetch the control parameters from HR Settings
        allowed_late_entries_base = int(
            frappe.db.get_single_value(
                "HR Settings", "custom_late_coming_allowed_per_month_for_indifoss"
            )
            or 0
        )
        late_entries_per_penalty = int(
            frappe.db.get_single_value(
                "HR Settings",
                "custom_number_of_late_entries_per_leave_penalty_for_indifoss",
            )
            or 1
        )

        print(f"✅ Base allowed late entries: {allowed_late_entries_base}")
        print(f"✅ Late entries per penalty: {late_entries_per_penalty}")

        # Calculate total allowed entries before first penalty
        total_allowed_before_first_penalty = (
            allowed_late_entries_base * late_entries_per_penalty
        )
        print(
            f"✅ Total allowed entries before first penalty: {total_allowed_before_first_penalty}"
        )

        # Default deduction amount - actual configuration will be handled by create_employee_penalty method
        late_entry_deduct_leave = (
            1.0  # This will be overridden by the penalty configuration
        )
        print(
            f"✅ Default leave deduction: {late_entry_deduct_leave} (actual amount determined by penalty configuration)"
        )

        print(f"\n📐 PENALTY LOGIC EXPLANATION:")
        print(
            f"   - If allowed_base={allowed_late_entries_base} and frequency={late_entries_per_penalty}:"
        )
        print(
            f"   - First {total_allowed_before_first_penalty} late entries: NO PENALTY"
        )
        print(
            f"   - Entry #{total_allowed_before_first_penalty + late_entries_per_penalty}: 1st PENALTY"
        )
        print(
            f"   - Entry #{total_allowed_before_first_penalty + 2*late_entries_per_penalty}: 2nd PENALTY"
        )
        print(f"   - And so on...")

        # ─────────────────────────────────────────────
        # STEP 2: CALCULATE EVALUATION WINDOW
        # ─────────────────────────────────────────────
        print("\n📅 STEP 2: CALCULATING EVALUATION WINDOW")
        print("-" * 40)

        cutoff_day_str = frappe.db.get_single_value(
            "HR Settings", "custom_month_date_for_attendance_penalty_indifoss"
        )
        print(f"📌 Cutoff day from settings: {cutoff_day_str}")

        if not cutoff_day_str:
            print("❌ ERROR: Missing cutoff date in HR Settings")
            frappe.log_error(
                "Missing cutoff date",
                "HR Settings: custom_month_date_for_attendance_penalty_indifoss",
            )
            return

        cutoff_day = int(cutoff_day_str)
        today = getdate()
        print(f"📅 Today's date: {today}")
        print(f"📅 Cutoff day: {cutoff_day}")

        # ── CHECK IF PROCESSING SHOULD OCCUR (when run_now=0) ──────────────────
        if run_now == 0:
            # Calculate expected processing date (cutoff_day + 1)
            try:
                if today.day <= cutoff_day:
                    expected_processing_date = add_months(
                        today.replace(day=cutoff_day), -1
                    )
                    expected_processing_date = add_days(expected_processing_date, 1)
                else:
                    expected_processing_date = add_days(
                        today.replace(day=cutoff_day), 1
                    )
            except ValueError:
                # Handle months where cutoff_day doesn't exist
                from frappe.utils import get_last_day

                if today.day <= cutoff_day:
                    expected_processing_date = add_months(get_last_day(today), -1)
                    expected_processing_date = add_days(expected_processing_date, 1)
                else:
                    expected_processing_date = add_days(get_last_day(today), 1)

            print(f"📅 Expected processing date: {expected_processing_date}")

            if today != expected_processing_date:
                print(f"\n⏸️  PROCESS HALTED")
                print(
                    f"❌ Today ({today}) is not the scheduled processing day ({expected_processing_date})"
                )
                print(
                    f"💡 TIP: To run immediately regardless of date, call with run_now=1"
                )
                print("=" * 80)
                return {
                    "status": "skipped",
                    "message": f"Not scheduled to run today. Expected: {expected_processing_date}",
                    "today": str(today),
                    "expected_date": str(expected_processing_date),
                }
            else:
                print(f"✅ Today matches expected processing date - proceeding...")
        else:
            print(f"⚡ MANUAL RUN MODE: Processing previous cycle immediately")

        # ── Determine the last fully completed cycle ───────────────────────────
        # Always process the PREVIOUS COMPLETED cycle
        # A cycle runs from (cutoff_day + 1) of one month to cutoff_day of next month
        # BUT if cutoff_day is last day of month, cycle is simply: 1st to last day of previous month
        from frappe.utils import get_last_day

        try:
            # Check if cutoff_day represents end of month
            current_month_last_day = get_last_day(today).day

            if cutoff_day >= current_month_last_day:
                # Cutoff is set to month-end (e.g., 31)
                # Cycle should be full calendar months
                # Example: Today = Nov 3, cutoff = 31 → Process Oct 1 to Oct 31

                # Get first day of previous month
                first_day_of_current_month = today.replace(day=1)
                first_day_of_prev_month = add_months(first_day_of_current_month, -1)
                last_day_of_prev_month = get_last_day(first_day_of_prev_month)

                from_date = first_day_of_prev_month
                to_date = last_day_of_prev_month

            else:
                # Cutoff is mid-month (e.g., 15)
                # Cycle runs from cutoff_day+1 of prev month to cutoff_day of this month

                # Step 1: Find the most recent cutoff date that has PASSED
                if today.day > cutoff_day:
                    # We've already passed this month's cutoff
                    # Example: Today = Nov 25, cutoff = 15 → Most recent passed = Nov 15
                    most_recent_cutoff = today.replace(day=cutoff_day)
                else:
                    # We haven't reached this month's cutoff yet
                    # Example: Today = Nov 3, cutoff = 15 → Most recent passed = Oct 15
                    most_recent_cutoff = add_months(today.replace(day=cutoff_day), -1)

                # Step 2: For PREVIOUS cycle, go back one more month
                last_cutoff = add_months(most_recent_cutoff, -1)
                prev_cutoff = add_months(last_cutoff, -1)

                from_date = add_days(prev_cutoff, 1)
                to_date = last_cutoff

        except ValueError:
            # Handles edge cases with invalid dates
            if cutoff_day >= 28:  # Likely month-end cutoff
                first_day_of_current_month = today.replace(day=1)
                first_day_of_prev_month = add_months(first_day_of_current_month, -1)
                last_day_of_prev_month = get_last_day(first_day_of_prev_month)

                from_date = first_day_of_prev_month
                to_date = last_day_of_prev_month
            else:
                # Fall back to standard logic
                if today.day > cutoff_day:
                    most_recent_cutoff = get_last_day(today)
                else:
                    most_recent_cutoff = add_months(get_last_day(today), -1)

                last_cutoff = add_months(most_recent_cutoff, -1)
                prev_cutoff = add_months(last_cutoff, -1)

                from_date = add_days(prev_cutoff, 1)
                to_date = last_cutoff

        if "prev_cutoff" in locals() and "last_cutoff" in locals():
            from_date = add_days(prev_cutoff, 1)
            to_date = last_cutoff

        print(f"🎯 EVALUATION WINDOW (PREVIOUS COMPLETED CYCLE):")
        print(f"   🔍 Debug Info:")
        print(f"      - Today: {today}")
        print(f"      - Cutoff Day: {cutoff_day}")
        print(f"      - Current Month Last Day: {get_last_day(today).day}")
        print(f"      - Is Month-End Cutoff: {cutoff_day >= get_last_day(today).day}")
        print(f"   📅 Period:")
        print(f"      From Date: {from_date.strftime('%d %B %Y')}")
        print(f"      To Date: {to_date.strftime('%d %B %Y')}")
        print(f"   📊 Total Days: {(to_date - from_date).days + 1}")

        # ─────────────────────────────────────────────
        # STEP 3: FETCH COMPANY & EMPLOYEES
        # ─────────────────────────────────────────────
        print("\n🏢 STEP 3: FETCHING COMPANY & EMPLOYEES")
        print("-" * 40)

        company_data = fetch_company_name(indifoss=1)
        print(f"🏢 Company data fetched: {company_data}")

        if company_data.get("error"):
            print(f"❌ ERROR: Invalid company fetched - {company_data}")
            frappe.log_error("Invalid company fetched", str(company_data))
            return

        company = company_data.get("company_id")
        print(f"✅ Company ID: {company}")

        employee_list = frappe.db.get_all(
            "Employee",
            {"status": "Active", "company": company},
            ["name", "relieving_date"],
        )
        print(f"👥 Total active employees found: {len(employee_list)}")

        skipped_due_to_reg = []
        penalties_created = 0

        # ─────────────────────────────────────────────
        # STEP 4: EVALUATE EACH EMPLOYEE
        # ─────────────────────────────────────────────
        print(f"\n👤 STEP 4: EVALUATING {len(employee_list)} EMPLOYEES")
        print("-" * 40)

        for emp_idx, emp in enumerate(employee_list, 1):
            emp_id = emp.name
            relieving_date = emp.relieving_date

            print(
                f"\n👤 [{emp_idx}/{len(employee_list)}] Processing Employee: {emp_id}"
            )
            print(f"   Relieving Date: {relieving_date}")

            # Check penalty criteria
            try:
                penalty_criteria_result = check_employee_penalty_criteria(
                    emp_id, "For Late Arrival"
                )
                print(f"   ✅ Penalty criteria check: {penalty_criteria_result}")

                if not penalty_criteria_result:
                    print(f"   ⏭️  SKIPPED: Employee doesn't meet penalty criteria")
                    continue
            except Exception as e:
                print(f"   ❌ ERROR checking penalty criteria: {str(e)}")
                continue

            # Fetch all late entries in range
            print(f"   🔍 Searching for late entries between {from_date} and {to_date}")
            try:
                late_attendance_list = frappe.db.get_all(
                    "Attendance",
                    {
                        "docstatus": 1,
                        "employee": emp_id,
                        "attendance_date": ["between", [from_date, to_date]],
                        "late_entry": 1,
                    },
                    ["name", "attendance_date"],
                    order_by="attendance_date asc",
                )
            except Exception as e:
                print(f"   ❌ ERROR fetching late entries: {str(e)}")
                continue

            total_late_entries = len(late_attendance_list)
            print(f"   📊 Total late entries found: {total_late_entries}")
            print(
                f"   📊 Entries allowed before first penalty: {total_allowed_before_first_penalty}"
            )

            if total_late_entries <= total_allowed_before_first_penalty:
                print(f"   ✅ Employee within allowed limit, no penalties needed")
                continue

            # Show penalty calculation breakdown
            penalty_eligible_entries = (
                total_late_entries - total_allowed_before_first_penalty
            )
            expected_penalties = penalty_eligible_entries // late_entries_per_penalty
            print(f"   📊 Entries beyond allowed limit: {penalty_eligible_entries}")
            print(f"   📊 Expected penalties: {expected_penalties}")

            # Show all late entries for this employee with penalty status
            print(f"   📋 Late entries breakdown:")
            for i, att in enumerate(late_attendance_list, 1):
                if i <= total_allowed_before_first_penalty:
                    status = "ALLOWED"
                elif (
                    i - total_allowed_before_first_penalty
                ) % late_entries_per_penalty == 0:
                    penalty_number = (
                        i - total_allowed_before_first_penalty
                    ) // late_entries_per_penalty
                    status = f"PENALTY #{penalty_number}"
                else:
                    status = "NO PENALTY"
                print(f"      [{i:2d}] {att.attendance_date} - {att.name} ({status})")

            # Process penalty-eligible entries
            print(f"   🎯 Processing penalty-eligible entries...")

            for idx, attendance in enumerate(late_attendance_list, start=1):
                # Skip entries within allowed limit
                if idx <= total_allowed_before_first_penalty:
                    continue

                # Calculate position beyond allowed limit
                position_beyond_allowed = idx - total_allowed_before_first_penalty

                # Check if this entry should trigger a penalty
                if position_beyond_allowed % late_entries_per_penalty != 0:
                    continue  # Not a penalty trigger point

                penalty_number = position_beyond_allowed // late_entries_per_penalty
                print(
                    f"\n      🔄 Processing penalty #{penalty_number} for entry {idx}: {attendance.name} ({attendance.attendance_date})"
                )

                att_id = attendance.name
                att_date = attendance.attendance_date

                # Check relieving date
                if relieving_date and getdate(relieving_date) < att_date:
                    print(
                        f"         ⏭️  SKIPPED: Employee relieved ({relieving_date}) before attendance date ({att_date})"
                    )
                    continue

                # Check for existing leave
                try:
                    leave_exists = frappe.db.exists(
                        "Leave Application",
                        {
                            "employee": emp_id,
                            "docstatus": 1,
                            "from_date": ["<=", att_date],
                            "to_date": [">=", att_date],
                        },
                    )
                    print(f"         📋 Leave exists check: {bool(leave_exists)}")
                except Exception as e:
                    print(f"         ❌ ERROR checking leave: {str(e)}")
                    leave_exists = False

                # Check for existing penalty
                try:
                    penalty_id = frappe.db.get_value(
                        "Employee Penalty", {"employee": emp_id, "attendance": att_id}
                    )

                    if penalty_id:
                        reason_exists = frappe.db.exists(
                            "Employee Leave Penalty Details",
                            {"parent": penalty_id, "reason": "Late Coming"},
                        )
                        penalty_exists = bool(reason_exists)
                        print(
                            f"         ⚠️ Penalty for 'Late Coming' exists: {penalty_exists}"
                        )
                    else:
                        penalty_exists = False
                        print(f"         ✅ No penalty found for this attendance")

                except Exception as e:
                    penalty_exists = False
                    print(f"         ❌ ERROR checking penalty: {str(e)}")

                # Check for attendance regularization
                try:
                    attendance_reg_exists = frappe.db.exists(
                        "Attendance Regularization",
                        {
                            "employee": emp_id,
                            "attendance": att_id,
                            "regularization_date": att_date,
                            "status": ["in", ["Approved", "Pending"]],
                        },
                    )
                    print(
                        f"         🔄 Attendance regularization exists: {bool(attendance_reg_exists)}"
                    )
                except Exception as e:
                    print(f"         ❌ ERROR checking regularization: {str(e)}")
                    attendance_reg_exists = False

                if attendance_reg_exists:
                    print(f"         ⏭️  SKIPPED: Attendance regularization exists")
                    skipped_due_to_reg.append(
                        {"employee": emp_id, "attendance_id": att_id}
                    )
                    continue

                if leave_exists or penalty_exists:
                    skip_reason = (
                        "Leave exists" if leave_exists else "Penalty already exists"
                    )
                    print(f"         ⏭️  SKIPPED: {skip_reason}")
                    continue

                print(
                    f"         🎯 CREATING PENALTY #{penalty_number} for {emp_id} on {att_date}"
                )
                print(f"         📝 Penalty details:")
                print(f"            - Employee: {emp_id}")
                print(f"            - Penalty Date: {att_date}")
                print(f"            - Attendance ID: {att_id}")
                print(f"            - Leave Deduction: {late_entry_deduct_leave}")

                try:
                    penalty_id = create_employee_penalty(
                        employee=emp_id,
                        penalty_date=att_date,
                        deduct_leave=late_entry_deduct_leave,
                        attendance_id=att_id,
                        leave_balance_before_application=0.0,  # Will be calculated inside the method
                        leave_period_data=None,
                        leave_allocation_id=None,  # Will be determined inside the method
                        for_late_coming=1,
                        for_insufficient_hours=0,
                        for_no_attendance=0,
                        for_mispunch=0,
                    )

                    penalties_created += 1
                    print(f"         ✅ PENALTY CREATED SUCCESSFULLY!")
                    print(f"         📄 Penalty ID: {penalty_id}")
                    print(
                        f"         📊 Total penalties created so far: {penalties_created}"
                    )

                except Exception as penalty_error:
                    print(f"         ❌ ERROR CREATING PENALTY: {str(penalty_error)}")
                    frappe.log_error(
                        f"Error creating penalty for {emp_id}", str(penalty_error)
                    )

        # ─────────────────────────────────────────────
        # STEP 5: NOTIFY HR FOR SKIPPED ENTRIES
        # ─────────────────────────────────────────────
        print(f"\n📧 STEP 5: PROCESSING NOTIFICATIONS")
        print("-" * 40)

        print(f"📊 Entries skipped due to regularization: {len(skipped_due_to_reg)}")

        if skipped_due_to_reg:
            print("📋 Skipped entries details:")
            for entry in skipped_due_to_reg:
                print(
                    f"   - Employee: {entry['employee']}, Attendance: {entry['attendance_id']}"
                )

            try:
                notify_hr_if_non_creation_of_penalty_because_of_attendance_regularization(
                    skipped_due_to_reg
                )
                print("✅ HR notification sent successfully")
            except Exception as notify_error:
                print(f"❌ Error sending HR notification: {notify_error}")

        # FINAL SUMMARY
        print(f"\n" + "=" * 80)
        print(f"🎉 PROCESS COMPLETED SUCCESSFULLY!")
        print(f"📊 FINAL SUMMARY:")
        print(
            f"   - Run Mode: {'MANUAL (run_now=1)' if run_now else 'SCHEDULED (run_now=0)'}"
        )
        print(f"   - Total employees processed: {len(employee_list)}")
        print(f"   - Total penalties created: {penalties_created}")
        print(f"   - Entries skipped due to regularization: {len(skipped_due_to_reg)}")
        print(f"   - Evaluation period: {from_date} to {to_date}")
        print(
            f"   - Penalty logic: {allowed_late_entries_base} base allowed × {late_entries_per_penalty} frequency = {total_allowed_before_first_penalty} entries before first penalty"
        )
        print("=" * 80)

        return {
            "status": "success",
            "run_mode": "manual" if run_now else "scheduled",
            "employees_processed": len(employee_list),
            "penalties_created": penalties_created,
            "skipped_regularizations": len(skipped_due_to_reg),
            "evaluation_period": {"from": str(from_date), "to": str(to_date)},
        }

    except Exception as main_error:
        print(f"\n💥 CRITICAL ERROR IN MAIN PROCESS:")
        print(f"❌ Error: {str(main_error)}")
        print(f"📍 Traceback: {frappe.get_traceback()}")
        frappe.log_error("Error in late entry penalty method", frappe.get_traceback())
        return {"status": "error", "message": str(main_error)}


import frappe
from frappe.utils import getdate
from frappe.utils import today

import frappe
from frappe.utils import getdate


def create_employee_penalty(
    employee,
    penalty_date,
    deduct_leave,
    attendance_id=None,
    leave_balance_before_application=0.0,
    leave_period_data=None,
    leave_allocation_id=None,
    for_late_coming=0,
    for_insufficient_hours=0,
    for_no_attendance=0,
    for_mispunch=0,
):
    """
    Creates or updates an Employee Penalty and deducts leave as per HR Settings priority.
    If penalty exists for the date, appends penalty detail row and updates summary.
    """

    # ! GET LEAVE PERIOD DATA
    leave_period_data = frappe.db.get_value(
        "Leave Period",
        {
            "is_active": 1,
            "from_date": ["<=", penalty_date],
            "to_date": [">=", penalty_date],
        },
        ["name", "from_date", "to_date"],
        as_dict=True,
    )

    # ! DETERMINE CONFIG FIELD BASED ON PENALTY TYPE
    if for_late_coming:
        priority_field = "custom_late_coming_leave_penalty_configuration"
        reason = "Late Coming"
        remarks_reason = f"Penalty for Late Entry on {penalty_date}"
    elif for_insufficient_hours:
        priority_field = "custom_weekly_attendance_leave_penalty_configuration"
        reason = "Insufficient Hours"
        remarks_reason = f"Penalty for Insufficient Hours on {penalty_date}"
    elif for_no_attendance:
        priority_field = "custom_no_attendance_leave_penalty_configuration"
        reason = "No Attendance"
        remarks_reason = f"Penalty for No Attendance Marked on {penalty_date}"
    elif for_mispunch:
        priority_field = "custom_attendance_mispunch_leave_penalty_configuration"
        reason = "Mispunch"
        remarks_reason = f"Penalty for Mispunch on {penalty_date}"
    else:
        frappe.throw("Penalty type not specified.")

    # ! FETCH CONFIGURED LEAVE PENALTY PRIORITY
    leave_priority = frappe.db.get_all(
        "Leave Penalty Configuration",
        filters={
            "parent": "HR Settings",
            "parenttype": "HR Settings",
            "parentfield": priority_field,
        },
        fields=[
            "penalty_deduction_type",
            "leave_type_for_penalty",
            "deduction_of_leave",
        ],
        order_by="idx asc",
    )
    if not leave_priority:
        frappe.throw("Leave Penalty Configuration not set in HR Settings.")

    # ! FETCH CURRENT LEAVE BALANCES
    leave_balances = get_remaining_leaves_for_penalty(employee)

    remaining_deduction = deduct_leave

    # ! CHECK IF PENALTY EXISTS FOR DATE
    existing_penalty = frappe.db.get_value(
        "Employee Penalty",
        {
            "employee": employee,
            "penalty_date": penalty_date,
            "workflow_state": "Pending",
        },
        [
            "name",
            "deduct_earned_leave",
            "deduct_leave_without_pay",
            "total_leave_penalty",
        ],
        as_dict=True,
    )

    if existing_penalty:
        penalty_doc = frappe.get_doc("Employee Penalty", existing_penalty.name)
        earned_leaves_total = existing_penalty.deduct_earned_leave or 0
        leave_without_pay_total = existing_penalty.deduct_leave_without_pay or 0
        total_penalty = existing_penalty.total_leave_penalty or 0
    else:
        penalty_doc = frappe.new_doc("Employee Penalty")
        penalty_doc.employee = employee
        penalty_doc.penalty_date = penalty_date
        penalty_doc.leave_balance_before_application = leave_balance_before_application
        penalty_doc.remarks = remarks_reason

        if for_late_coming:
            penalty_doc.for_late_coming = 1
        if for_insufficient_hours:
            penalty_doc.for_insufficient_hours = 1
        if for_no_attendance:
            penalty_doc.for_no_attendance = 1
        if for_mispunch:
            penalty_doc.for_mispunch = 1

        if attendance_id:
            penalty_doc.attendance = attendance_id
            update_attendance_status(attendance_id, deduct_leave)

        earned_leaves_total = 0
        leave_without_pay_total = 0
        total_penalty = 0

    # ! LOOP OVER CONFIGURED PRIORITIES TO DEDUCT LEAVES
    for config in leave_priority:
        if remaining_deduction <= 0:
            break

        deduction_type = config.penalty_deduction_type
        leave_type = config.leave_type_for_penalty
        deduction_unit = 0.5 if config.deduction_of_leave == "Half Day" else 1.0
        leave_amount = min(deduction_unit, remaining_deduction)

        if deduction_type == "Deduct Earned Leave":
            available_balance = leave_balances.get(leave_type, 0.0)

            if available_balance >= leave_amount:
                earned_leaves_total += 1
                penalty_doc.append(
                    "leave_penalty_table",
                    {
                        "leave_type": leave_type,
                        "leave_amount": leave_amount,
                        "reason": reason,
                        "remarks": remarks_reason,
                        "leave_balance_before_penalty": available_balance,
                    },
                )

                remaining_deduction -= leave_amount

        elif deduction_type == "Deduct Leave Without Pay":
            leave_without_pay_total += 1

            penalty_doc.append(
                "leave_penalty_table",
                {
                    "leave_type": leave_type,
                    "leave_amount": leave_amount,
                    "reason": reason,
                    "remarks": remarks_reason,
                    "leave_ledger_entry": None,
                    "leave_balance_before_penalty": 0,
                },
            )

            remaining_deduction -= leave_amount

    # ! UPDATE PENALTY TOTALS
    penalty_doc.total_leave_penalty = total_penalty + deduct_leave
    penalty_doc.deduct_earned_leave = earned_leaves_total
    penalty_doc.deduct_leave_without_pay = leave_without_pay_total

    if existing_penalty:
        penalty_doc.save(ignore_permissions=True)
    else:
        penalty_doc.insert(ignore_permissions=True)

    if attendance_id:
        frappe.db.set_value(
            "Attendance", attendance_id, "custom_employee_penalty_id", penalty_doc.name
        )

    frappe.db.commit()
    return penalty_doc.name


# ! METHOD TO CREATE LEAVE LEDGER ENTRY AND RETURN ITS NAME
@frappe.whitelist()
def add_leave_ledger_entry(
    employee, leave_type, leave_allocation_id, leave_period_data, earned_leave
):
    """
    Creates a Leave Ledger Entry for deduction and returns its name.
    Requires valid leave_period_data with 'from_date' and 'to_date'.
    """
    try:
        if (
            not leave_period_data
            or not leave_period_data.get("from_date")
            or not leave_period_data.get("to_date")
        ):
            frappe.throw(
                "Missing leave period data. 'from_date' and 'to_date' are required."
            )

        leave_ledger_entry_doc = frappe.new_doc("Leave Ledger Entry")
        leave_ledger_entry_doc.employee = employee
        leave_ledger_entry_doc.leave_type = leave_type
        leave_ledger_entry_doc.transaction_type = "Leave Allocation"
        leave_ledger_entry_doc.transaction_name = leave_allocation_id
        leave_ledger_entry_doc.from_date = getdate(today())
        leave_ledger_entry_doc.to_date = leave_period_data.get("to_date")
        leave_ledger_entry_doc.leaves = -abs(
            earned_leave
        )  # Deduction is always negative

        leave_ledger_entry_doc.insert(ignore_permissions=True)
        leave_ledger_entry_doc.submit()
        frappe.db.commit()

        return leave_ledger_entry_doc.name

    except Exception as e:
        frappe.log_error(
            message="Error in add_leave_ledger_entry", title=frappe.get_traceback()
        )
        return None


# ! UPDATE ATTENDANCE STATUS


def update_attendance_status(attendance_id, deduct_leave):
    status = frappe.db.get_value("Attendance", attendance_id, "status")
    if deduct_leave == 0.5:
        if status == "Present":
            frappe.db.set_value("Attendance", attendance_id, "status", "Half Day")
        elif status == "Half Day":
            frappe.db.set_value("Attendance", attendance_id, "status", "Absent")
    elif deduct_leave >= 1.0:
        frappe.db.set_value("Attendance", attendance_id, "status", "Absent")


# ! GET REMAINING LEAVES


def get_remaining_leaves_for_penalty(employee):
    entries = frappe.db.get_all(
        "Leave Ledger Entry",
        filters={"docstatus": 1, "employee": employee, "is_expired": 0},
        fields=["leave_type", "leaves"],
    )
    balance_map = {}
    for entry in entries:
        balance_map[entry.leave_type] = (
            balance_map.get(entry.leave_type, 0) + entry.leaves
        )
    return balance_map


import frappe
from frappe.utils import getdate, today, nowdate
from datetime import timedelta
import calendar


@frappe.whitelist()
def penalize_incomplete_week_for_indifoss(run_now=0):
    """
    PENALIZES EMPLOYEES WHO FAIL TO MEET WEEKLY WORK HOUR REQUIREMENTS FOR INDIFOSS BASED ON CONFIGURABLE RULES.
    EVALUATION WEEKS ARE FROM MONDAY TO SUNDAY.
    MONTHLY EVALUATION PERIOD: FROM (TRIGGER_DATE+1 LAST_MONTH)'S LAST MONDAY TO TRIGGER_DATE'S LAST SUNDAY.
    NOW SUPPORTS REPEAT PENALTIES BASED ON CONFIGURED DURATION INTERVALS.

    Args:
        run_now (int): If 1, runs for previous cycle window regardless of current date. Default is 0.
    """

    print("\n" + "=" * 80)
    print("🚀 STARTING INCOMPLETE WEEK PENALTY PROCESS")
    if int(run_now) == 1:
        print("⚡ MANUAL RUN MODE: Processing previous cycle")
    print("=" * 80)

    try:
        # ─────────────────────────────────────────────
        # STEP 1: FETCH COMPANY CONFIGURATION
        # ─────────────────────────────────────────────
        print("\n🏢 STEP 1: FETCHING COMPANY CONFIGURATION")

        company_id = fetch_company_name(indifoss=1)

        today_date = getdate(today())
        print(f"✅ Company ID: {company_id}")
        print(f"📅 Today's date: {today_date}")

        if company_id.get("error"):
            print(f"❌ ERROR: Company fetch failed - {company_id}")
            frappe.log_error(
                "Error in penalize_incomplete_week scheduler", frappe.get_traceback()
            )
            return

        # ─────────────────────────────────────────────
        # STEP 2: VALIDATE EXECUTION DATE
        # ─────────────────────────────────────────────
        print("\n📅 STEP 2: VALIDATING EXECUTION DATE")
        print("-" * 40)

        custom_cutoff_date = frappe.db.get_single_value(
            "HR Settings", "custom_month_date_for_attendance_penalty_indifoss"
        )

        if not custom_cutoff_date:
            print("❌ ERROR: Missing cutoff date in HR Settings")
            frappe.log_error(
                "Missing Cutoff Date",
                "CUSTOM_MONTH_DATE_FOR_ATTENDANCE_PENALTY_INDIFOSS not set",
            )
            return

        # Convert day number (like 31) into valid date in current month
        today_obj = getdate(nowdate())
        year = today_obj.year
        month = today_obj.month

        # If run_now is enabled, calculate for previous cycle
        if int(run_now) == 1:
            print("⚡ MANUAL RUN: Calculating for PREVIOUS cycle")
            # Go back one month
            if month == 1:
                month = 12
                year = year - 1
            else:
                month = month - 1

        # If value is numeric, treat it as a day in the target month
        if str(custom_cutoff_date).isdigit():
            cutoff_day = int(custom_cutoff_date)
            # Get last valid day of the month (handles Feb, April, etc.)
            last_day = calendar.monthrange(year, month)[1]
            # Avoid invalid dates like 31-Feb
            cutoff_day = min(cutoff_day, last_day)
            custom_cutoff_date = f"{year}-{month:02d}-{cutoff_day:02d}"

        # Now safely parse it
        to_date = getdate(custom_cutoff_date)
        print(f"📌 Cutoff date: {to_date}")
        print(f"📅 Expected execution date: {to_date + timedelta(days=1)}")

        # Skip date validation if run_now is enabled
        if int(run_now) != 1:
            if today_date != (to_date + timedelta(days=1)):
                print(
                    "⏭️  SKIPPING: Not the day after cutoff - process should run on cutoff+1 day"
                )
                return
            print("✅ Execution date validated - proceeding with penalty process")
        else:
            print("✅ Manual run mode - bypassing date validation")

        # ─────────────────────────────────────────────
        # STEP 3: FETCH BASIC PARAMETERS
        # ─────────────────────────────────────────────
        print("\n📋 STEP 3: FETCHING BASIC PARAMETERS")
        print("-" * 40)

        # Cache HR Settings values to avoid repeated queries
        hr_settings = frappe.get_single("HR Settings")
        expected_work_hours_per_day = float(
            hr_settings.custom_weekly_hours_criteria_for_penalty_for_indifoss or 0
        )
        grace_minutes = int(hr_settings.custom_weekly_hours_grace_for_indifoss or 0)

        # Fetch repeat penalty duration in minutes
        repeat_penalty_minutes = 480

        print(f"✅ Expected work hours per day: {expected_work_hours_per_day}")
        print(f"✅ Grace minutes: {grace_minutes}")
        print(f"✅ Repeat penalty duration (minutes): {repeat_penalty_minutes}")

        if expected_work_hours_per_day <= 0:
            print("❌ ERROR: Invalid expected work hours per day")
            frappe.log_error(
                "Invalid Configuration",
                "Expected work hours per day must be greater than 0",
            )
            return

        # Default deduction amount - actual configuration will be handled by create_employee_penalty method
        insufficient_hours_deduct_leave = 1.0
        print(
            f"✅ Default leave deduction: {insufficient_hours_deduct_leave} (actual amount determined by penalty configuration)"
        )

        # ─────────────────────────────────────────────
        # STEP 4: FETCH ACTIVE EMPLOYEES
        # ─────────────────────────────────────────────
        print("\n👥 STEP 4: FETCHING ACTIVE EMPLOYEES")
        print("-" * 40)

        employee_list = frappe.db.get_all(
            "Employee",
            filters={"status": "Active", "company": company_id.get("company_id")},
            fields=[
                "name",
                "custom_weeklyoff",
                "date_of_joining",
                "relieving_date",
                "holiday_list",
            ],
        )
        print(f"✅ Total active employees found: {len(employee_list)}")

        if not employee_list:
            print("⏭️  No active employees found - exiting")
            return

        # ─────────────────────────────────────────────
        # STEP 5: DEFINE EVALUATION WINDOW
        # ─────────────────────────────────────────────
        print("\n📅 STEP 5: DEFINING EVALUATION WINDOW")
        print("-" * 40)

        # Get trigger date (cutoff date from HR Settings)
        print(f"📌 Trigger date (cutoff): {to_date}")

        # Calculate monthly evaluation period
        # Start: Last month's (trigger_date + 1) date's last Monday
        last_month_date = to_date.replace(day=1) - timedelta(
            days=1
        )  # Last day of previous month
        start_day = min(
            to_date.day + 1, last_month_date.day
        )  # Handle month-end edge cases

        try:
            monthly_start_reference = last_month_date.replace(day=start_day)
        except ValueError:
            # Handle case where start_day doesn't exist in last month (e.g., Feb 31 -> Feb 28)
            monthly_start_reference = last_month_date

        print(f"📅 Monthly start reference date: {monthly_start_reference}")

        # Find last Monday of the monthly start reference date
        # Python weekday: Monday=0, Sunday=6
        monthly_ref_weekday = monthly_start_reference.weekday()
        if monthly_ref_weekday == 0:  # Already Monday
            monthly_eval_start = monthly_start_reference
        else:
            # Go back to last Monday
            days_back_to_monday = monthly_ref_weekday
            monthly_eval_start = monthly_start_reference - timedelta(
                days=days_back_to_monday
            )

        print(f"📅 Monthly evaluation start (last Monday): {monthly_eval_start}")

        # End: Trigger date's last Sunday
        trigger_weekday = to_date.weekday()
        if trigger_weekday == 6:  # Already Sunday
            monthly_eval_end = to_date
        else:
            # Go back to last Sunday
            days_back_to_sunday = (trigger_weekday + 1) % 7
            monthly_eval_end = to_date - timedelta(days=days_back_to_sunday)

        print(f"📅 Monthly evaluation end (last Sunday): {monthly_eval_end}")
        print(f"📅 Total evaluation period: {monthly_eval_start} to {monthly_eval_end}")

        # Validate that we have a valid evaluation period
        if monthly_eval_start > monthly_eval_end:
            print("❌ ERROR: Invalid evaluation period - start date is after end date")
            frappe.log_error(
                "Invalid Evaluation Period",
                f"Start: {monthly_eval_start}, End: {monthly_eval_end}",
            )
            return

        eval_start_date = monthly_eval_start
        eval_end_date_limit = monthly_eval_end

        penalties_created = 0
        weeks_processed = 0
        grace_hours = grace_minutes / 60.0
        repeat_penalty_hours = repeat_penalty_minutes / 60.0

        # ─────────────────────────────────────────────
        # STEP 6: PROCESS WEEKLY EVALUATIONS
        # ─────────────────────────────────────────────
        print(f"\n⏰ STEP 6: PROCESSING WEEKLY EVALUATIONS (Monday to Sunday)")
        print("-" * 40)

        # Process week by week from Monday to Sunday
        current_monday = eval_start_date
        while current_monday <= eval_end_date_limit:
            # Calculate Sunday of current week
            current_sunday = current_monday + timedelta(days=6)

            # Ensure we don't go beyond the monthly evaluation end date
            week_end_date = min(current_sunday, eval_end_date_limit)

            weeks_processed += 1
            print(
                f"\n📅 [WEEK {weeks_processed}] Processing: {current_monday} (Mon) to {week_end_date} (Sun)"
            )

            # Validate this is a complete week or acceptable partial week
            days_in_week = (week_end_date - current_monday).days + 1
            print(f"   📊 Days in this evaluation week: {days_in_week}")

            if days_in_week < 7:
                print(f"   ⚠️  PARTIAL WEEK: Only {days_in_week} days")

            employees_processed = 0
            employees_penalized = 0

            for emp_idx, emp in enumerate(employee_list, 1):
                emp_name = emp["name"]
                joining_date = emp.get("date_of_joining") or current_monday
                relieving_date = emp.get("relieving_date") or week_end_date

                print(
                    f"\n   👤 [{emp_idx}/{len(employee_list)}] Processing: {emp_name}"
                )

                # Adjust week range to employee's joining/relieving dates
                effective_week_start = max(current_monday, joining_date)
                effective_week_end = min(week_end_date, relieving_date)

                if effective_week_start > effective_week_end:
                    print(
                        f"      ⏭️  SKIPPED: Outside employment range ({joining_date} to {relieving_date})"
                    )
                    continue

                print(
                    f"      📅 Effective week period: {effective_week_start} to {effective_week_end}"
                )
                employees_processed += 1

                # Check penalty eligibility
                try:
                    penalty_criteria_result = check_employee_penalty_criteria(
                        emp_name, "For Work Hours"
                    )
                    print(f"      ✅ Penalty criteria check: {penalty_criteria_result}")

                    if not penalty_criteria_result:
                        print(f"      ⏭️  SKIPPED: Not eligible for penalty")
                        continue
                except Exception as e:
                    print(f"      ❌ ERROR checking penalty criteria: {str(e)}")
                    continue

                if not emp.get("custom_weeklyoff"):
                    print(f"      ⏭️  SKIPPED: No weekly off configured")
                    continue

                # Calculate approved leaves
                print(f"      🔍 Calculating approved leaves...")
                try:
                    leave_application_list = frappe.db.get_all(
                        "Leave Application",
                        {
                            "employee": emp_name,
                            "status": "Approved",
                            "from_date": ["<=", effective_week_end],
                            "to_date": [">=", effective_week_start],
                        },
                        ["name", "half_day", "from_date", "to_date"],
                    )

                    # Calculate actual leave days within the week period
                    leave_day_count = 0
                    for leave in leave_application_list:
                        leave_start = max(
                            getdate(leave["from_date"]), effective_week_start
                        )
                        leave_end = min(getdate(leave["to_date"]), effective_week_end)
                        leave_days = (leave_end - leave_start).days + 1

                        if leave["half_day"]:
                            leave_day_count += leave_days * 0.5
                        else:
                            leave_day_count += leave_days

                    print(f"         📋 Approved leave days: {leave_day_count}")
                except Exception as e:
                    print(f"      ❌ ERROR calculating leaves: {str(e)}")
                    leave_day_count = 0

                # Calculate holiday count
                print(f"      🔍 Calculating holidays...")
                try:
                    emp_holiday_list = emp.get("holiday_list")
                    holiday_day_count = 0
                    if emp_holiday_list:
                        holiday_day_count = frappe.db.count(
                            "Holiday",
                            {
                                "parenttype": "Holiday List",
                                "parent": emp_holiday_list,
                                "holiday_date": [
                                    "between",
                                    [effective_week_start, effective_week_end],
                                ],
                            },
                        )
                    print(f"         🎉 Holiday days: {holiday_day_count}")
                except Exception as e:
                    print(f"      ❌ ERROR calculating holidays: {str(e)}")
                    holiday_day_count = 0

                # Calculate working requirements
                total_days = (effective_week_end - effective_week_start).days + 1
                eligible_working_days = total_days - leave_day_count - holiday_day_count
                expected_hours = expected_work_hours_per_day * eligible_working_days

                print(f"      📊 Working days calculation:")
                print(f"         Total days in period: {total_days}")
                print(f"         Leave days: {leave_day_count}")
                print(f"         Holiday days: {holiday_day_count}")
                print(f"         Eligible working days: {eligible_working_days}")
                print(f"         Expected work hours: {expected_hours}")

                # Skip if no working days expected
                if eligible_working_days <= 0:
                    print(f"      ⏭️  SKIPPED: No eligible working days in this period")
                    continue

                # Get actual working hours
                print(f"      🔍 Fetching actual working hours...")
                try:
                    attendance = frappe.db.get_all(
                        "Attendance",
                        {
                            "employee": emp_name,
                            "attendance_date": [
                                "between",
                                [effective_week_start, effective_week_end],
                            ],
                            "status": ["!=", "Mispunch"],
                        },
                        ["working_hours"],
                    )
                    total_hours = sum(float(a.working_hours or 0) for a in attendance)

                    print(f"         ⏰ Actual work hours: {total_hours}")
                    print(f"         🎯 Expected hours: {expected_hours}")
                    print(f"         ⏳ Grace hours: {grace_hours}")
                    print(f"         📈 Hours with grace: {total_hours + grace_hours}")
                except Exception as e:
                    print(f"      ❌ ERROR fetching attendance: {str(e)}")
                    continue

                # Check if penalty is needed - considering grace period
                hours_with_grace = total_hours + grace_hours
                if hours_with_grace >= expected_hours:
                    print(f"      ✅ PASSED: No penalty required")
                    continue

                print(f"      ⚠️  INSUFFICIENT HOURS: Penalty required")

                # Calculate multiple penalties based on repeat duration
                print(f"      🔢 CALCULATING MULTIPLE PENALTIES:")

                # Calculate how many hours short (after grace period)
                hours_deficit = expected_hours - hours_with_grace
                print(f"         📉 Hours deficit (after grace): {hours_deficit:.2f}")

                # If repeat penalty duration is configured, calculate number of penalties
                if repeat_penalty_minutes > 0 and repeat_penalty_hours > 0:
                    # Calculate number of penalties needed
                    num_penalties = int(hours_deficit / repeat_penalty_hours)
                    if hours_deficit % repeat_penalty_hours > 0:
                        num_penalties += 1
                    print(
                        f"         🔄 Repeat penalty interval: {repeat_penalty_hours:.2f} hours"
                    )
                    print(f"         📊 Number of penalties to create: {num_penalties}")
                else:
                    # Default: single penalty
                    num_penalties = 1
                    print(f"         📊 Single penalty (no repeat duration configured)")

                # Find attendance record to tag penalty
                print(f"      🔍 Finding attendance record for penalty tagging...")
                try:
                    attendance_id = frappe.db.get_all(
                        "Attendance",
                        {
                            "employee": emp_name,
                            "attendance_date": [
                                "between",
                                [effective_week_start, effective_week_end],
                            ],
                            "status": ["in", ["Present", "Work From Home", "Half Day"]],
                        },
                        ["name", "attendance_date"],
                        order_by="attendance_date desc",
                        limit=1,
                    )

                    if not attendance_id:
                        print(f"      ⏭️  SKIPPED: No suitable attendance record found")
                        continue

                    attendance_name = attendance_id[0]["name"]
                    attendance_date = attendance_id[0]["attendance_date"]
                    print(
                        f"         📄 Using attendance: {attendance_name} ({attendance_date})"
                    )
                except Exception as e:
                    print(f"      ❌ ERROR finding attendance record: {str(e)}")
                    continue

                # Check exclusion conditions
                print(f"      🔍 Checking exclusion conditions...")

                try:
                    # Check if leave exists for the attendance date
                    leave_exists = frappe.db.exists(
                        "Leave Application",
                        {
                            "employee": emp_name,
                            "docstatus": 1,
                            "from_date": ["<=", attendance_date],
                            "to_date": [">=", attendance_date],
                        },
                    )
                    print(f"         📋 Leave exists check: {bool(leave_exists)}")

                    if leave_exists:
                        print(f"      ⏭️  SKIPPED: Leave exists for attendance date")
                        continue

                    # Check if attendance regularization exists
                    reg_exists = frappe.db.exists(
                        "Attendance Regularization",
                        {
                            "employee": emp_name,
                            "attendance": attendance_name,
                            "regularization_date": attendance_date,
                        },
                    )
                    print(
                        f"         🔄 Regularization exists check: {bool(reg_exists)}"
                    )

                    if reg_exists:
                        print(f"      ⏭️  SKIPPED: Attendance regularization exists")
                        continue

                    # Check for existing penalties in the given week for the employee
                    existing_penalties = frappe.db.get_all(
                        "Employee Penalty",
                        {
                            "employee": emp_name,
                            "penalty_date": [
                                "between",
                                [current_monday, week_end_date],
                            ],
                        },
                        ["name"],
                    )

                    # Count existing "Insufficient Hours" penalties
                    existing_insufficient_hours_count = 0
                    for penalty in existing_penalties:
                        reason_exists = frappe.db.exists(
                            "Employee Leave Penalty Details",
                            {"parent": penalty["name"], "reason": "Insufficient Hours"},
                        )
                        if reason_exists:
                            existing_insufficient_hours_count += 1

                    print(
                        f"         ⚠️ Existing 'Insufficient Hours' penalties: {existing_insufficient_hours_count}"
                    )

                    # Calculate how many new penalties we need to create
                    penalties_to_create = max(
                        0, num_penalties - existing_insufficient_hours_count
                    )
                    print(f"         📊 New penalties to create: {penalties_to_create}")

                    if penalties_to_create <= 0:
                        print(f"      ⏭️  SKIPPED: Required penalties already exist")
                        continue

                except Exception as e:
                    print(f"      ❌ ERROR checking exclusion conditions: {str(e)}")
                    continue

                # Create multiple penalties based on deficit and repeat duration
                penalty_date = effective_week_end  # Use week end date (Sunday or last day of period)
                penalties_created_for_employee = 0

                print(
                    f"      🎯 CREATING {penalties_to_create} PENALTIES for insufficient hours"
                )
                print(f"         📝 Employee: {emp_name}")
                print(f"         📅 Penalty Date: {penalty_date}")
                print(f"         📄 Attendance ID: {attendance_name}")
                print(
                    f"         💰 Leave Deduction per penalty: {insufficient_hours_deduct_leave}"
                )

                for penalty_idx in range(penalties_to_create):
                    try:
                        # Calculate the threshold for this penalty
                        if repeat_penalty_minutes > 0 and repeat_penalty_hours > 0:
                            penalty_threshold = expected_hours - (
                                penalty_idx * repeat_penalty_hours
                            )
                            print(
                                f"         🎯 Penalty {penalty_idx + 1}: Threshold {penalty_threshold:.2f} hours (deficit: {penalty_threshold - hours_with_grace:.2f} hours)"
                            )
                        else:
                            print(
                                f"         🎯 Creating single penalty for insufficient hours"
                            )

                        penalty_id = create_employee_penalty(
                            employee=emp_name,
                            penalty_date=penalty_date,
                            deduct_leave=insufficient_hours_deduct_leave,
                            attendance_id=attendance_name,
                            leave_balance_before_application=0.0,  # Will be calculated inside the method
                            leave_period_data=None,  # Will be fetched inside the method
                            leave_allocation_id=None,  # Will be determined inside the method
                            for_late_coming=0,
                            for_insufficient_hours=1,
                            for_no_attendance=0,
                            for_mispunch=0,
                        )

                        penalties_created += 1
                        penalties_created_for_employee += 1
                        print(
                            f"         ✅ PENALTY {penalty_idx + 1} CREATED SUCCESSFULLY!"
                        )
                        print(f"         📄 Penalty ID: {penalty_id}")

                    except Exception as penalty_error:
                        print(
                            f"         ❌ ERROR CREATING PENALTY {penalty_idx + 1}: {str(penalty_error)}"
                        )
                        frappe.log_error(
                            f"Error creating penalty {penalty_idx + 1} for {emp_name}",
                            str(penalty_error),
                        )

                if penalties_created_for_employee > 0:
                    employees_penalized += 1
                    print(
                        f"      ✅ TOTAL PENALTIES CREATED FOR {emp_name}: {penalties_created_for_employee}"
                    )
                    print(
                        f"      📊 Total penalties created so far: {penalties_created}"
                    )

            print(f"\n   📊 Week {weeks_processed} Summary:")
            print(f"      - Week period: {current_monday} to {week_end_date}")
            print(f"      - Employees processed: {employees_processed}")
            print(f"      - Employees penalized: {employees_penalized}")

            # Move to next Monday
            current_monday += timedelta(days=7)

        # ─────────────────────────────────────────────
        # FINAL SUMMARY
        # ─────────────────────────────────────────────
        print(f"\n" + "=" * 80)
        print(f"🎉 INCOMPLETE WEEK PENALTY PROCESS COMPLETED!")
        print(f"📊 FINAL SUMMARY:")
        print(f"   - Evaluation period: {monthly_eval_start} to {monthly_eval_end}")
        print(f"   - Total weeks processed: {weeks_processed}")
        print(f"   - Total employees evaluated: {len(employee_list)}")
        print(f"   - Total penalties created: {penalties_created}")
        if repeat_penalty_minutes > 0:
            print(
                f"   - Repeat penalty interval: {repeat_penalty_minutes} minutes ({repeat_penalty_hours:.2f} hours)"
            )
        if int(run_now) == 1:
            print(f"   - Mode: MANUAL RUN (Previous Cycle)")
        print("=" * 80)

    except Exception as e:
        print(f"\n💥 CRITICAL ERROR IN INCOMPLETE WEEK PENALTY PROCESS:")
        print(f"❌ Error: {str(e)}")
        print(f"📍 Traceback: {frappe.get_traceback()}")
        frappe.log_error(
            "Error in penalize_incomplete_week scheduler", frappe.get_traceback()
        )


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


@frappe.whitelist()
def check_employee_penalty_criteria(employee=None, penalization_type=None):
    print("\n\n======================== DEBUG START ========================")
    print("🔥 Function Called: check_employee_penalty_criteria")
    print(f"INPUT employee={employee}, INPUT penalization_type={penalization_type}")

    # OVERRIDE FOR DEBUG
    employee = "090: Puran Mal Menariya"
    penalization_type = "For Late Arrival"

    print("\n🎯 Using DEBUG employee override:")
    print(f"employee = {employee}")
    print(f"penalization_type = {penalization_type}")

    print("\n📌 Fetching Employee Document...")
    employee = frappe.get_doc("Employee", employee)
    print(f"✅ Employee Loaded: {employee.name}")
    print(f"➡️  Department = {employee.department}")
    print(f"➡️  Subdepartment = {employee.custom_subdepartment}")
    print(f"➡️  Employment Type = {employee.employment_type}")
    print(f"➡️  Designation = {employee.designation}")
    print(f"➡️  Grade = {employee.grade}")
    print(f"➡️  Work Location = {employee.custom_work_location}")
    print(f"➡️  Product Line = {employee.custom_product_line}")
    print(f"➡️  Business Unit = {employee.custom_business_unit}")
    print(f"➡️  Company = {employee.company}")

    company_abbr = frappe.db.get_value("Company", employee.company, "abbr")
    print(f"\n🏢 Company Abbreviation: {company_abbr}")

    print("\n📌 Loading HR Settings...")
    hr_settings = frappe.get_single("HR Settings")
    print("✅ HR Settings Loaded")

    print("\n🔧 FIELD MAPPING:")
    criteria = {
        "Business Unit": "custom_business_unit",
        "Department": "department",
        "Address": "custom_work_location",
        "Employment Type": "employment_type",
        "Employee Grade": "grade",
        "Designation": "designation",
        "Product Line": "custom_product_line",
    }
    print(criteria)

    # Abbreviations
    prompt_abbr = hr_settings.custom_prompt_abbr
    indifoss_abbr = hr_settings.custom_indifoss_abbr

    print("\n🏢 Company Abbreviation Matching:")
    print(f"PROMPT Abbr = {prompt_abbr}")
    print(f"INDIFOSS Abbr = {indifoss_abbr}")
    print(f"Employee Company Abbr = {company_abbr}")

    # Determine which table to use
    if company_abbr == prompt_abbr:
        print("\n✅ Employee belongs to PROMPT, using PROMPT table")
        table = hr_settings.custom_penalization_criteria_table_for_prompt
    elif company_abbr == indifoss_abbr:
        print("\n✅ Employee belongs to INDIFOSS, using INDIFOSS table")
        table = hr_settings.custom_penalization_criteria_table_for_indifoss
    else:
        print("\n⚠️ Company does not match PROMPT or INDIFOSS → ALLOW")
        return True

    if not table:
        print("\n⚠️ No table configured → ALLOW")
        return True

    print("\n📋 Penalization Table Loaded:")
    for idx, row in enumerate(table, 1):
        print(
            f"   Row {idx}: penalization_type={row.penalization_type}, "
            f"doctype={row.select_doctype}, value={row.value}, subdept={row.is_sub_department}"
        )

    print("\n🔍 Now Evaluating Criteria Rows...\n")

    is_penalisation = False

    for idx, row in enumerate(table, 1):
        print(f"\n------------------ ROW #{idx} ------------------")
        print(f"Row Penalization Type: {row.penalization_type}")
        print(f"Expected Penalization Type: {penalization_type}")

        if row.penalization_type != penalization_type:
            print("❌ Penalization type does NOT MATCH → SKIP")
            continue

        print("✅ Penalization type MATCHED")
        is_penalisation = True

        print(f"Row Doctype = {row.select_doctype}")
        print(f"Row Value = {row.value}")
        print(f"Row is_sub_department = {row.is_sub_department}")

        # Subdepartment rule
        if row.select_doctype == "Department" and row.is_sub_department:
            print("\n📌 Checking SUBDEPARTMENT:")
            print(f"Employee Subdepartment = {employee.custom_subdepartment}")
            print(f"Required = {row.value}")

            if employee.custom_subdepartment == row.value:
                print("✅ MATCHED SUBDEPARTMENT → RETURN True")
                print("======================== DEBUG END ========================")
                return True

            print("❌ Subdepartment did NOT match → Continue")
            continue

        # Normal field matching
        employee_fieldname = criteria.get(row.select_doctype)
        print(f"\n📌 Checking NORMAL FIELD MATCH")
        print(f"Employee FieldName Mapped = {employee_fieldname}")

        if not employee_fieldname:
            print("❌ No mapping found for this select_doctype → SKIP")
            continue

        emp_value = getattr(employee, employee_fieldname, None)
        print(f"Employee Value = {emp_value}")
        print(f"Required Value = {row.value}")

        if emp_value == row.value:
            print("✅ FIELD MATCH → RETURN True")
            print("======================== DEBUG END ========================")
            return True

        print("❌ Field NOT matched → Continue")

    print("\n✅ Finished scanning all rows")
    print(f"is_penalisation = {is_penalisation}")

    if not is_penalisation:
        print("✅ No rules exist for this penalization_type → ALLOW")
        print("======================== DEBUG END ========================")
        return True

    print("❌ Rules exist but NO match → DENY")
    print("======================== DEBUG END ========================")
    return False


# ? DAILY SCHEDULER TO HANDLE EXIT CHECKLIST & INTERVIEW AUTOMATICALLY
def process_exit_approvals():
    today_date = getdate(today())

    records = frappe.get_all(
        "Exit Approval Process",
        filters={"resignation_approval": "Approved"},
        fields=[
            "name",
            "employee",
            "company",
            "custom_exit_checklist_notification_date",
            "employee_separation",
            "exit_interview",
        ],
    )

    for r in records:
        try:

            # ? PROCESS CHECKLIST IF DUE AND NOT YET CREATED
            checklist_due = (
                r.custom_exit_checklist_notification_date
                and getdate(r.custom_exit_checklist_notification_date) <= today_date
                and not r.employee_separation
            )
            if checklist_due:
                raise_exit_checklist(r.employee, r.company, r.name)

        except Exception as e:
            frappe.log_error(
                title="Auto Exit Process Error",
                message=frappe.get_traceback()
                + f"\n\nEmployee: {r.employee}, Company: {r.company}",
            )


# * Scheduler entry: Call on 15th and 2 days before month end
def send_penalty_summary_email():
    current_date = getdate(today())
    day = current_date.day

    # ? Send on 15th of the month
    if day == 15:
        send_penalty_summary_notification(current_date)

    # ? Send 2 days before month end
    last_day = get_last_day(current_date)
    if current_date == add_days(last_day, -2):
        send_penalty_summary_notification(current_date)


# * Sends penalty summary grouped by penalty type and leave type
def send_penalty_summary_notification(current_date=None):
    # * If not current date, use today
    if not current_date:
        current_date = today()

    first_day = get_first_day(current_date)

    # * Get company context (here, Indifoss)
    company = fetch_company_name(indifoss=1)
    if company.get("error"):
        frappe.log_error(
            "Error in send_penalty_summary_notification", frappe.get_traceback()
        )
        return

    if not company.get("company_id"):
        return

    # * Get all active employees in the company
    employees = frappe.db.get_all(
        "Employee",
        {"status": "Active", "company": company.get("company_id")},
        ["name", "employee_name", "user_id"],
    )

    for emp in employees:
        # * Fetch penalty entries between first_day and current date
        penalties = frappe.db.get_all(
            "Employee Penalty",
            {
                "employee": emp.name,
                "company": company.get("company_id"),
                "workflow_state": "Pending",
                "penalty_date": ["between", [first_day, current_date]],
            },
            [
                "penalty_date",
                "for_late_coming",
                "for_insufficient_hours",
                "for_no_attendance",
                "total_leave_penalty",
                "remarks",
                "deduct_leave_without_pay",
                "deduct_earned_leave",
            ],
            order_by="penalty_date asc",
        )
        if not penalties:
            continue  # Skip employees with no penalties

        # * Initialize totals
        total_earned_leave = 0.0
        total_lwp_leave = 0.0
        total_deducted = 0.0

        # * Grouped summary for Late Entry, Insufficient Hours, No Attendance
        penalty_summary_by_type = {
            "Late Entry": {"earned": 0.0, "lwp": 0.0, "total": 0.0},
            "No Attendance": {"earned": 0.0, "lwp": 0.0, "total": 0.0},
            "Insufficient Hours": {"earned": 0.0, "lwp": 0.0, "total": 0.0},
            "Other Penalties": {
                "earned": 0.0,
                "lwp": 0.0,
                "total": 0.0,
            },  # <-- for uncategorized penalties
        }

        for p in penalties:
            earned = p.deduct_earned_leave or 0
            lwp = p.deduct_leave_without_pay or 0

            penalty_types = []

            if p.for_late_coming:
                penalty_types.append("Late Entry")
            if p.for_no_attendance:
                penalty_types.append("No Attendance")
            if p.for_insufficient_hours:
                penalty_types.append("Insufficient Hours")
            if not penalty_types:
                penalty_types.append("Other Penalties")

            # Distribute earned/lwp into each applicable type
            for ptype in penalty_types:
                penalty_summary_by_type[ptype]["earned"] += earned
                penalty_summary_by_type[ptype]["lwp"] += lwp

            # Totals (count once per penalty entry, not per type)
            total_earned_leave += earned
            total_lwp_leave += lwp
            total_deducted += earned + lwp

        # * Compute per-type total
        for t in penalty_summary_by_type.values():
            t["total"] = t["earned"] + t["lwp"]

        # * Load the Notification document
        notification = frappe.get_doc("Notification", "Penalty Summary Report")

        if notification and emp.user_id:
            # * Get employee email
            email_id = frappe.db.get_value("User", emp.user_id, "email")
            if email_id:
                # * Render subject
                subject = frappe.render_template(
                    notification.subject,
                    {
                        "from_date": formatdate(first_day),
                        "to_date": formatdate(current_date),
                    },
                )

                # * Render full email message
                message = frappe.render_template(
                    notification.message,
                    {
                        "employee_name": emp.employee_name,
                        "from_date": formatdate(first_day),
                        "to_date": formatdate(current_date),
                        "penalty_summary_by_type": penalty_summary_by_type,
                        "total_earned_leave": total_earned_leave,
                        "total_lwp_leave": total_lwp_leave,
                        "total_deducted": total_deducted,
                    },
                )

                # * Send email
                frappe.sendmail(recipients=[email_id], subject=subject, message=message)


# ! DAILY SCHEDULER TO HANDLE ATTENDANCE REQUEST RITUALS
@frappe.whitelist()
def daily_attendance_request_rituals():

    all_employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "custom_attendance_capture_scheme"],
    )

    # ? ATTENDANCE CAPTURE SCHEME MAP BASED ON WORK MODE
    attendance_capture_scheme_map = {
        "Work From Home": "Web Checkin-Checkout",
        "On Duty": "Mobile Clockin-Clockout",
    }

    # ? CREATE EMPLOYEE HASHMAP FOR QUICK ACCESS (NAME AS KEY AND SCHEME AS VALUE)
    employee_map = {
        emp.name: emp.custom_attendance_capture_scheme for emp in all_employees
    }

    all_attendance_requests = frappe.get_all(
        "Attendance Request",
        filters={
            "docstatus": 1,
            "custom_status": "Approved",
            "employee": ["in", list(employee_map.keys())],
            "from_date": ["<=", today()],
            "to_date": [">=", today()],
        },
        fields=["name", "employee", "reason"],
    )

    attendance_request_hashmap = {}
    for request in all_attendance_requests:
        employee_name = request.employee
        if employee_name not in attendance_request_hashmap:
            attendance_request_hashmap[employee_name] = []
        attendance_request_hashmap[employee_name].append(request)

    for employee, scheme in employee_map.items():
        attendance_request = attendance_request_hashmap.get(employee)
        if attendance_request:
            reason = attendance_request[0].get("reason")
            scheme = attendance_capture_scheme_map.get(reason)
            if employee_map.get(employee) != scheme:
                # ? UPDATE EMPLOYEE SCHEME IF IT DOES NOT MATCH
                frappe.db.set_value(
                    "Employee", employee, "custom_attendance_capture_scheme", scheme
                )
                frappe.db.commit()

        elif not attendance_request and scheme in [
            "Mobile Clockin-Clockout",
            "Web Checkin-Checkout",
        ]:
            # ? IF NO ATTENDANCE REQUEST EXISTS FOR THE EMPLOYEE, SET THE SCHEME TO BIOMETRIC
            frappe.db.set_value(
                "Employee", employee, "custom_attendance_capture_scheme", "Biometric"
            )
            frappe.db.commit()


@frappe.whitelist()
def penalize_employee_for_attendance_mispunch_indifoss(run_now=0):
    """
    PENALIZE EMPLOYEES WHO HAVE ATTENDANCE RECORDS MARKED AS 'MISPUNCH' AND
    DO NOT ALREADY HAVE A PENALTY RECORDED FOR THE SAME ATTENDANCE DATE.

    TRIGGERED (scheduled) ON: HR Settings -> custom_month_date_for_attendance_penalty_indifoss + 1
    If run_now=1, the function will process the previous completed cycle immediately,
    regardless of today's date.
    """

    print("\n" + "=" * 80)
    print("🚀 STARTING MISPUNCH PENALTY PROCESS")
    print("=" * 80)

    try:
        from calendar import monthrange
        from frappe.utils import (
            get_first_day,
            getdate,
            add_months,
            add_days,
            get_last_day,
        )
        from datetime import timedelta
        import frappe

        # Normalize run_now
        run_now = int(run_now) if run_now else 0

        # ─────────────────────────────────────────────
        # STEP 1: TRIGGER DATE VALIDATION (unless manual run)
        # ─────────────────────────────────────────────
        print("\n📅 STEP 1: VALIDATING TRIGGER DATE")
        print("-" * 40)

        today_date = getdate()
        today_day = today_date.day
        print(f"📅 Today's date: {today_date} (Day: {today_day})")

        penalty_day_str = frappe.db.get_single_value(
            "HR Settings", "custom_month_date_for_attendance_penalty_indifoss"
        )
        if not penalty_day_str:
            print("❌ ERROR: Missing penalty day in HR Settings")
            frappe.log_error(
                "Missing Penalty Day",
                "HR Settings: custom_month_date_for_attendance_penalty_indifoss not set",
            )
            return

        configured_penalty_day = int(penalty_day_str)
        max_day = monthrange(today_date.year, today_date.month)[1]
        expected_trigger_day = min(configured_penalty_day + 1, max_day)

        print(f"📌 Configured penalty day: {configured_penalty_day}")
        print(f"📅 Max days in month: {max_day}")
        print(f"🎯 Expected trigger day: {expected_trigger_day}")

        if run_now == 0:
            # scheduled mode: only run on expected trigger day
            if today_day != expected_trigger_day:
                print(f"⏭️  SKIPPING: Not the scheduled mispunch penalty day")
                print(
                    f"   Expected: Day {expected_trigger_day}, Today: Day {today_day}"
                )
                return
            else:
                print(
                    "✅ Trigger date validated - proceeding with scheduled penalty process"
                )
        else:
            print(
                "⚡ MANUAL RUN requested (run_now=1) - processing previous completed cycle"
            )

        # ─────────────────────────────────────────────
        # STEP 2: FETCH COMPANY CONFIGURATION
        # ─────────────────────────────────────────────
        print("\n🏢 STEP 2: FETCHING COMPANY CONFIGURATION")
        print("-" * 40)

        company = get_indifoss_company_name().get("company_name")
        if not company:
            print("❌ ERROR: No company found")
            frappe.log_error(
                "Missing Company", "get_indifoss_company_name() returned no company"
            )
            return

        print(f"✅ Company: {company}")

        # Default deduction amount - actual configuration will be handled by create_employee_penalty method
        deduct_days = 1.0  # This will be overridden by the penalty configuration
        print(
            f"✅ Default leave deduction: {deduct_days} (actual amount determined by penalty configuration)"
        )

        # ─────────────────────────────────────────────
        # STEP 3: DEFINE EVALUATION WINDOW (CYCLE BASED)
        # ─────────────────────────────────────────────
        print("\n📅 STEP 3: DEFINING EVALUATION WINDOW (CYCLE BASED)")
        print("-" * 40)

        # If scheduled run (run_now==0), we already know today is expected_trigger_day.
        # Define evaluation window based on current date.
        if run_now == 0:
            # If today's date is greater than the cutoff day → current cycle started last cutoff day
            if today_date.day > configured_penalty_day:
                eval_start = today_date.replace(day=configured_penalty_day + 1)
                eval_end = add_months(eval_start, 1) - timedelta(days=1)
            else:
                # If today is before or on cutoff → previous cycle is active
                last_month = add_months(today_date, -1)
                eval_start = last_month.replace(day=configured_penalty_day + 1)
                eval_end = today_date.replace(day=configured_penalty_day)
        else:
            # Manual run: process the PREVIOUS COMPLETED cycle
            # Cycle definition:
            #   - If configured cutoff is month-end (>= last day), use previous calendar month
            #   - Else use: (cutoff+1 of prev-prev month) -> cutoff of previous month
            last_day_of_current_month = get_last_day(today_date).day
            if configured_penalty_day >= last_day_of_current_month:
                # previous calendar month
                first_day_of_current_month = today_date.replace(day=1)
                first_day_of_prev_month = add_months(first_day_of_current_month, -1)
                last_day_of_prev_month = get_last_day(first_day_of_prev_month)
                eval_start = first_day_of_prev_month
                eval_end = last_day_of_prev_month
            else:
                # mid-month cutoff logic: previous completed cycle
                # Find the most recent cutoff that has passed
                if today_date.day > configured_penalty_day:
                    most_recent_cutoff = today_date.replace(day=configured_penalty_day)
                else:
                    most_recent_cutoff = add_months(
                        today_date.replace(day=configured_penalty_day), -1
                    )

                # previous completed cycle is one month before most_recent_cutoff
                last_cutoff = add_months(most_recent_cutoff, -1)
                prev_cutoff = add_months(last_cutoff, -1)
                eval_start = add_days(prev_cutoff, 1)
                eval_end = last_cutoff

        print(f"🎯 EVALUATION WINDOW:")
        print(f"   From Date: {eval_start}")
        print(f"   To Date: {eval_end}")
        print(f"   Total Days: {(eval_end - eval_start).days + 1}")

        # ─────────────────────────────────────────────
        # STEP 4: FETCH MISPUNCH ATTENDANCE RECORDS
        # ─────────────────────────────────────────────
        print("\n🔍 STEP 4: FETCHING MISPUNCH ATTENDANCE RECORDS")
        print("-" * 40)

        attendance_list = frappe.get_all(
            "Attendance",
            filters={
                "status": "Mispunch",
                "attendance_date": ["between", [eval_start, eval_end]],
                "docstatus": 1,
            },
            fields=["name", "employee", "attendance_date"],
        )

        print(f"📊 Total mispunch records found: {len(attendance_list)}")

        if not attendance_list:
            print(f"✅ No mispunch records found in the evaluation period")
            print("🎉 Process completed - no penalties needed")
            return

        # Show summary of mispunch records
        employee_mispunch_count = {}
        for att in attendance_list:
            emp = att.employee
            employee_mispunch_count[emp] = employee_mispunch_count.get(emp, 0) + 1

        print(f"📋 Mispunch summary by employee:")
        for emp, count in employee_mispunch_count.items():
            print(f"   - {emp}: {count} mispunch(es)")

        penalties_created = 0
        penalties_skipped = 0

        # ─────────────────────────────────────────────
        # STEP 5: PROCESS EACH MISPUNCH RECORD
        # ─────────────────────────────────────────────
        print(f"\n⚠️  STEP 5: PROCESSING {len(attendance_list)} MISPUNCH RECORDS")
        print("-" * 40)

        for att_idx, att in enumerate(attendance_list, 1):
            emp = att.employee
            att_id = att.name
            att_date = att.attendance_date

            print(f"\n⚠️  [{att_idx}/{len(attendance_list)}] Processing Mispunch:")
            print(f"   👤 Employee: {emp}")
            print(f"   📅 Attendance Date: {att_date}")
            print(f"   📄 Attendance ID: {att_id}")

            # Check if employee exists and is not relieved
            print(f"   🔍 Checking employee status...")
            emp_doc = frappe.db.get_value(
                "Employee", emp, ["name", "relieving_date"], as_dict=True
            )
            if not emp_doc:
                print(f"   ❌ SKIPPED: Invalid employee record")
                penalties_skipped += 1
                continue

            if emp_doc.relieving_date and getdate(emp_doc.relieving_date) < att_date:
                print(
                    f"   ⏭️  SKIPPED: Employee relieved ({emp_doc.relieving_date}) before mispunch date"
                )
                penalties_skipped += 1
                continue

            # Check penalty eligibility
            penalty_criteria_result = check_employee_penalty_criteria(
                emp, "For Attendance Mispunch"
            )
            print(f"   ✅ Penalty criteria check: {penalty_criteria_result}")

            if not penalty_criteria_result:
                print(f"   ⏭️  SKIPPED: Employee not eligible for penalty")
                penalties_skipped += 1
                continue

            # Step 1: Check if Employee Penalty exists on this date
            penalty_id = frappe.db.get_value(
                "Employee Penalty", {"employee": emp, "penalty_date": att_date}
            )

            if penalty_id:
                # Step 2: Check child table for reason = "Mispunch"
                reason_exists = frappe.db.exists(
                    "Employee Leave Penalty Details",
                    {"parent": penalty_id, "reason": "Mispunch"},
                )
                if reason_exists:
                    print(f"   🔍 Existing penalty for 'Mispunch' found: {penalty_id}")
                    print(f"   ⏭️  SKIPPED: Penalty already exists")
                    penalties_skipped += 1
                    continue
                else:
                    print(
                        f"   ✅ Penalty exists but not for 'Mispunch', continue processing"
                    )
            else:
                print(f"   ✅ No penalty found for this date")

            # Create penalty
            print(f"   🎯 CREATING MISPUNCH PENALTY")
            print(f"      📝 Employee: {emp}")
            print(f"      📅 Penalty Date: {att_date}")
            print(f"      📄 Attendance ID: {att_id}")
            print(f"      💰 Leave Deduction: {deduct_days}")

            try:
                penalty_id = create_employee_penalty(
                    employee=emp,
                    penalty_date=att_date,
                    deduct_leave=deduct_days,
                    attendance_id=att_id,
                    leave_balance_before_application=0.0,  # Will be calculated inside the method
                    leave_period_data=None,  # Will be fetched inside the method
                    leave_allocation_id=None,  # Will be determined inside the method
                    for_late_coming=0,
                    for_insufficient_hours=0,
                    for_no_attendance=0,
                    for_mispunch=1,
                )

                penalties_created += 1
                print(f"   ✅ PENALTY CREATED SUCCESSFULLY!")
                print(f"   📄 Penalty ID: {penalty_id}")
                print(f"   📊 Total penalties created so far: {penalties_created}")

            except Exception as penalty_error:
                print(f"   ❌ ERROR CREATING PENALTY: {str(penalty_error)}")
                penalties_skipped += 1
                frappe.log_error(
                    f"Error creating mispunch penalty for {emp}", str(penalty_error)
                )

        # ─────────────────────────────────────────────
        # FINAL SUMMARY
        # ─────────────────────────────────────────────
        print(f"\n" + "=" * 80)
        print(f"🎉 MISPUNCH PENALTY PROCESS COMPLETED!")
        print(f"📊 FINAL SUMMARY:")
        print(f"   - Total mispunch records found: {len(attendance_list)}")
        print(f"   - Penalties created: {penalties_created}")
        print(f"   - Records skipped: {penalties_skipped}")
        print(f"   - Unique employees with mispunch: {len(employee_mispunch_count)}")
        print(f"   - Evaluation period: {eval_start} to {eval_end}")
        print("=" * 80)

    except Exception as main_error:
        print(f"\n💥 CRITICAL ERROR IN MISPUNCH PENALTY PROCESS:")
        print(f"❌ Error: {str(main_error)}")
        print(f"📍 Traceback: {frappe.get_traceback()}")
        frappe.log_error(
            "Error in penalize_employee_for_attendance_mispunch_indifoss",
            frappe.get_traceback(),
        )


# ! HELPER FUNCTION TO NOTIFY HR IF PENALTY IS NOT CREATED DUE TO ATTENDANCE REGULARIZATION
# ? AT THE END OF THE SCHEDULER METHOD, THIS FUNCTION WILL NOTIFY ALL THE HR MANAGER AND HR USER ROLES IF THE PENALTY IS NOT CREATED DUE TO ATTENDANCE REGULARIZATION.
# ! EVERY SUCH ATTENDANCE WILL BE SENT IN A SINGLE MAIL
def notify_hr_if_non_creation_of_penalty_because_of_attendance_regularization(data):
    """
    NOTIFIES HR TEAM IF PENALTY WAS SKIPPED BECAUSE ATTENDANCE WAS REGULARIZED.

    @logic
    - THIS FUNCTION CHECKS IF THE PROVIDED ATTENDANCE RECORDS WERE SKIPPED FOR PENALTY
      DUE TO REGULARIZATION.
    - IF YES, THEN IT NOTIFIES ALL USERS WITH ROLE 'HR Manager' OR 'HR User'.
    - EMAILS ARE SENT WITH DETAILS OF SKIPPED RECORDS.

    @param data: LIST OF DICTIONARIES CONTAINING 'employee', 'attendance_date', 'attendance_id'
    @return: NONE
    """

    try:
        print(
            ">> ENTERED notify_hr_if_non_creation_of_penalty_because_of_attendance_regularization"
        )

        # ! IF NO DATA IS PASSED, EXIT IMMEDIATELY
        if not data:
            print(">> NO DATA RECEIVED — EXITING FUNCTION")
            return

        # ? FETCH USERS WHO HAVE HR ROLES ASSIGNED
        hr_roles = frappe.get_all(
            "Has Role",
            filters={"role": ["in", ["S - HR Manager", "S - HR Executive"]]},
            fields=["parent"],
        )
        print(f">> FOUND {len(hr_roles)} HR ROLE USERS")

        if not hr_roles:
            print(">> NO HR USERS FOUND — EXITING")
            return

        # ? EXTRACT HR USER EMAIL ADDRESSES
        hr_emails = frappe.get_all(
            "User",
            filters={"name": ["in", [i.parent for i in hr_roles]]},
            fields=["email"],
        )
        print(f">> FOUND {len(hr_emails)} USER EMAILS")

        if not hr_emails:
            print(">> NO EMAILS FOUND FOR HR USERS — EXITING")
            return

        # ? COMPILE LIST OF EMAILS (REMOVE ANY BLANKS)
        to_emails = [user.email for user in hr_emails if user.email]
        print(f">> VALID EMAILS: {to_emails}")

        if not to_emails:
            print(">> NO VALID EMAIL ADDRESSES — EXITING")
            return

        # ? COMPOSE EMAIL CONTENT WITH ATTENDANCE DETAILS INCLUDING LINKS TO ATTENDANCE DOCS
        content = """
        <p>Dear HR Team,</p>

        <p>The following attendance entries were <strong>excluded from penalty</strong> as the respective employees had their attendance regularized on these dates:</p>

        <ul>
        """
        url = frappe.utils.get_url()
        for record in data:
            att_id = record.get("attendance_id")
            emp = record.get("employee")
            att_date = record.get("attendance_date")

            print(f">> RECORD: {emp} — {att_date} — ATT_ID: {att_id}")

            link = f"/app/attendance/{att_id}"
            link = url + link if not link.startswith("http") else link
            content += f"<li><strong>Employee:</strong> {emp} — <strong>Date:</strong> {att_date} — <a href='{link}' target='_blank'>View Attendance</a></li>"

        content += """
        </ul>

        <p>Please review these entries to ensure the regularizations comply with policy. If any corrections are required, kindly take the necessary action.</p>

        <p>Regards,<br>
        ERPNext HR Automation</p>
        """

        # ? SEND EMAIL TO HR USERS AND MANAGERS
        print(">> SENDING EMAIL...")
        frappe.enqueue(
            method="frappe.core.doctype.communication.email.make",
            queue="short",
            timeout=300,
            now=False,
            recipients=to_emails,
            subject="Penalty Not Applied Due to Attendance Regularization",
            content=content,
            doctype=None,
            name=None,
            send_email=True,
        )

        print(">> EMAIL SENT SUCCESSFULLY")

    except Exception as e:
        print(">> EXCEPTION OCCURRED")
        frappe.log_error(
            frappe.get_traceback(),
            "Error in notify_hr_if_non_creation_of_penalty_because_of_attendance_regularization",
        )


# ! prompt_hr.scheduler_methods.penalization_for_no_attendance_for_indifoss

from datetime import timedelta
from frappe.utils import getdate, today, add_months, get_last_day
import frappe


@frappe.whitelist()
def penalization_for_no_attendance_for_indifoss(run_now=None):
    """
    Penalize employees for dates where there is:
    - No attendance
    - No leave application
    - No attendance regularization
    - No already created penalty
    - Not a holiday
    - Not before joining or after relieving

    For dates between (last month X + 1) to (this month X),
    where X is configured in HR Settings.
    """

    print("\n" + "=" * 80)
    print("🚀 STARTING NO ATTENDANCE PENALTY PROCESS")
    print("=" * 80)

    try:

        # ─────────────────────────────────────────────
        # STEP 1: VALIDATE EXECUTION DATE
        # ─────────────────────────────────────────────
        print("\n📅 STEP 1: VALIDATING EXECUTION DATE")
        print("-" * 40)

        penalty_day = int(
            frappe.db.get_single_value(
                "HR Settings", "custom_month_date_for_attendance_penalty_indifoss"
            )
        )
        import datetime
        from frappe.utils import now_datetime

        # ✅ FIX: Use actual current date instead of hardcoded date
        today_date = now_datetime().date()

        print(f"📅 Today's date: {today_date} (Day: {today_date.day})")
        print(f"📌 Configured penalty day: {penalty_day}")
        print(f"🎯 Expected execution day: {penalty_day + 1}")

        # ✅ Skip validation if manually triggered with run_now=1
        if not run_now and today_date.day != (penalty_day + 1):
            print("⏭️  SKIPPING: Not the penalty run day")
            return "Not penalty run day"

        if run_now:
            print("🧪 OVERRIDE ACTIVE: Forcing penalty run for previous cycle")

        print("✅ Execution date validated - proceeding with penalty process")

        # ─────────────────────────────────────────────
        # STEP 2: CALCULATE EVALUATION WINDOW (CYCLE BASED)
        # ─────────────────────────────────────────────
        print("\n📅 STEP 2: CALCULATING EVALUATION WINDOW (CYCLE BASED)")
        print("-" * 40)

        from frappe.utils import add_months, get_last_day, getdate
        from datetime import timedelta

        # ✅ FIX: Safely handle date replacement for short months
        import calendar

        def safe_replace_day(date_obj, target_day):
            """Safely replace day, handling months with fewer days"""
            max_day = calendar.monthrange(date_obj.year, date_obj.month)[1]
            actual_day = min(target_day, max_day)
            return date_obj.replace(day=actual_day)

        if run_now:
            # Force previous cycle window
            last_month = add_months(today_date, -1)
            prev_month = add_months(today_date, -2)
            eval_start = safe_replace_day(prev_month, penalty_day + 1)
            eval_end = safe_replace_day(last_month, penalty_day)
        else:
            # Standard logic
            if today_date.day > penalty_day:
                eval_start = safe_replace_day(
                    add_months(today_date, -1), penalty_day + 1
                )
                eval_end = safe_replace_day(today_date, penalty_day)
            else:
                last_month = add_months(today_date, -1)
                prev_month = add_months(today_date, -2)
                eval_start = safe_replace_day(prev_month, penalty_day + 1)
                eval_end = safe_replace_day(last_month, penalty_day)

        # Ensure dates are proper date objects
        eval_start = getdate(eval_start)
        eval_end = getdate(eval_end)

        print(f"🎯 EVALUATION WINDOW:")
        print(f"   From Date: {eval_start.strftime('%d %B %Y')}")
        print(f"   To Date: {eval_end.strftime('%d %B %Y')}")
        print(f"   Total Days: {(eval_end - eval_start).days + 1}")

        # ─────────────────────────────────────────────
        # STEP 3: FETCH EMPLOYEES
        # ─────────────────────────────────────────────
        print("\n👥 STEP 3: FETCHING ACTIVE EMPLOYEES")
        print("-" * 40)

        employees = frappe.get_all(
            "Employee", filters={"status": "Active"}, pluck="name"
        )
        if not employees:
            print("❌ No active employees found")
            return "No active employees found."

        print(f"✅ Total active employees found: {len(employees)}")

        emp_info = frappe.get_all(
            "Employee",
            filters={"name": ["in", employees]},
            fields=["name", "holiday_list", "date_of_joining", "relieving_date"],
        )

        # ─────────────────────────────────────────────
        # STEP 4: BUILD DATA MAPS
        # ─────────────────────────────────────────────
        print("\n📊 STEP 4: BUILDING DATA MAPS")
        print("-" * 40)

        print("   🔍 Building holiday map...")
        holiday_map, doj_map, dor_map = {}, {}, {}
        for emp in emp_info:
            doj_map[emp.name] = emp.date_of_joining
            dor_map[emp.name] = emp.relieving_date
            if not emp.holiday_list:
                continue
            holidays = frappe.get_all(
                "Holiday",
                filters={
                    "holiday_date": ["between", [eval_start, eval_end]],
                    "parent": emp.holiday_list,
                },
                pluck="holiday_date",
            )
            holiday_map[emp.name] = set(holidays)
        print(f"      ✅ Holiday data loaded for employees with holiday lists")

        print("   🔍 Building attendance map...")
        att_map, leave_map, reg_map, penalty_map, att_id_map = {}, {}, {}, {}, {}

        attendance_list = frappe.get_all(
            "Attendance",
            filters={
                "attendance_date": ["between", [eval_start, eval_end]],
                "employee": ["in", employees],
                "docstatus": 1,
            },
            fields=["name", "employee", "attendance_date"],
        )
        for a in attendance_list:
            att_map.setdefault(a.employee, set()).add(a.attendance_date)
            att_id_map.setdefault(a.employee, {})[a.attendance_date] = a.name
        print(f"      ✅ Attendance records loaded: {len(attendance_list)}")

        print("   🔍 Building leave map...")
        leave_list = frappe.db.sql(
            """
            SELECT employee, from_date, to_date
            FROM `tabLeave Application`
            WHERE docstatus = 1 AND employee IN %(employees)s
            AND (from_date <= %(end)s AND to_date >= %(start)s)
        """,
            {"employees": employees, "start": eval_start, "end": eval_end},
            as_dict=True,
        )
        for l in leave_list:
            # ✅ FIX: Added helper function inline
            for d in get_daterange_overlap(
                getdate(l.from_date), getdate(l.to_date), eval_start, eval_end
            ):
                leave_map.setdefault(l.employee, set()).add(d)
        print(f"      ✅ Leave applications loaded: {len(leave_list)}")

        print("   🔍 Building regularization map...")
        reg_list = frappe.get_all(
            "Attendance Regularization",
            filters={
                "regularization_date": ["between", [eval_start, eval_end]],
                "employee": ["in", employees],
                "docstatus": 1,
            },
            fields=["employee", "regularization_date"],
        )
        for r in reg_list:
            reg_map.setdefault(r.employee, set()).add(r.regularization_date)
        print(f"      ✅ Regularizations loaded: {len(reg_list)}")

        print("   🔍 Building existing penalty map...")
        penalty_list = frappe.get_all(
            "Employee Penalty",
            filters={
                "penalty_date": ["between", [eval_start, eval_end]],
                "employee": ["in", employees],
                "docstatus": ["<", 2],
            },
            fields=["employee", "penalty_date"],
        )
        for p in penalty_list:
            penalty_map.setdefault(p.employee, set()).add(p.penalty_date)
        print(f"      ✅ Existing penalties loaded: {len(penalty_list)}")

        # ─────────────────────────────────────────────
        # STEP 5: IDENTIFY MISSING ATTENDANCE
        # ─────────────────────────────────────────────
        print("\n🔍 STEP 5: IDENTIFYING MISSING ATTENDANCE")
        print("-" * 40)

        missing_map = {}
        total_missing_days = 0

        for emp_idx, emp in enumerate(employees, 1):
            try:
                if emp_idx % 50 == 0:
                    print(
                        f"   📊 Progress: {emp_idx}/{len(employees)} employees processed"
                    )

                missing_days = {}
                d = eval_start
                while d <= eval_end:
                    if (
                        d not in att_map.get(emp, set())
                        and d not in leave_map.get(emp, set())
                        and d not in reg_map.get(emp, set())
                        and d not in penalty_map.get(emp, set())
                        and d not in holiday_map.get(emp, set())
                        and (not doj_map.get(emp) or d >= getdate(doj_map[emp]))
                        and (not dor_map.get(emp) or d <= getdate(dor_map[emp]))
                    ):
                        missing_days[str(d)] = att_id_map.get(emp, {}).get(d)
                        total_missing_days += 1
                    d += timedelta(days=1)
                if missing_days:
                    missing_map[emp] = missing_days

            except Exception as e:
                print(f"❌ Error processing employee {emp}: {e}")
                frappe.log_error(
                    title=f"Error in Attendance Penalization for {emp}",
                    message=f"""
                    Error: {str(e)}

                    Employee: {emp}
                    Date Range: {eval_start} → {eval_end}
                    DOJ: {doj_map.get(emp)}
                    DOR: {dor_map.get(emp)}
                    Holidays: {holiday_map.get(emp, set())}
                    Attendance: {att_map.get(emp, set())}
                    Leaves: {leave_map.get(emp, set())}
                    Regularizations: {reg_map.get(emp, set())}
                    Penalties: {penalty_map.get(emp, set())}
                    """,
                )

            # 🧩 SPECIAL DEBUG LOG FOR HARISH RATHOR
            if emp == "002: Harish Rathor":
                frappe.log_error(
                    title="DEBUG: Full Data Dump for 002 - Harish Rathor",
                    message=f"""
                    Employee: {emp}
                    Date Range: {eval_start} → {eval_end}
                    DOJ: {doj_map.get(emp)}
                    DOR: {dor_map.get(emp)}
                    Holidays: {holiday_map.get(emp, set())}
                    Attendance: {att_map.get(emp, set())}
                    Leaves: {leave_map.get(emp, set())}
                    Regularizations: {reg_map.get(emp, set())}
                    Existing Penalties: {penalty_map.get(emp, set())}
                    Missing Days Identified: {missing_days if missing_days else 'None'}
                    """,
                )

        print(
            f"\n📊 Summary: Found {total_missing_days} missing attendance days across {len(missing_map)} employees"
        )

        # ─────────────────────────────────────────────
        # STEP 6: APPLY PENALTIES
        # ─────────────────────────────────────────────
        print(f"\n⚠️  STEP 6: APPLYING PENALTIES FOR MISSING ATTENDANCE")
        print("-" * 40)

        return apply_penalty_for_no_attendance_indifoss(missing_map)

    except Exception as main_error:
        print(f"\n💥 CRITICAL ERROR IN NO ATTENDANCE PENALTY PROCESS:")
        print(f"❌ Error: {str(main_error)}")
        print(f"📍 Traceback: {frappe.get_traceback()}")
        frappe.log_error(
            "Error in penalization_for_no_attendance_for_indifoss",
            frappe.get_traceback(),
        )
        return "Error"


# ✅ HELPER FUNCTION: Generate date range with overlap
def get_daterange_overlap(start_date, end_date, window_start, window_end):
    """
    Generate dates that overlap between [start_date, end_date] and [window_start, window_end]
    """
    from datetime import timedelta
    from frappe.utils import getdate

    # Ensure we work with date objects
    start_date = getdate(start_date)
    end_date = getdate(end_date)
    window_start = getdate(window_start)
    window_end = getdate(window_end)

    # Find actual overlap
    actual_start = max(start_date, window_start)
    actual_end = min(end_date, window_end)

    # Generate dates
    dates = []
    current = actual_start
    while current <= actual_end:
        dates.append(current)
        current += timedelta(days=1)

    return dates


@frappe.whitelist()
def apply_penalty_for_no_attendance_indifoss(missing_attendance_map=None):
    """
    Apply penalties for employees with missing attendance.
    Configuration is handled by create_employee_penalty method.
    """

    print("\n📋 APPLYING NO ATTENDANCE PENALTIES")
    print("-" * 40)

    try:
        import json
        from prompt_hr.py.utils import get_indifoss_company_name

        if isinstance(missing_attendance_map, str):
            missing_attendance_map = json.loads(missing_attendance_map)

        if not missing_attendance_map:
            print("✅ No missing attendance data to process")
            return "No missing attendance data."

        print(
            f"📊 Processing missing attendance for {len(missing_attendance_map)} employees"
        )

        # ─────────────────────────────────────────────
        # FETCH COMPANY CONFIGURATION
        # ─────────────────────────────────────────────
        print("🏢 Fetching company configuration...")
        company = get_indifoss_company_name().get("company_name")

        if not company:
            print("❌ ERROR: Indifoss company not found")
            frappe.log_error(
                "Indifoss company not found", "apply_penalty_for_no_attendance_indifoss"
            )
            return "Company not configured"

        print(f"✅ Company: {company}")

        # Default deduction amount - actual configuration will be handled by create_employee_penalty method
        deduct_days = 1.0  # This will be overridden by the penalty configuration
        print(
            f"✅ Default leave deduction: {deduct_days} (actual amount determined by penalty configuration)"
        )

        penalties_created = 0
        penalties_skipped = 0
        attendance_created = 0

        # ─────────────────────────────────────────────
        # PROCESS EACH EMPLOYEE'S MISSING DAYS
        # ─────────────────────────────────────────────
        total_days_to_process = sum(
            len(days) for days in missing_attendance_map.values()
        )
        processed_days = 0

        print(f"📊 Total missing days to process: {total_days_to_process}")

        for emp_idx, (emp, date_map) in enumerate(missing_attendance_map.items(), 1):
            print(
                f"\n👤 [{emp_idx}/{len(missing_attendance_map)}] Processing Employee: {emp}"
            )
            print(f"   📅 Missing attendance days: {len(date_map)}")

            emp_penalties_created = 0
            emp_penalties_skipped = 0
            emp_attendance_created = 0

            for day_idx, (date_str, existing_att_id) in enumerate(date_map.items(), 1):
                date_obj = getdate(date_str)
                processed_days += 1

                print(
                    f"      📅 [{day_idx}/{len(date_map)}] Processing date: {date_str}"
                )

                # Check if penalty already exists (double-check)
                if frappe.db.exists(
                    "Employee Penalty", {"employee": emp, "penalty_date": date_obj}
                ):
                    print(f"         ⏭️  SKIPPED: Penalty already exists")
                    penalties_skipped += 1
                    emp_penalties_skipped += 1
                    continue

                # Check penalty eligibility
                penalty_criteria_result = check_employee_penalty_criteria(
                    emp, "For No Attendance"
                )
                print(f"         ✅ Penalty criteria check: {penalty_criteria_result}")

                if not penalty_criteria_result:
                    print(f"         ⏭️  SKIPPED: Employee not eligible for penalty")
                    penalties_skipped += 1
                    emp_penalties_skipped += 1
                    continue

                # Create absent attendance if not exists
                if not existing_att_id:
                    print(f"         📝 Creating absent attendance record...")
                    try:
                        att_doc = frappe.get_doc(
                            {
                                "doctype": "Attendance",
                                "employee": emp,
                                "attendance_date": date_obj,
                                "status": "Absent",
                                "working_hours": 0,
                                "company": company,
                                "check_in": None,
                                "check_out": None,
                            }
                        )

                        att_doc.insert()
                        att_doc.submit()
                        existing_att_id = att_doc.name
                        attendance_created += 1
                        emp_attendance_created += 1
                        print(f"         ✅ Attendance created: {existing_att_id}")

                    except Exception as att_error:
                        print(
                            f"         ❌ ERROR creating attendance: {str(att_error)}"
                        )
                        penalties_skipped += 1
                        emp_penalties_skipped += 1
                        continue
                else:
                    print(f"         📄 Using existing attendance: {existing_att_id}")

                # Create penalty
                print(f"         🎯 CREATING NO ATTENDANCE PENALTY")
                print(f"            📝 Employee: {emp}")
                print(f"            📅 Penalty Date: {date_obj}")
                print(f"            📄 Attendance ID: {existing_att_id}")
                print(f"            💰 Leave Deduction: {deduct_days}")

                try:
                    penalty_id = create_employee_penalty(
                        employee=emp,
                        penalty_date=date_obj,
                        deduct_leave=deduct_days,
                        attendance_id=existing_att_id,
                        leave_balance_before_application=0.0,  # Will be calculated inside the method
                        leave_period_data=None,  # Will be fetched inside the method
                        leave_allocation_id=None,  # Will be determined inside the method
                        for_late_coming=0,
                        for_insufficient_hours=0,
                        for_no_attendance=1,
                        for_mispunch=0,
                    )

                    # Link penalty in Attendance
                    frappe.db.set_value(
                        "Attendance",
                        existing_att_id,
                        "custom_employee_penalty_id",
                        penalty_id,
                    )

                    penalties_created += 1
                    emp_penalties_created += 1
                    print(f"         ✅ PENALTY CREATED SUCCESSFULLY!")
                    print(f"         📄 Penalty ID: {penalty_id}")

                except Exception as penalty_error:
                    print(f"         ❌ ERROR CREATING PENALTY: {str(penalty_error)}")
                    penalties_skipped += 1
                    emp_penalties_skipped += 1
                    frappe.log_error(
                        f"Error creating no attendance penalty for {emp}",
                        str(penalty_error),
                    )

                # Progress indicator for large datasets
                if processed_days % 100 == 0:
                    print(
                        f"   📊 Progress: {processed_days}/{total_days_to_process} days processed"
                    )

            print(f"   📊 Employee {emp} Summary:")
            print(f"      - Penalties created: {emp_penalties_created}")
            print(f"      - Penalties skipped: {emp_penalties_skipped}")
            print(f"      - Attendance records created: {emp_attendance_created}")

        # ─────────────────────────────────────────────
        # FINAL SUMMARY
        # ─────────────────────────────────────────────
        print(f"\n" + "=" * 60)
        print(f"🎉 NO ATTENDANCE PENALTY APPLICATION COMPLETED!")
        print(f"📊 FINAL SUMMARY:")
        print(f"   - Total employees processed: {len(missing_attendance_map)}")
        print(f"   - Total missing days processed: {total_days_to_process}")
        print(f"   - Penalties created: {penalties_created}")
        print(f"   - Penalties skipped: {penalties_skipped}")
        print(f"   - Attendance records created: {attendance_created}")
        print("=" * 60)

        return "Penalties created."

    except Exception as apply_error:
        print(f"\n💥 CRITICAL ERROR IN PENALTY APPLICATION:")
        print(f"❌ Error: {str(apply_error)}")
        print(f"📍 Traceback: {frappe.get_traceback()}")
        frappe.log_error(
            "Error in apply_penalty_for_no_attendance_indifoss", frappe.get_traceback()
        )
        return "Error"


@frappe.whitelist()
def run_all_indifoss_penalties(run_now=None):
    """
    RUN ALL PENALTY METHODS FOR INDIFOSS IN THIS ORDER:
    1. No Attendance
    2. Mispunch
    3. Late Entry
    4. Incomplete Week
    """

    try:
        penalization_for_no_attendance_for_indifoss(run_now=run_now)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error: No Attendance Penalty Failed")

    try:
        penalize_employee_for_attendance_mispunch_indifoss(run_now=run_now)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error: Mispunch Penalty Failed")

    try:
        penalize_employee_for_late_entry_for_indifoss(run_now=run_now)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error: Late Entry Penalty Failed")

    try:
        penalize_incomplete_week_for_indifoss(run_now=run_now)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(), "Error: Incomplete Week Penalty Failed"
        )


def get_leave_allocation_id(employee, leave_type, attendance_date):
    """
    RETURN THE LEAVE ALLOCATION ID FOR THE EMPLOYEE, LEAVE TYPE, AND DATE.
    """
    allocation = frappe.get_value(
        "Leave Allocation",
        {
            "employee": employee,
            "leave_type": leave_type,
            "from_date": ["<=", attendance_date],
            "to_date": [">=", attendance_date],
            "docstatus": 1,
        },
        "name",
    )
    return allocation

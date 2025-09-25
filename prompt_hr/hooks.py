app_name = "prompt_hr"
app_title = "Prompt HR"
app_publisher = "Jignasha Chavda"
app_description = "Prompt HR"
app_email = "jignasha@sanskartechnolab.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "prompt_hr",
# 		"logo": "/assets/prompt_hr/logo.png",
# 		"title": "Prompt HR",
# 		"route": "/prompt_hr",
# 		"has_permission": "prompt_hr.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/prompt_hr/css/prompt_hr.css"
app_include_js = [
    "assets/prompt_hr/js/web_form_redirect.js",
    "assets/prompt_hr/js/utils.js",
    "assets/prompt_hr/js/frappe/form/workflow.js",
    "assets/prompt_hr/js/employee_leave_balance.js",
    "assets/prompt_hr/js/employee_leave_balance_summary.js"
]


# include js, css files in header of web template
# web_include_css = "/assets/prompt_hr/css/prompt_hr.css"
# web_include_js = "/assets/prompt_hr/js/prompt_hr.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "prompt_hr/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Salary Structure Assignment": "public/js/salary_structure_assignment.js",
    "Employee Onboarding": "public/js/employee_onboarding.js",
    "Job Offer": "public/js/job_offer.js",
    "Job Requisition": "public/js/job_requisition.js",
    "Job Opening": "public/js/job_opening.js",
    "Employee": "public/js/employee.js",
    "Job Applicant": "public/js/job_applicant.js",
    "Appointment Letter": "public/js/appointment_letter.js",
    "Interview": "public/js/interview.js",
    "Interview Feedback": "public/js/interview_feedback.js",
    "Interview Round": "public/js/interview_round.js",
    "Attendance": "public/js/attendance.js",
    "Attendance Request": "public/js/attendance_request.js",
    "Payroll Entry": "public/js/payroll_entry.js",
    "Leave Application": "public/js/leave_application.js",
    "Employee Checkin": "public/js/employee_checkin.js",
    "HR Settings": "public/js/hr_settings.js",
    "Expense Claim": "public/js/expense_claim.js",
    "Full and Final Statement": "public/js/full_and_final_statement.js",
    "Loan Application": "public/js/loan_application.js",
    "Exit Interview": "public/js/exit_interview.js",
    "Travel Request": "public/js/travel_request.js",
    "Leave Allocation": "public/js/leave_allocation.js",
    "Leave Policy Assignment": "public/js/leave_policy_assignment.js",
    "Salary Slip": "public/js/salary_slip.js",
    "Compensatory Leave Request": "public/js/compensatory_leave_request.js",
    "Shift Request": "public/js/shift_request.js"
}

doctype_list_js = {
    "Job Applicant": "public/js/job_applicant_list.js",
    "Attendance": "public/js/attendance_list.js",
    "Leave Application": "public/js/leave_application_list.js",
    "Employee Checkin": "public/js/employee_checkin_list.js",
    "Shift Request": "public/js/shift_request_list.js",
    "Attendance Request": "public/js/attendance_request_list.js",
    "Compensatory Leave Request": "public/js/compensatory_leave_request_list.js",
    "Loan Application": "public/js/loan_application_list.js",
    "Job Requisition": "public/js/job_requisition_list.js",
    "Travel Request": "public/js/travel_request_list.js",
    "Expense Claim": "public/js/expense_claim_list.js",
}

# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
doctype_calendar_js = {"Attendance" : "public/js/attendance_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "prompt_hr/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "prompt_hr.utils.jinja_methods",
# 	"filters": "prompt_hr.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "prompt_hr.install.before_install"
# after_install = "prompt_hr.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "prompt_hr.uninstall.before_uninstall"
# after_uninstall = "prompt_hr.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "prompt_hr.utils.before_app_install"
# after_app_install = "prompt_hr.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "prompt_hr.utils.before_app_uninstall"
# after_app_uninstall = "prompt_hr.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "prompt_hr.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Interview": "prompt_hr.py.interview_availability.check_interviewer_permission",
    "Interview Feedback": "prompt_hr.py.interview_feedback.get_permission_query_conditions",
    "Job Opening": "prompt_hr.py.job_opening.get_permission_query_conditions",
    "Salary Slip": "prompt_hr.py.salary_slip.salary_slip_view_and_access_permissions"
}

# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    # "ToDo": "custom_app.overrides.CustomToDo"
    "Interview": "prompt_hr.overrides.interview_override.CustomInterview",
    "Job Offer": "prompt_hr.overrides.job_offer_override.CustomJobOffer",
    "Attendance Request": "prompt_hr.overrides.attendance_request_override.CustomAttendanceRequest",
    "Salary Slip": "prompt_hr.overrides.salary_slip_override.CustomSalarySlip",
    "Attendance": "prompt_hr.overrides.attendance_override.CustomAttendance",
    "Leave Policy Assignment": "prompt_hr.overrides.leave_policy_assignment_override.CustomLeavePolicyAssignment",
    "Payroll Entry": "prompt_hr.overrides.payroll_entry_override.CustomPayrollEntry",
    "Compensatory Leave Request": "prompt_hr.overrides.compensatory_leave_request_override.CustomCompensatoryLeaveRequest",
    'Process Loan Interest Accrual': 'prompt_hr.overrides.process_loan_interest_accrual_override.CustomProcessLoanInterestAccrual',
    "Leave Encashment": "prompt_hr.overrides.leave_encashment_override.CustomLeaveEncashment",
    "Leave Application": "prompt_hr.overrides.leave_application_override.CustomLeaveApplication",
    "Shift Request": "prompt_hr.overrides.shift_request_override.CustomShiftRequest"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Employee Onboarding": {
        "validate": "prompt_hr.py.employee_onboarding.validate",
        "after_insert": "prompt_hr.py.employee_onboarding.after_insert",
    },
    "Job Requisition": {
        "validate": [
            "prompt_hr.py.job_requisition.add_or_update_custom_last_updated_by",
            "prompt_hr.py.job_requisition.set_requested_by",
        ],
        "on_update": [
            "prompt_hr.py.job_requisition.on_update",
            "prompt_hr.py.job_requisition.notify_approver",
        ],
        # "after_insert": "prompt_hr.py.job_requisition.after_insert",
    },
    "Job Applicant": {
        "after_insert": "prompt_hr.py.job_applicant.after_insert",
        "before_insert": "prompt_hr.py.job_applicant.before_insert",
    },
    "Interview": {
        "validate": "prompt_hr.custom_methods.update_job_applicant_status_based_on_interview",
        "on_submit": "prompt_hr.custom_methods.update_job_applicant_status_based_on_interview",
        "on_update": "prompt_hr.py.interview_availability.on_update",
        "before_save": "prompt_hr.py.interview.before_save",
    },
    "Job Offer": {
        "validate": "prompt_hr.custom_methods.update_job_applicant_status_based_on_job_offer",
        "after_insert": "prompt_hr.py.job_offer.after_insert",
        "on_submit": "prompt_hr.custom_methods.update_job_applicant_status_based_on_job_offer",
    },
    "Employee": {
        "onload": "prompt_hr.py.employee.onload",
        "on_update": "prompt_hr.py.employee.on_update",
        "autoname": "prompt_hr.py.employee.custom_autoname_employee",
        "validate": "prompt_hr.py.employee.validate",
        "before_insert": "prompt_hr.py.employee.before_insert",
        "after_insert": "prompt_hr.py.employee.after_insert",
        "before_save": "prompt_hr.py.employee.before_save",
    },
    # "Probation Feedback Form": {
    #     "on_submit": "prompt_hr.custom_methods.add_probation_feedback_data_to_employee"
    # },
    "LMS Quiz Submission": {
        "validate": "prompt_hr.py.lms_quiz_submission.update_status"
    },
    "User": {
        "before_save": "prompt_hr.py.user.before_save"
    },
    "Interview Feedback": {
        "on_submit": "prompt_hr.py.interview_feedback.on_submit",
        "on_update": "prompt_hr.py.interview_feedback.on_update",
    },
    # "User": {
    #     "after_insert": "prompt_hr.py.welcome_status.after_insert"
    # },
    "Attendance Request": {
        "after_insert": "prompt_hr.py.attendance_request.notify_reporting_manager",
        "validate": [
            "prompt_hr.py.attendance_request.notify_reporting_manager",
            "prompt_hr.py.attendance_request.validate",
            "prompt_hr.py.attendance_request.is_valid_for_partial_day",
        ],
        "before_submit": "prompt_hr.py.attendance_request.before_submit",
        "on_update": "prompt_hr.py.attendance_request.on_update",
    },
    "Payroll Entry": {
        "on_update": "prompt_hr.py.payroll_entry.on_update",
        "on_submit": "prompt_hr.py.payroll_entry.on_submit",
        
    },
    "Leave Allocation": {
        "before_validate": "prompt_hr.py.leave_allocation.before_validate",
        "before_submit": "prompt_hr.py.leave_allocation.before_submit"
    },
    "Additional Salary": {"before_save": "prompt_hr.py.additional_salary.before_save"},
    "Leave Encashment": {
        "before_save": "prompt_hr.py.leave_encashment.before_save",
    },
    "Additional Salary": {"before_save": "prompt_hr.py.additional_salary.before_save"},
    "Job Opening": {"before_insert": "prompt_hr.py.job_opening.before_insert"},
    "Leave Application": {
        "on_update": "prompt_hr.py.leave_application.on_update",
        "on_cancel": "prompt_hr.py.leave_application.on_cancel",
        "before_save": "prompt_hr.py.leave_application.before_save",
        "before_insert": "prompt_hr.py.leave_application.before_insert",
        "before_validate": "prompt_hr.py.leave_application.before_validate",
        "validate": "prompt_hr.py.leave_application.validate",
        "before_submit": "prompt_hr.py.leave_application.before_submit",
        "on_submit": "prompt_hr.py.leave_application.on_submit"
    },
    "Expense Claim": {
        "before_save": "prompt_hr.py.expense_claim.before_save",
        "on_update": "prompt_hr.py.expense_claim.on_update",
        "before_submit": "prompt_hr.py.expense_claim.before_submit",
        "on_cancel": "prompt_hr.py.expense_claim.update_amount_in_marketing_planning",
    },
    "Employee Tax Exemption Declaration": {
        "before_save": "prompt_hr.py.income_tax_computation.before_save",
        "on_submit": "prompt_hr.py.income_tax_computation.on_submit"
    },
    "Full and Final Statement": {
        "on_update": "prompt_hr.py.full_and_final_statement.on_update",
        "before_submit": "prompt_hr.py.full_and_final_statement.before_submit",
        "before_insert": "prompt_hr.py.full_and_final_statement.before_insert",
        "on_submit": "prompt_hr.py.full_and_final_statement.on_submit"
    },
    "Travel Request": {
        "on_update": "prompt_hr.py.travel_request.on_update",
        "before_save":"prompt_hr.py.travel_request.before_save"
    },
    "Loan Application": {
        "on_update": "prompt_hr.py.loan_application.on_update",
        "on_cancel": "prompt_hr.py.loan_application.on_cancel",
    },
    "Salary Slip": {
        "on_submit": "prompt_hr.py.salary_slip.loan_repayment_amount",
        "on_update": "prompt_hr.py.salary_slip.update_loan_principal_amount",
        "on_cancel": "prompt_hr.py.salary_slip.cancel_loan_repayment_amount",
        "before_validate": "prompt_hr.py.salary_slip.before_validate",
    },
    "Salary Structure Assignment": {
        "on_submit": "prompt_hr.py.salary_structure_assignment.update_employee_ctc",
        "before_save": "prompt_hr.py.salary_structure_assignment.update_arrear_details",
        "on_cancel": "prompt_hr.py.salary_structure_assignment.on_cancel",
    },
    "Appointment Letter": {
        "before_save": "prompt_hr.py.appointment_letter.before_save",
    },
    "Appraisal": {
        "before_save": "prompt_hr.py.appraisal_letter.before_save",
    },
    "Leave Type": {
        "on_update": "prompt_hr.py.leave_type.on_update",
    },
    "Employee Separation": {
        "before_save": "prompt_hr.py.employee_separation.before_save"
    },
    "Income Tax Slab": {
        "validate": "prompt_hr.py.income_tax_slab.validate",
    },
    "Employee Checkin": {
        "before_insert": "prompt_hr.py.employee_checkin.before_insert"
    },
    "HR Settings":{
        "before_save": "prompt_hr.py.hr_settings.set_employee_field_names"
    },
    "Notification Log": {
        "after_insert": "prompt_hr.api.mobile.firebase.push_notification_handler"
    }
}

on_logout = "prompt_hr.api.mobile.firebase.clear_token_for_user"

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        "50 23 * * *": [
            "prompt_hr.py.employee.update_employee_status_for_prompt_company"
        ],
        "0 20 * * *": [
            "prompt_hr.py.employee.update_employee_status_for_indifoss_company"
        ],
        # "0 8 * * *":[
        #     "prompt_hr.scheduler_methods.send_attendance_issue"
        # ],
        "0 1 * * *": [
            "prompt_hr.scheduler_methods.auto_attendance"
        ],
        "0 2 * * *": [
            "prompt_hr.py.attendance_penalty_api.auto_approve_scheduler"
        ],
        "0 3 * * *": [
            "prompt_hr.py.attendance_penalty_api.prompt_employee_attendance_penalties"
        ],
        "0 4 * * *": [
            "prompt_hr.py.attendance_penalty_api.send_penalty_notification_emails"
        ],
    },
    "daily": [
        "prompt_hr.py.employee_changes_approval.daily_check_employee_changes_approval",
        "prompt_hr.scheduler_methods.create_probation_feedback_form",
        "prompt_hr.scheduler_methods.create_confirmation_evaluation_form_for_prompt",
        "prompt_hr.scheduler_methods.inform_employee_for_confirmation_process",
        "prompt_hr.scheduler_methods.validate_employee_holiday_list",
        # "prompt_hr.scheduler_methods.assign_checkin_role",
        "prompt_hr.scheduler_methods.process_exit_approvals",
        "prompt_hr.scheduler_methods.daily_attendance_request_rituals",
    ],
}

# Testing
# -------

# before_tests = "prompt_hr.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
"hrms.hr.doctype.leave_application.leave_application.get_holidays": "prompt_hr.py.leave_application.get_holidays"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "prompt_hr.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["prompt_hr.utils.before_request"]
# after_request = ["prompt_hr.utils.after_request"]

# Job Events
# ----------
# before_job = ["prompt_hr.utils.before_job"]
# after_job = ["prompt_hr.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"prompt_hr.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    # {
    #     "dt": "Kanban Board",
    #     "filters": [
    #         [
    #             "name",
    #             "in",
    #             [
    #                 "Meetings",
    #             ],
    #         ]
    #     ],
    # },
    # {"dt":"Notification","filters":[
    #     [
    #         "module","in",[
    #             "Prompt HR"
    #         ]
    #     ]
    # ]},
    # {"dt":"Custom Field","filters":[
    #     [
    #         "module","in",[
    #             "Prompt HR"
    #         ]
    #     ]
    # ]},
    # {"dt":"Property Setter","filters":[
    #     [
    #         "module","in",[
    #             "Prompt HR"
    #         ]
    #     ]
    # ]},
    # {"dt":"Client Script","filters":[
    #     [
    #         "module","in",[
    #             "Prompt HR"
    #         ]
    #     ]
    # ]},
    # {"dt":"Server Script","filters":[
    #     [
    #         "module","in",[
    #             "Prompt HR"
    #         ]
    #     ]
    # ]},
    # {"dt":"Print Format","filters":[
    #     [
    #         "module","in",[
    #             "Prompt HR"
    #         ]
    #     ]
    # ]},
    # {
    #     "dt":"Role", "filters": [["name", "in", ["Job Requisition", "Head of Department", "Managing Director", "S - Payroll Accounting", "Travel Desk User", "Reporting Manager", "IT User", "Admin User"]]]
    # },
    # {
    #     "dt":"Workflow", "filters": [["name", "in", ["Job Requisition","Loan Application", "Compensatory Leave Request", "Leave Application", "Expense Claim", "Travel Request", "Shift Request", "WeekOff Change Request", "Attendance Regularization", "Attendance Request"]]]
    # },
    # {
    #     "dt":"Workflow State", "filters": [["name", "in", ["Approved by HOD", "Pending", "Rejected by HOD", "Approved by Director", "Rejected by Director", "Cancelled", "On-Hold", "Filled", "Confirmed", "Approved by HR", "Rejected by HR", "Approved by BU Head", "Rejected by BU Head", "Extension Approved", "Extension Confirmed", "Extension Rejected", "Extension Requested", "Send For Approval", "Pending For Approval"]]]
    # },
    # {
    #     "dt":"Workflow Action Master", "filters": [["name", "in", ["Confirm", "Send For Approval"]]]
    # },
    # {
    #     "doctype": "Type of Document",
    #     "filters": {
    #         "name": ["in", [
    #             "Proof of Work Experience",
    #             "Proof of Identity",
    #             "Proof of Address",
    #             "Proof of Qualification"
    #         ]]
    #     }
    # },
    # {
    #     "doctype": "Workspace",
    #     "filters": {
    #         "name": ["in", [
    #             "Employee ESS",
    #             "Leaves",
    #             "Shift & Attendance",
    #             "HR"
    #         ]]
    #     }
    # },
    # {
    #     "doctype": "Number Card",
    #     "filters": {
    #         "name": ["in", [
    #             "Leave Application - Pending Approval",
    #             "Attendance Regularization - Pending Approval",
    #             "Attendance Request - Pending Approval",
    #             "Shift Request - Pending Approval",
    #             "WeekOff Change Request - Pending Approval",
    #             "Leave Application - Approved/Rejected by RM",
    #         ]]
    #     }
    # }
]

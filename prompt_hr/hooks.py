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
                    # "assets/prompt_hr/js/welcome_page_check.js",
                    "assets/prompt_hr/js/frappe/form/workflow.js",
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
    "Employee Onboarding": "public/js/employee_onboarding.js",
    "Job Offer": "public/js/job_offer.js",
    # "Job Requisition": "public/js/job_requisition.js",
    "Job Opening": "public/js/job_opening.js",
    'Employee': 'public/js/employee.js',
    "Job Applicant": "public/js/job_applicant.js",
    'Appointment Letter': 'public/js/appointment_letter.js',
    "Interview": "public/js/interview.js",
    "Interview Feedback": "public/js/interview_feedback.js",
    "Interview Round": "public/js/interview_round.js",
    "Attendance": "public/js/attendance.js",
    "Attendance Request": "public/js/attendance_request.js",
    "Payroll Entry": "public/js/payroll_entry.js",
    "Leave Application": "public/js/leave_application.js",
    "Employee Checkin": "public/js/employee_checkin.js"

}

doctype_list_js = {
    "Job Applicant": "public/js/job_applicant_list.js",
}

# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

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
        
        "on_update": [ "prompt_hr.py.job_requisition.on_update", 
                        "prompt_hr.py.job_requisition.notify_approver",
                    ],
        "after_insert": "prompt_hr.py.job_requisition.after_insert",        
    },
    "Job Applicant": {
        "after_insert": "prompt_hr.py.job_applicant.after_insert",
        "before_insert": "prompt_hr.py.job_applicant.before_insert",
    },
    "Interview": {
        "validate": "prompt_hr.custom_methods.update_job_applicant_status_based_on_interview",
        "on_submit": "prompt_hr.custom_methods.update_job_applicant_status_based_on_interview",
        "on_update": "prompt_hr.py.interview_availability.on_update",
    },
    "Job Offer": {
        "validate": "prompt_hr.custom_methods.update_job_applicant_status_based_on_job_offer",
        "after_insert": "prompt_hr.py.job_offer.after_insert",
        "on_submit": "prompt_hr.custom_methods.update_job_applicant_status_based_on_job_offer",
    },
    "Employee": {
#         "on_update": "prompt_hr.py.employee.on_update",
        "validate": "prompt_hr.py.employee.validate",
    },
    # "Probation Feedback Form": {
    #     "on_submit": "prompt_hr.custom_methods.add_probation_feedback_data_to_employee"
    # },
    "LMS Quiz Submission": {
        "validate":"prompt_hr.py.lms_quiz_submission.update_status"
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
        "validate": "prompt_hr.py.attendance_request.notify_reporting_manager",
        "before_submit": "prompt_hr.py.attendance_request.before_submit"
    },
    "Payroll Entry": {
        "before_save": "prompt_hr.py.payroll_entry.before_save",
    },
    "Leave Allocation":{
        "before_validate": "prompt_hr.py.leave_allocation.before_validate"
    },
    "Leave Encashment":{
        "before_save": "prompt_hr.py.leave_encashment.before_save",
    },
    "Compensatory Leave Request": {
        "before_save": "prompt_hr.py.compensatory_leave_request.before_save",
        "on_cancel": "prompt_hr.py.compensatory_leave_request.on_cancel"
    },
    "Leave Allocation"  : {  
        "on_update": "prompt_hr.py.leave_allocation.on_update"
    },
    "Additional Salary": {
        "before_save": "prompt_hr.py.additional_salary.before_save"
    }
}


# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "prompt_hr.py.employee_changes_approval.daily_check_employee_changes_approval",
        "prompt_hr.py.compensatory_leave_request.expire_compensatory_leave_after_confirmation"
        # "prompt_hr.scheduler_methods.create_probation_feedback_form",
        # "prompt_hr.scheduler_methods.create_confirmation_evaluation_form_for_prompt",
        # "prompt_hr.scheduler_methods.validate_employee_holiday_list", 						        
    ],
}

# Testing
# -------

# before_tests = "prompt_hr.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
	# "frappe.desk.doctype.event.event.get_events": "prompt_hr.event.get_events"
    # "frappe.model.workflow.get_transitions": "prompt_hr.overrides.workflow_override.custom_get_transitions",
    # "frappe.model.workflow.apply_workflow": "prompt_hr.overrides.workflow_override.custom_apply_workflow"
# }
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
#     "dt":"Role", "filters": [["name", "in", ["Job Requisition", "Head of Department", "Managing Director"]]]
# },
# {
#     "dt":"Workflow", "filters": [["name", "in", ["Job Requisition", "Compensatory Leave Request"]]]
# },
# {
#     "dt":"Workflow State", "filters": [["name", "in", ["Approved by HOD", "Pending", "Rejected by HOD", "Approved by Director", "Rejected by Director", "Cancelled", "On-Hold", "Filled"]]]
# }

]
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
app_include_js = "assets/prompt_hr/js/welcome_page_check.js"


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
}

doctype_list_js = {"Interview": "public/js/interview.js"}
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

# permission_query_conditions = {
#     "DocType": "prompt_hr.py.welcome_status.check_welcome_completion"
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    # "ToDo": "custom_app.overrides.CustomToDo"
    "Interview": "prompt_hr.override.CustomInterview",
    "Job Offer": "prompt_hr.override.CustomJobOffer",
    "Appointment Letter": "prompt_hr.override.CustomAppointmentLetter",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Employee Onboarding": {
        "on_update": "prompt_hr.py.employee_onboarding.on_update",
    },
    "Job Requisition": {
        "validate": "prompt_hr.custom_methods.update_job_requisition_status",
        "on_update": "prompt_hr.py.job_requisition.on_update",
    },
    "Interview": {
        "validate": "prompt_hr.custom_methods.update_job_applicant_status_based_on_interview"
    },
    "Job Offer": {
        "validate": "prompt_hr.custom_methods.update_job_applicant_status_based_on_job_offer",
        "on_submit": "prompt_hr.custom_methods.update_job_applicant_status_based_on_job_offer",
    },
    "Employee": {
        "on_update": "prompt_hr.py.employee.on_update",
    },
    "Probation Feedback Form": {
        "on_submit": "prompt_hr.custom_methods.add_probation_feedback_data_to_employee"
    },
    "Confirmation Evaluation Form": {
        "on_submit": "prompt_hr.custom_methods.add_confirmation_evaluation_data_to_employee"
    },
    "Job Requisition": {
         "on_update": "prompt_hr.py.job_requisition.on_update",
     },
    # "User": {
    #     "after_insert": "prompt_hr.py.welcome_status.after_insert"
    # },
}


# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "prompt_hr.py.employee_changes_approval.daily_check_employee_changes_approval",
        # "prompt_hr.scheduler_methods.create_probation_feedback_form",
        # "prompt_hr.scheduler_methods.create_confirmation_evaluation_form",
    ],
}

# Testing
# -------

# before_tests = "prompt_hr.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "prompt_hr.event.get_events"
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

# fixtures = [
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
#     "dt":"Workflow", "filters": [["name", "in", ["Job Requisition"]]]
# },
# {
#     "dt":"Workflow State", "filters": [["name", "in", ["Approved by HOD", "Pending", "Rejected by HOD", "Approved by Director", "Rejected by Director", "Cancelled", "On-Hold", "Filled"]]]
# }

# ]

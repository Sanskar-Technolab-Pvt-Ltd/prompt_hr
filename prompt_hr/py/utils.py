import frappe
import hmac
import hashlib
import json
import traceback
from frappe import _
from frappe.utils import add_days, date_diff, flt, get_link_to_form, month_diff
from hrms.hr.utils import get_salary_assignments
from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from hrms.regional.india.utils import calculate_hra_exemption, get_component_pay, get_end_date_for_assignment, has_hra_component


# ? FUNCTION TO GENERATE HMAC HASH FROM INPUT USING SITE SECRET
def create_hash(input_text: str) -> str:
    try:
        hash_secret = frappe.local.conf.get("candidate_hash_generation_key")
        if not hash_secret:
            frappe.throw(_("Hash secret not found in site_config.json"))

        full_hash = hmac.new(
            key=hash_secret.encode("utf-8"),
            msg=input_text.strip().encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return full_hash[:12]
    except Exception as e:
        frappe.log_error("Error creating hash:", f"Error creating hash: {str(e)}\n{traceback.format_exc()}")
        frappe.throw(_("Something went wrong during hash generation."))


# ? FUNCTION TO VERIFY IF PROVIDED INPUT MATCHES THE EXPECTED HASH
def verify_hash(input_text: str, hash_to_check: str) -> bool:
    try:
        generated_hash = create_hash(input_text)
        return hmac.compare_digest(generated_hash, hash_to_check)
    except Exception as e:
        frappe.log_error(f"Error verifying hash: {str(e)}\n{traceback.format_exc()}")
        return False


# ! prompt_hr.py.utils.validate_hash
# ? FUNCTION TO VALIDATE THE HASH FOR A SPECIFIC DOCTYPE AND PRIMARY KEY
@frappe.whitelist(allow_guest=True)
def validate_hash(hash, doctype, filters):
    try:
        filters_dict = json.loads(filters)
        docname = frappe.db.get_value(doctype, filters_dict, "name")

        if not docname:
            frappe.throw(_("Document not found."))

        generated_hash = create_hash(docname)

        if not hmac.compare_digest(generated_hash, hash):
            frappe.throw(_("Invalid hash."))

        return True

    except json.JSONDecodeError:
        frappe.log_error(f"Invalid filters format: {filters}")
        frappe.throw(_("Invalid filter format. Please contact support."))
    except Exception as e:
        frappe.log_error(f"Hash Validation Error: {str(e)}\n{traceback.format_exc()}")
        frappe.throw(_("Something went wrong during hash validation."))


# ? FUNCTION TO SEND FULLY DYNAMIC NOTIFICATION EMAIL WITH PRINT FORMAT ATTACHMENT SUPPORT
# ? FUNCTION TO SEND CUSTOM NOTIFICATION EMAIL WITH OPTIONAL BUTTON, TEMPLATE, HASH, AND PDF ATTACHMENT
def send_notification_email(
    recipients,
    doctype,
    docname,
    notification_name,
    send_link=True,
    button_label="View Details",
    button_link="None",
    fallback_subject="Notification",
    fallback_message="You have a new update. Please check your portal.",
    hash_input_text=None,
    send_attach=False,
    print_format=None,
    letterhead=None,
    send_header_greeting=False,
):
    try:
        hash_value = None
        base_url = frappe.utils.get_url()
        attachments = []

        # ? GENERATE DEFAULT BUTTON LINK IF NOT EXPLICITLY PROVIDED
        if send_link and button_link == "None" and doctype and docname:
            button_link = (
                f"{base_url}/app/{doctype.lower().replace(' ', '-')}/{docname}"
            )

        # ? GENERATE SECURE HASH IF REQUIRED
        if hash_input_text:
            hash_value = create_hash(hash_input_text)

        # ? FETCH NOTIFICATION TEMPLATE IF PROVIDED
        notification_doc = None
        message = fallback_message
        subject = fallback_subject
        if notification_name:
            notification_doc = frappe.db.get_value(
                "Notification", notification_name, ["subject", "message"], as_dict=True
            )
            if notification_doc:
                doc = frappe.get_doc(doctype, docname)
                message = frappe.render_template(notification_doc.message, {"doc": doc})
                subject = frappe.render_template(notification_doc.subject, {"doc": doc})

        # ? GENERATE PDF ATTACHMENT IF REQUIRED
        if send_attach and print_format and doctype and docname:
            try:
                # ? GENERATE PDF USING FRAPPE'S BUILT-IN PDF GENERATION
                pdf_content = frappe.get_print(
                    doctype=doctype,
                    name=docname,
                    print_format=print_format,
                    letterhead=letterhead,
                    as_pdf=True,
                )

                # ? CREATE ATTACHMENT DICTIONARY
                attachment_name = f"{doctype}_{docname}_{print_format}.pdf"
                attachments.append({"fname": attachment_name, "fcontent": pdf_content})

            except Exception as pdf_error:
                frappe.log_error(
                    title="PDF Generation Error",
                    message=f"Failed to generate PDF attachment: {str(pdf_error)}\n{traceback.format_exc()}",
                )
                # ? CONTINUE WITHOUT ATTACHMENT RATHER THAN FAILING THE ENTIRE EMAIL

        for email in recipients:
            
            user = frappe.db.get_value(
                    "User", {"email": email}, ["name", "first_name"], as_dict=True
                )
           
            final_message = message
            if send_header_greeting and user:
                

                if user:
                    # ? ADD GREETING BASED ON USER'S FIRST NAME
                    greeting = (
                        f"<p>Dear {user.first_name},</p>"
                        if user.first_name
                        else "<p>Dear User,</p>"
                    )
                    final_message = greeting + final_message

            # ? ADD HASH AND ACTION BUTTON TO MESSAGE IF LINK SHOULD BE INCLUDED
            if send_link:
                hash_message = (
                    f"<p>Password: <b>{hash_value}</b></p>" if hash_value else ""
                )
                if button_link:
                    final_message += f"""
                        <hr>
                        {hash_message}
                        <p><b>{button_label}</b></p>
                        <p><a href="{button_link}" target="_blank">{button_label}</a></p>
                    """

            # ? LOG NOTIFICATION IN FRAPPE'S NOTIFICATION LOG
            if user:
                system_notification = frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "subject": subject,
                        "for_user": user.get("name"),
                        "type": "Energy Point",
                        "document_type": doctype,
                        "document_name": docname,
                    }
                )
                system_notification.insert(ignore_permissions=True)

            # ? SEND EMAIL WITH OPTIONAL ATTACHMENT
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=final_message,
                attachments=attachments if attachments else None,
            )

    except Exception as e:
        frappe.log_error(
            title="Notification Email Error",
            message=f"Failed sending notification: {str(e)}\n{traceback.format_exc()}",
        )
        frappe.throw(_("An error occurred while sending notification emails."))


# ? FUNCTION TO FETCH DOCUMENTS FROM A JOINING DOCUMENT CHECKLIST
@frappe.whitelist()
def get_checklist_documents(checklist):
    try:
        documents = frappe.db.get_all(
            "Joining Document",
            filters={"parent": checklist},
            fields=["required_document", "document_collection_stage"],
        )
        if not documents:
            return {
                "error": 1,
                "message": _("No documents found for the provided checklist."),
            }
        return {"documents": documents}
    except Exception as e:
        frappe.log_error(
            f"Error fetching checklist documents: {str(e)}\n{traceback.format_exc()}"
        )
        return {"error": str(e)}


# ? FUNCTION TO INVITE CANDIDATE FOR DOCUMENT COLLECTION
@frappe.whitelist()
def invite_for_document_collection(
    args,
    joining_document_checklist,
    child_table_fieldname,
    document_collection_stage=None,
    documents=None,
):
    try:
        if isinstance(args, str):
            args = frappe.parse_json(args)

        if isinstance(documents, str):
            documents = frappe.parse_json(documents)

        job_applicant = frappe.db.get_value(
            "Job Applicant",
            args.get("name"),
            [
                "email_id",
                "phone_number",
                "applicant_name",
                "designation",
                "custom_company",
            ],
            as_dict=True,
        )

        if not job_applicant:
            frappe.throw(_("Job Applicant not found."))

        existing = frappe.db.exists(
            "Candidate Portal",
            {
                "applicant_email": job_applicant.email_id,
            },
        )

        if existing:
            invitation = frappe.get_doc("Candidate Portal", existing)
            invitation.update(
                {
                    "phone_number": job_applicant.phone_number,
                    "applicant_name": job_applicant.applicant_name,
                    "applied_for_designation": job_applicant.designation,
                    "joining_document_checklist": joining_document_checklist,
                    "document_collection_stage": document_collection_stage,
                    "company": job_applicant.custom_company,
                }
            )

            existing_required_docs = {d.required_document for d in invitation.documents}
            if documents:
                new_docs_seen = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if (
                        req_doc
                        and req_doc not in existing_required_docs
                        and req_doc not in new_docs_seen
                    ):
                        invitation.append(
                            child_table_fieldname,
                            {
                                "required_document": req_doc,
                                "document_collection_stage": doc.get(
                                    "document_collection_stage"
                                ),
                            },
                        )
                        new_docs_seen.add(req_doc)

            invitation.save(ignore_permissions=True)
            frappe.db.commit()
            send_notification_email(
                recipients=[job_applicant.email_id],
                notification_name="Candidate Portal Link",
                doctype="Candidate Portal",
                docname=invitation.name,
                button_label="Submit Documents",
                button_link=f"/login?redirect-to=/candidate-portal/new#login",
                hash_input_text=invitation.name,
            )
            return _("Invitation updated successfully.")
        else:
            invitation = frappe.new_doc("Candidate Portal")
            invitation.update(
                {
                    "applicant_email": job_applicant.email_id,
                    "phone_number": job_applicant.phone_number,
                    "applicant_name": job_applicant.applicant_name,
                    "applied_for_designation": job_applicant.designation,
                    "joining_document_checklist": joining_document_checklist,
                    "document_collection_stage": document_collection_stage,
                    "company": job_applicant.custom_company,
                }
            )

            if documents:
                seen_docs = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in seen_docs:
                        invitation.append(
                            "documents",
                            {
                                "required_document": req_doc,
                                "document_collection_stage": doc.get(
                                    "document_collection_stage"
                                ),
                            },
                        )
                        seen_docs.add(req_doc)

            invitation.insert(ignore_permissions=True)
            frappe.db.commit()
            send_notification_email(
                recipients=[job_applicant.email_id],
                notification_name="Candidate Portal Link",
                doctype="Candidate Portal",
                docname=invitation.name,
                button_label="Submit Documents",
                button_link=f"/candidate-portal/",
                hash_input_text=invitation.name,
            )
            return _("Invitation sent successfully.")

    except Exception as e:
        frappe.log_error("Error inviting for document collection:",
            f"Error inviting for document collection: {str(e)}\n{traceback.format_exc()}"
        )
        frappe.throw(_("An error occurred while inviting for document collection."))


def get_hr_managers_by_company(company):
    try:
        return [
            row.email
            for row in frappe.db.sql(
                """
                SELECT DISTINCT u.email
                FROM `tabHas Role` hr
                JOIN `tabUser` u ON u.name = hr.parent
                JOIN `tabEmployee` e ON e.user_id = u.name
                WHERE hr.role = 'HR Manager'
                  AND u.enabled = 1
                  AND e.company = %s
            """,
                (company,),
                as_dict=1,
            )
            if row.email
        ]
    except Exception as e:
        frappe.log_error(
            f"Error fetching HR managers by company: {str(e)}\n{traceback.format_exc()}"
        )
        return []


@frappe.whitelist()
def check_user_is_reporting_manager(user_id, requesting_employee_id):
    """Method to check if the current user is Employees reporting manager"""
    try:
        reporting_manager_emp_id = frappe.db.get_value(
            "Employee", requesting_employee_id, "reports_to"
        )

        if reporting_manager_emp_id:
            rh_user_id = frappe.db.get_value(
                "Employee", reporting_manager_emp_id, "user_id"
            )
            if rh_user_id and (user_id == rh_user_id):
                return {"error": 0, "is_rh": 1}
            else:
                return {"error": 0, "is_rh": 0}
        else:
            return {"error": 0, "is_rh": 0}
    except Exception as e:
        frappe.log_error("Error while Verifying User", frappe.get_traceback())
        return {"error": 1, "message": f"{str(e)}"}

@frappe.whitelist()
def is_user_reporting_manager_or_hr(user_id, requesting_employee_id):
    """Method to check if the current user is the employee's Reporting Manager or has HR roles"""

    try:
        # * REUSE EXISTING FUNCTION TO CHECK REPORTING MANAGER LOGIC
        rh_check = check_user_is_reporting_manager(user_id, requesting_employee_id)

        # ? IF USER IS REPORTING MANAGER, RETURN SUCCESS
        if rh_check.get("is_rh") == 1:
            return {"error": 0, "is_rh": 1}

        # ? CHECK IF THE USER HAS HR ROLES
        has_hr_role = frappe.db.exists({
            "doctype": "Has Role",
            "parent": user_id,
            "role": ["in", ["HR User", "HR Manager"]]
        })

        # * IF HR ROLE FOUND, GRANT ACCESS
        if has_hr_role:
            return {"error": 0, "is_rh": 1}

        # ? OTHERWISE, NOT AUTHORIZED
        return {"error": 0, "is_rh": 0}

    except Exception as e:
        # ! LOG ERROR IF SOMETHING GOES WRONG
        frappe.log_error("Error while Verifying User HR Role or RH Status", frappe.get_traceback())
        return {"error": 1, "message": f"{str(e)}"}


@frappe.whitelist()
def fetch_company_name(indifoss=0, prompt=0):
    """Method to fetch the company abbreviation from hr settings then based on the abbreviation fetch the company name

    Args:
        indifoss (int, optional):  to fetch the indifoss company's abbreviation. Defaults to 0.
        prompt (int, optional): to fetch the prompt company's abbreviation. Defaults to 0.
    """

    try:
        if indifoss:
            indifoss_abbr = frappe.db.get_single_value(
                "HR Settings", "custom_indifoss_abbr"
            )

            if not indifoss_abbr:
                return {
                    "error": 1,
                    "message": "No Abbreviation found in HR Settings, Please set abbreviation first",
                }

            return {
                "error": 0,
                "company_id": frappe.db.get_value(
                    "Company", {"abbr": indifoss_abbr}, "name"
                )
                or None,
            }

        if prompt:
            prompt_abbr = frappe.db.get_single_value(
                "HR Settings", "custom_prompt_abbr"
            )

            if not prompt_abbr:
                return {
                    "error": 1,
                    "message": "No Abbreviation found in HR Settings, Please set abbreviation first",
                }

            return {
                "error": 0,
                "company_id": frappe.db.get_value(
                    "Company", {"abbr": prompt_abbr}, "name"
                )
                or None,
            }

    except Exception as e:
        frappe.log_error(
            f"Error fetching company name: {str(e)}\n{traceback.format_exc()}"
        )
        return {"error": 1, "message": str(e)}


@frappe.whitelist()
def fetch_leave_type_for_indifoss(doctype, txt, searchfield, start, page_len, filters):
    """Static method to fetch options for leave type link field. Field is in  HR Settings"""
    try:
        company_id = filters.get("company_id")
        if not company_id:
            frappe.throw(_("Company ID is required to fetch leave types."))

        return frappe.db.sql(
            """
            SELECT name FROM `tabLeave Type`
            WHERE custom_company = %s
            AND (is_earned_leave = 1 OR custom_is_quarterly_carryforward_rule_applied = 1)
        """,
            (company_id),
            as_list=True,
        )
    except Exception as e:
        frappe.log_error(
            f"Error fetching leave type for Indifoss: {str(e)}\n{traceback.format_exc()}"
        )
        return []


# ? FUNCTION TO SHARE DOCUMENT AND SEND NOTIFICATION EMAIL
def expense_claim_and_travel_request_workflow_email(doc):
    try:
        old_doc = doc.get_doc_before_save()

        # ? CHECK IF WORKFLOW STATE CHANGED
        if old_doc and doc.workflow_state != old_doc.workflow_state:
            recipient = None
            if doc.workflow_state == "Escalated":
                if doc.company == get_prompt_company_name().get("company_name"):
                    recipient = get_bu_head_email(doc.employee, doc)
                elif doc.company == get_indifoss_company_name().get("company_name"):
                    recipient = get_hod_email(doc.employee)
                if recipient:
                    share_and_notify(
                        doc,
                        recipient,
                        "Travel Request and Expense Claim Update Notification",
                        send_header_greeting=True,
                    )
                else:
                    frappe.log_error(
                        "No recipient found for escalation in Expense Claim workflow."
                    )

            elif (
                doc.workflow_state == "Senior Approval"
                or doc.workflow_state == "Approved by BU Head"
            ):
                reporting_manager_email = get_reporting_manager_email(doc.employee)
                if reporting_manager_email:
                    share_and_notify(
                        doc,
                        reporting_manager_email,
                        "Travel Request and Expense Claim Update Notification",
                        send_header_greeting=True,
                    )

            elif (
                doc.workflow_state == "Senior Rejection"
                or doc.workflow_state == "Rejected by BU Head"
            ):
                user_email = frappe.get_value("Employee", doc.employee, "user_id")
                if user_email:
                    share_and_notify(
                        doc,
                        user_email,
                        "Travel Request and Expense Claim Update Notification",
                        send_header_greeting=True,
                    )

            elif doc.workflow_state == "Approved by Reporting Manager":
                travel_desk_emails = get_travel_desk_user_emails(doc.company)
                send_email_to_users(
                    doc,
                    travel_desk_emails,
                    "Travel Request and Expense Claim Update Notification",
                    send_header_greeting=True,
                )

            elif doc.workflow_state == "Sent to Accounting Team":
                accounting_emails = get_accounting_team_emails(doc.company)
                send_email_to_users(
                    doc,
                    accounting_emails,
                    "Travel Request and Expense Claim Update Notification",
                    send_header_greeting=True,
                )

        elif not old_doc and doc.workflow_state == "Pending":
            reporting_manager_email = get_reporting_manager_email(doc.employee)
            if reporting_manager_email:
                share_and_notify(
                    doc,
                    reporting_manager_email,
                    "Travel Request and Expense Claim Update Notification",
                    send_header_greeting=True,
                )
    except Exception as e:
        frappe.log_error(
            "Error While expense claim workflow email",
            f"Error in expense claim workflow email: {str(e)}\n{traceback.format_exc()}"
        )


# ? FUNCTION TO GET REPORTING MANAGER EMAIL FROM EMPLOYEE
def get_reporting_manager_email(employee_id):
    try:
        reporting_manager = frappe.get_value("Employee", employee_id, "reports_to")
        if not reporting_manager:
            return None
        reporting_manager_email = frappe.get_value(
            "Employee", reporting_manager, "user_id"
        )
        return reporting_manager_email
    except Exception as e:
        frappe.log_error(
            f"Error getting reporting manager email: {str(e)}\n{traceback.format_exc()}"
        )
        return None


# ? FUNCTION TO GET BUSINESS UNIT HEAD EMAIL FROM EMPLOYEE'S BUSINESS UNIT
def get_bu_head_email(employee_id, doc):
    try:
        business_unit = frappe.get_value(
            "Employee", employee_id, "custom_business_unit"
        )
        if not business_unit:
            return None
        bu_head = frappe.get_value("Business Unit", business_unit, "business_unit_head")
        doc.custom_escalated_to = bu_head
        doc.custom_escalated_to_name = frappe.get_value(
            "Employee", bu_head, "first_name"
        )
        if not bu_head:
            return None
        user_id = frappe.get_value("Employee", bu_head, "user_id")
        return user_id
    except Exception as e:
        frappe.log_error(
            f"Error getting Business Unit Head email: {str(e)}\n{traceback.format_exc()}"
        )
        return None


# ? FUNCTION TO GET ALL EMPLOYEE EMAILS WITH TRAVEL DESK USER ROLE IN A COMPANY
def get_travel_desk_user_emails(company):
    try:
        employees = frappe.get_all(
            "Employee", filters={"company": company}, fields=["user_id"]
        )
        valid_emails = [
            e.user_id
            for e in employees
            if e.user_id and has_role(e.user_id, "Travel Desk User")
        ]
        return valid_emails
    except Exception as e:
        frappe.log_error(
            f"Error getting travel desk user emails: {str(e)}\n{traceback.format_exc()}"
        )
        return []


# ? FUNCTION TO GET ALL EMPLOYEE EMAILS WITH ACCOUNTS USER ROLE IN A COMPANY
def get_accounting_team_emails(company):
    try:
        employees = frappe.get_all(
            "Employee", filters={"company": company}, fields=["user_id"]
        )
        valid_emails = [
            e.user_id
            for e in employees
            if e.user_id and has_role(e.user_id, "Accounts User")
        ]
        return valid_emails
    except Exception as e:
        frappe.log_error(
            f"Error getting accounting team emails: {str(e)}\n{traceback.format_exc()}"
        )
        return []


# ? FUNCTION TO CHECK IF USER HAS A SPECIFIC ROLE
def has_role(user, role_name):
    try:
        return frappe.db.exists("Has Role", {"parent": user, "role": role_name})
    except Exception as e:
        frappe.log_error(
            f"Error checking user role: {str(e)}\n{traceback.format_exc()}"
        )
        return False


# ? FUNCTION TO SHARE DOCUMENT AND SEND NOTIFICATION EMAIL TO A SINGLE USER
def share_and_notify(doc, user_id, notification_name, send_header_greeting=False):
    try:
        frappe.share.add(doc.doctype, doc.name, user_id)
        send_notification_email(
            doctype=doc.doctype,
            docname=doc.name,
            recipients=[user_id],
            notification_name=notification_name,
            send_header_greeting=send_header_greeting,
        )
    except Exception as e:
        frappe.log_error(
            f"Error sharing document and sending notification: {str(e)}\n{traceback.format_exc()}"
        )


# ? FUNCTION TO SEND EMAIL NOTIFICATIONS TO MULTIPLE USERS
def send_email_to_users(doc, user_ids, notification_name, send_header_greeting=False):
    try:
        if not user_ids:
            return

        send_notification_email(
            doctype=doc.doctype,
            docname=doc.name,
            recipients=user_ids,
            notification_name=notification_name,
            send_header_greeting=send_header_greeting,
        )
    except Exception as e:
        frappe.log_error(
            f"Error sending email to multiple users: {str(e)}\n{traceback.format_exc()}"
        )


@frappe.whitelist()
# ? FUNCTION TO GET THE COMPANY NAME BASED ON THE ABRREVIATION SET IN HR SETTINGS
def get_prompt_company_name():
    """Method to fetch the company name for Prompt HR"""
    try:
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
        if not prompt_abbr:
            return {
                "error": 1,
                "message": "No Abbreviation found in HR Settings, Please set abbreviation first",
            }

        company_name = frappe.db.get_value("Company", {"abbr": prompt_abbr}, "name")
        return {"error": 0, "company_name": company_name or None}

    except Exception as e:
        frappe.log_error(
            f"Error getting Prompt company name: {str(e)}\n{traceback.format_exc()}"
        )
        return {"error": 1, "message": str(e)}


@frappe.whitelist()
# ? FUNCTION TO GET THE COMPANY NAME BASED ON THE ABRREVIATION SET IN HR SETTINGS
def get_indifoss_company_name():
    """Method to fetch the company name for Indifoss HR"""
    try:
        indifoss_abbr = frappe.db.get_single_value(
            "HR Settings", "custom_indifoss_abbr"
        )
        if not indifoss_abbr:
            return {
                "error": 1,
                "message": "No Abbreviation found in HR Settings, Please set abbreviation first",
            }

        company_name = frappe.db.get_value("Company", {"abbr": indifoss_abbr}, "name")
        return {"error": 0, "company_name": company_name or None}

    except Exception as e:
        frappe.log_error(
            f"Error getting Indifoss company name: {str(e)}\n{traceback.format_exc()}"
        )
        return {"error": 1, "message": str(e)}


# ? FUNCTION TO GET THE APPLICABLE PRINT FORMAT BASED ON IS_PROMPT AND DOCTYPE
def get_applicable_print_format(is_prompt, doctype):
    try:
        if is_prompt:
            print_format = frappe.db.get_value(
                "Print Format Selection",
                {
                    "parentfield": "custom_print_format_table_indifoss",
                    "document": doctype,
                },
                "print_format_document",
            )
            if not print_format:
                return {"error": 1, "message": _("No Print Format found for Prompt HR")}
            return {"error": 0, "print_format": print_format}

        else:
            print_format = frappe.db.get_value(
                "Print Format", {"doc_type": doctype, "disabled": 0}, "name"
            )
            if not print_format:
                return {
                    "error": 1,
                    "message": _("No Print Format found for Indifoss HR"),
                }
            return {"error": 0, "print_format": print_format}

    except Exception as e:
        frappe.log_error(
            f"Error getting applicable print format: {str(e)}\n{traceback.format_exc()}"
        )
        return {"error": 1, "message": str(e)}


# ? FUNCTION TO GET HOD EMAIL FROM EMPLOYEE ID
def get_hod_email(employee_id):
    """Method to get the HOD email of an employee"""
    try:
        department = frappe.get_value("Employee", employee_id, "department")
        if not department:
            return None

        hod = frappe.get_value("Department", department, "custom_department_head")
        if not hod:
            return None

        return frappe.get_value("Employee", hod, "user_id")

    except Exception as e:
        frappe.log_error(
            f"Error fetching HOD email: {str(e)}\n{traceback.format_exc()}"
        )
        return None
    


# HRA calculation override
def calculate_annual_eligible_hra_exemption(doc):
	basic_component, hra_component, da_component = frappe.db.get_value(
		"Company", doc.company, ["basic_component", "hra_component", "custom_dearness_allowance"]
	)

	if not (basic_component and hra_component):
		frappe.throw(
			_("Please set Basic and HRA component in Company {0}").format(
				get_link_to_form("Company", doc.company)
			)
		)

	annual_exemption = monthly_exemption = hra_amount = basic_amount = 0

	if hra_component and basic_component:
		assignments = get_salary_assignments(doc.employee, doc.payroll_period)

		if not assignments and doc.docstatus == 1:
			frappe.throw(_("Salary Structure must be submitted before submission of {0}").format(doc.doctype))

		period_start_date = frappe.db.get_value("Payroll Period", doc.payroll_period, "start_date")

		assignment_dates = []
		for assignment in assignments:
			# if assignment is before payroll period, use period start date to get the correct days
			assignment.from_date = max(assignment.from_date, period_start_date)
			assignment_dates.append(assignment.from_date)

		for idx, assignment in enumerate(assignments):
			if has_hra_component(assignment.salary_structure, hra_component):
				basic_salary_amt, hra_salary_amt, da_amt = get_component_amt_from_salary_slip(
					doc.employee,
					assignment.salary_structure,
					basic_component,
					hra_component,
					da_component,
					assignment.from_date,
				)
				to_date = get_end_date_for_assignment(assignment_dates, idx, doc.payroll_period)

				frequency = frappe.get_value(
					"Salary Structure", assignment.salary_structure, "payroll_frequency"
				)
				basic_amount += get_component_pay(frequency, basic_salary_amt + da_amt, assignment.from_date, to_date)
				hra_amount += get_component_pay(frequency, hra_salary_amt, assignment.from_date, to_date)

		if hra_amount:
			if doc.monthly_house_rent:
				annual_exemption = calculate_hra_exemption(
					assignment.salary_structure,
					basic_amount,
					hra_amount,
					doc.monthly_house_rent,
					doc.rented_in_metro_city,
				)
				if annual_exemption > 0:
					monthly_exemption = annual_exemption / 12
				else:
					annual_exemption = 0

	return frappe._dict(
		{
			"hra_amount": hra_amount,
			"annual_exemption": annual_exemption,
			"monthly_exemption": monthly_exemption,
		}
	)

def get_component_amt_from_salary_slip(employee, salary_structure, basic_component, hra_component, da_component, from_date):

	salary_slip = make_salary_slip(
		salary_structure,
		employee=employee,
		for_preview=1,
		ignore_permissions=True,
		posting_date=from_date,
	)

	basic_amt, hra_amt, da_amt = 0, 0, 0
	for earning in salary_slip.earnings:
		if earning.salary_component == basic_component:
			basic_amt = earning.amount
		elif earning.salary_component == hra_component:
			hra_amt = earning.amount
		elif earning.salary_component == da_component:
			da_amt = earning.amount
		if basic_amt and hra_amt and da_amt:
			return basic_amt, hra_amt, da_amt
	return basic_amt, hra_amt, da_amt

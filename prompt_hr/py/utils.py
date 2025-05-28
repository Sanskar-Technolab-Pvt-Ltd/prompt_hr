import frappe
import hmac
import hashlib
import json
import traceback
from frappe import _


# ? FUNCTION TO GENERATE HMAC HASH FROM INPUT USING SITE SECRET
def create_hash(input_text: str) -> str:
    try:
        hash_secret = frappe.local.conf.get("candidate_hash_generation_key")
        if not hash_secret:
            frappe.throw(_("Hash secret not found in site_config.json"))

        full_hash = hmac.new(
            key=hash_secret.encode('utf-8'),
            msg=input_text.strip().encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        return full_hash[:12]
    except Exception as e:
        frappe.log_error(f"Error creating hash: {str(e)}\n{traceback.format_exc()}")
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
):
    try:
        hash = None
        base_url = frappe.utils.get_url()
        attachments = []

        # ? GENERATE DEFAULT BUTTON LINK IF NOT EXPLICITLY PROVIDED
        if send_link and button_link == "None" and doctype and docname:
            button_link = f"{base_url}/app/{doctype.lower().replace(' ', '-')}/{docname}"

        # ? GENERATE SECURE HASH IF REQUIRED
        if hash_input_text:
            hash = create_hash(hash_input_text)

        # ? FETCH NOTIFICATION TEMPLATE IF PROVIDED
        notification_doc = None
        if notification_name:
            notification_doc = frappe.db.get_value(
                "Notification", notification_name, ["subject", "message"], as_dict=True
            )
            if notification_doc:
                doc = frappe.get_doc(doctype, docname)
                message = frappe.render_template(notification_doc.message, {"doc": doc})
                subject = frappe.render_template(notification_doc.subject, {"doc": doc})
            else:
                message = fallback_message
                subject = fallback_subject
        else:
            message = fallback_message
            subject = fallback_subject

        # ? GENERATE PDF ATTACHMENT IF REQUIRED
        if send_attach and print_format and doctype and docname:
            try:
                # Generate PDF using Frappe's built-in PDF generation
                pdf_content = frappe.get_print(
                    doctype=doctype,
                    name=docname,
                    print_format=print_format,
                    letterhead=letterhead,
                    as_pdf=True
                )
                
                # Create attachment dictionary
                attachment_name = f"{doctype}_{docname}_{print_format}.pdf"
                attachments.append({
                    "fname": attachment_name,
                    "fcontent": pdf_content
                })
                
            except Exception as pdf_error:
                frappe.log_error(
                    title="PDF Generation Error",
                    message=f"Failed to generate PDF attachment: {str(pdf_error)}\n{traceback.format_exc()}"
                )
                # Continue without attachment rather than failing the entire email

        for email in recipients:
            user = frappe.db.get_value("User", {"email": email}, "name")
            final_message = message
            
            # ? ADD HASH AND ACTION BUTTON TO MESSAGE IF LINK SHOULD BE INCLUDED
            if send_link:
                hash_message = f"<p>Password: <b>{hash}</b></p>" if hash else ""
                if button_link:
                    final_message += f"""
                        <hr>
                        {hash_message}
                        <p><b>{button_label}</b></p>
                        <p><a href="{button_link}" target="_blank">{button_label}</a></p>
                    """

            # ? LOG NOTIFICATION IN FRAPPE'S NOTIFICATION LOG
            if user:
                system_notification = frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": subject,
                    "for_user": user,
                    "type": "Energy Point",
                    "document_type": doctype,
                    "document_name": docname,
                })
                system_notification.insert(ignore_permissions=True)

            # ? SEND EMAIL WITH OPTIONAL ATTACHMENT
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=final_message,
                attachments=attachments if attachments else None,
            )

        # ? LOG SUCCESS
        attachment_info = f" with {len(attachments)} attachment(s)" if attachments else ""
        frappe.log_error(
            title="Notification Sent",
            message=f"Sent dynamic notification to {len(recipients)} recipient(s){attachment_info}."
        )

    except Exception as e:
        frappe.log_error(
            title="Notification Email Error",
            message=f"Failed sending notification: {str(e)}\n{traceback.format_exc()}"
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
            return {"error": 1, "message": _("No documents found for the provided checklist.")}
        return {"documents": documents}
    except Exception as e:
        frappe.log_error(f"Error fetching checklist documents: {str(e)}\n{traceback.format_exc()}")
        return {"error": str(e)}


# ? FUNCTION TO INVITE CANDIDATE FOR DOCUMENT COLLECTION
@frappe.whitelist()
def invite_for_document_collection(args, joining_document_checklist, child_table_fieldname,document_collection_stage=None, documents=None):
    try:
        if isinstance(args, str):
            args = frappe.parse_json(args)

        if isinstance(documents, str):
            documents = frappe.parse_json(documents)

        job_applicant = frappe.db.get_value(
            "Job Applicant",
            args.get("name"),
            ["email_id", "phone_number", "applicant_name", "designation","custom_company"],
            as_dict=True
        )

        if not job_applicant:
            frappe.throw(_("Job Applicant not found."))

        existing = frappe.db.exists("Candidate Portal", {
            "applicant_email": job_applicant.email_id,
        })

        if existing:
            invitation = frappe.get_doc("Candidate Portal", existing)
            invitation.update({
                "phone_number": job_applicant.phone_number,
                "applicant_name": job_applicant.applicant_name,
                "applied_for_designation": job_applicant.designation,
                "joining_document_checklist": joining_document_checklist,
                "document_collection_stage": document_collection_stage,
                "company": job_applicant.custom_company,
            })

            existing_required_docs = {d.required_document for d in invitation.documents}
            if documents:
                new_docs_seen = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in existing_required_docs and req_doc not in new_docs_seen:
                        invitation.append(child_table_fieldname, {
                            "required_document": req_doc,
                            "document_collection_stage": doc.get("document_collection_stage")
                        })
                        new_docs_seen.add(req_doc)

            invitation.save(ignore_permissions=True)
            frappe.db.commit()
            send_notification_email(
                recipients=[job_applicant.email_id],
                notification_name="Candidate Portal Link",
                doctype="Candidate Portal",
                docname=invitation.name,
                button_label="Submit Documents",
                button_link=f"/candidate-portal/",
                hash_input_text = invitation.name,
            )
            return _("Invitation updated successfully.")
        else:
            invitation = frappe.new_doc("Candidate Portal")
            invitation.update({
                "applicant_email": job_applicant.email_id,
                "phone_number": job_applicant.phone_number,
                "applicant_name": job_applicant.applicant_name,
                "applied_for_designation": job_applicant.designation,
                "joining_document_checklist": joining_document_checklist,
                "document_collection_stage": document_collection_stage,
                "company": job_applicant.custom_company,
            })

            if documents:
                seen_docs = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in seen_docs:
                        invitation.append("documents", {
                            "required_document": req_doc,
                            "document_collection_stage": doc.get("document_collection_stage")
                        })
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
                hash_input_text = invitation.name,
            )
            return _("Invitation sent successfully.")

    except Exception as e:
        frappe.log_error(f"Error inviting for document collection: {str(e)}\n{traceback.format_exc()}")
        frappe.throw(_("An error occurred while inviting for document collection."))

def get_hr_managers_by_company(company):
    return [
        row.email for row in frappe.db.sql("""
            SELECT DISTINCT u.email
            FROM `tabHas Role` hr
            JOIN `tabUser` u ON u.name = hr.parent
            JOIN `tabEmployee` e ON e.user_id = u.name
            WHERE hr.role = 'HR Manager'
              AND u.enabled = 1
              AND e.company = %s
        """, (company,), as_dict=1) if row.email
    ]


@frappe.whitelist()
def check_user_is_reporting_manager(user_id, requesting_employee_id):
	""" Method to check if the current user is Employees reporting manager
	"""
	try:
		reporting_manager_emp_id = frappe.db.get_value("Employee", requesting_employee_id, "reports_to")

		if reporting_manager_emp_id:
			rh_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")
			if rh_user_id and (user_id == rh_user_id):
				return {"error": 0, "is_rh": 1}
			else:
				return {"error": 0, "is_rh": 0}
		else:
			return {"error": 0, "is_rh": 0}
	except Exception as e:
		frappe.log_error("Error while Verifying User", frappe.get_traceback())
		return {"error":1, "message": f"{str(e)}"}


@frappe.whitelist()
def fetch_company_name(indifoss=0, prompt=0):
    """Method to fetch the company abbreviation from hr settings then based on the abbreviation fetch the company name

    Args:
        indifoss (int, optional):  to fetch the indifoss company's abbreviation. Defaults to 0.
        prompt (int, optional): to fetch the prompt company's abbreviation. Defaults to 0.
    """
    
    try:
        if indifoss:
            indifoss_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
            
            if not indifoss_abbr:
                return {"error": 1, "message": "No Abbreviation found in HR Settings, Please set abbreviation first"}

            return {"error": 0, "company_id": frappe.db.get_value("Company", {"abbr": indifoss_abbr}, "name") or None}
            
        
        if prompt:
            prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
            
            if not prompt_abbr:
                return {"error": 1, "message": "No Abbreviation found in HR Settings, Please set abbreviation first"}
            
            return {"error": 0, "company_id": frappe.db.get_value("Company", {"abbr": prompt_abbr}, "name") or None}
            
    except Exception as e:
        return {"error": 1, "message": str(e)}
    
@frappe.whitelist()
def fetch_leave_type_for_indifoss(doctype, txt, searchfield, start, page_len, filters):
    """ Static method to fetch options for leave type link field. Field is in  HR Settings 
    """
    company_id = filters.get("company_id")

    return frappe.db.sql("""
        SELECT name FROM `tabLeave Type`
        WHERE custom_company = %s
        AND (is_earned_leave = 1 OR custom_is_quarterly_carryforward_rule_applied = 1)
    """, (company_id))

# ? FUNCTION TO SHARE DOCUMENT AND SEND NOTIFICATION EMAIL
def expense_claim_workflow_email(doc):
    old_doc = doc.get_doc_before_save()
    print(f"[DEBUG] Old Document\n\n\n: {old_doc}")

    # ? CHECK IF WORKFLOW STATE CHANGED
    if old_doc and doc.workflow_state != old_doc.workflow_state:
        print(f"[DEBUG] Workflow changed from {old_doc.workflow_state} to {doc.workflow_state}")

        if doc.workflow_state == "Escalated":
            print(f"[DEBUG] BU Head Email\n\n\n:")
            bu_head_email = get_bu_head_email(doc.employee, doc)
            print(f"[DEBUG] BU Head Email: {bu_head_email}")
            if bu_head_email:
                share_and_notify(doc, bu_head_email, "Expense Claim - BU Head")

        elif doc.workflow_state == "Approved by BU Head":
            travel_desk_emails = get_travel_desk_user_emails(doc.company)
            print(f"[DEBUG] Travel Desk Emails: {travel_desk_emails}")
            send_email_to_users(doc, travel_desk_emails, "Expense Claim - Travel Desk User")

        elif doc.workflow_state == "Approved by Reporting Manager":
            travel_desk_emails = get_travel_desk_user_emails(doc.company)
            print(f"[DEBUG] Travel Desk Emails: {travel_desk_emails}")
            send_email_to_users(doc, travel_desk_emails, "Expense Claim - Travel Desk User")

        elif doc.workflow_state == "Sent to Accounting Team":
            accounting_emails = get_accounting_team_emails(doc.company)
            print(f"[DEBUG] Accounting Team Emails: {accounting_emails}")
            send_email_to_users(doc, accounting_emails, "Expense Claim - Accounting Team")

    elif not old_doc and doc.workflow_state == "Pending":
        reporting_manager_email = get_reporting_manager_email(doc.employee)
        print(f"[DEBUG] Reporting Manager Email: {reporting_manager_email}")
        if reporting_manager_email:
            share_and_notify(doc, reporting_manager_email, "Expense Claim - Reporting Manager")
    else:
        print(f"[DEBUG] No workflow state change detected or no action required for state: {doc.workflow_state}")
        print(doc, doc.is_new())


# ? FUNCTION TO GET REPORTING MANAGER EMAIL FROM EMPLOYEE
def get_reporting_manager_email(employee_id):
    reporting_manager = frappe.get_value("Employee", employee_id, "reports_to")
    reporting_manager_email = frappe.get_value("Employee", reporting_manager, "user_id")
    if not reporting_manager_email: 
        return None
    print(f"[DEBUG] get_reporting_manager_email({employee_id}) = {reporting_manager_email}")
    return reporting_manager_email


# ? FUNCTION TO GET BUSINESS UNIT HEAD EMAIL FROM EMPLOYEE'S BUSINESS UNIT
def get_bu_head_email(employee_id, doc):
    business_unit = frappe.get_value("Employee", employee_id, "custom_business_unit")
    print(f"[DEBUG] Employee {employee_id} - Business Unit: {business_unit}")
    if not business_unit:
        return None
    bu_head = frappe.get_value("Business Unit", business_unit, "business_unit_head")
    doc.custom_escalated_to = bu_head
    doc.custom_escalated_to_name = frappe.get_value("Employee", bu_head, "first_name")
    print(f"[DEBUG] Business Unit Head: {bu_head}")
    if not bu_head:
        return None
    user_id = frappe.get_value("Employee", bu_head, "user_id")
    print(f"[DEBUG] BU Head User ID: {user_id}")
    return user_id


# ? FUNCTION TO GET ALL EMPLOYEE EMAILS WITH TRAVEL DESK USER ROLE IN A COMPANY
def get_travel_desk_user_emails(company):
    employees = frappe.get_all(
        "Employee",
        filters={"company": company},
        fields=["user_id"]
    )
    valid_emails = [e.user_id for e in employees if e.user_id and has_role(e.user_id, "Travel Desk User")]
    print(f"[DEBUG] Travel Desk Users: {valid_emails}")
    return valid_emails


# ? FUNCTION TO GET ALL EMPLOYEE EMAILS WITH ACCOUNTS USER ROLE IN A COMPANY
def get_accounting_team_emails(company):
    employees = frappe.get_all(
        "Employee",
        filters={"company": company},
        fields=["user_id"]
    )
    print(f"[DEBUG] Employees in company '{company}': {[e.user_id for e in employees]}")
    valid_emails = [e.user_id for e in employees if e.user_id and has_role(e.user_id, "Accounts User")]
    print(f"[DEBUG] Accounts Users: {valid_emails}")
    return valid_emails


# ? FUNCTION TO CHECK IF USER HAS A SPECIFIC ROLE
def has_role(user, role_name):
    has = frappe.db.exists("Has Role", {"parent": user, "role": role_name})
    print(f"[DEBUG] has_role({user}, {role_name}) = {has}")
    return has


# ? FUNCTION TO SHARE DOCUMENT AND SEND NOTIFICATION EMAIL TO A SINGLE USER
def share_and_notify(doc, user_id, notification_name):
    print(f"[DEBUG] Sharing {doc.doctype} {doc.name} with {user_id}")
    frappe.share.add(doc.doctype, doc.name, user_id)

    print(f"[DEBUG] Sending notification '{notification_name}' to {user_id}")
    send_notification_email(
        doctype=doc.doctype,
        docname=doc.name,
        recipients=[user_id],
        notification_name=notification_name
    )

# ? FUNCTION TO SEND EMAIL NOTIFICATIONS TO MULTIPLE USERS
def send_email_to_users(doc, user_ids, notification_name):
    if not user_ids:
        print(f"[DEBUG] No users found for notification: {notification_name}")
        return

    print(f"[DEBUG] Sending notification '{notification_name}' to: {user_ids}")
    send_notification_email(
        doctype=doc.doctype,
        docname=doc.name,
        recipients=user_ids,
        notification_name=notification_name
    )

def get_prompt_company_name():
    """Method to fetch the company name for Prompt HR"""
    try:
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
        if not prompt_abbr:
            return {"error": 1, "message": "No Abbreviation found in HR Settings, Please set abbreviation first"}
        
        company_name = frappe.db.get_value("Company", {"abbr": prompt_abbr}, "name")
        return {"error": 0, "company_name": company_name or None}
    
    except Exception as e:
        return {"error": 1, "message": str(e)}

def get_indifoss_company_name():
    """Method to fetch the company name for Indifoss HR"""
    try:
        indifoss_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
        if not indifoss_abbr:
            return {"error": 1, "message": "No Abbreviation found in HR Settings, Please set abbreviation first"}
        
        company_name = frappe.db.get_value("Company", {"abbr": indifoss_abbr}, "name")
        return {"error": 0, "company_name": company_name or None}
    
    except Exception as e:
        return {"error": 1, "message": str(e)}


import frappe
import hmac
import hashlib
import json
import traceback
from frappe import _


# ? FUNCTION TO GENERATE HMAC HASH FROM INPUT USING SITE SECRET
def create_hash(input_text: str) -> str:
    try:
        hash_secret = frappe.local.conf.get("hash_secret_key")
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


# ? FUNCTION TO SEND FULLY DYNAMIC NOTIFICATION EMAIL
# ? FUNCTION TO SEND CUSTOM NOTIFICATION EMAIL WITH OPTIONAL BUTTON, TEMPLATE, AND HASH
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
):
    try:
        hash = None
        base_url = frappe.utils.get_url()

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
        for email in recipients:
            user = frappe.db.get_value("User", {"email": email}, "name")

            # ? ADD HASH AND ACTION BUTTON TO MESSAGE IF LINK SHOULD BE INCLUDED
            if send_link:
                hash_message = f"<p>Password: <b>{hash}</b></p>" if hash else ""
                if button_link:
                    final_message = message
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

            # ? SEND EMAIL
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=final_message,
            )

        # ? LOG SUCCESS
        frappe.log_error(
            title="Notification Sent",
            message=f"Sent dynamic notification to {len(recipients)} recipient(s)."
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
def invite_for_document_collection(args, joining_document_checklist, document_collection_stage=None, documents=None):
    try:
        if isinstance(args, str):
            args = frappe.parse_json(args)

        if isinstance(documents, str):
            documents = frappe.parse_json(documents)

        job_applicant = frappe.db.get_value(
            "Job Applicant",
            args.get("name"),
            ["email_id", "phone_number", "applicant_name", "designation"],
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
            })

            existing_required_docs = {d.required_document for d in invitation.documents}
            if documents:
                new_docs_seen = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in existing_required_docs and req_doc not in new_docs_seen:
                        invitation.append("documents", {
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




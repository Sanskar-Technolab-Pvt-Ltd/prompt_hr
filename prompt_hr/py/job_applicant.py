import frappe

#* API TO SEND EMAIL TO JOB APPLICANT FOR SCREEN TEST
@frappe.whitelist()
def check_test_and_invite(job_applicant):
    try:
        applicant = frappe.get_doc("Job Applicant", job_applicant)
        job_opening = frappe.get_doc("Job Opening", applicant.job_title)

        if not job_opening.custom_applicable_screening_test:
            return { "error":0,"message":"redirect"}

        if not applicant.email_id:
            frappe.throw("No email address found for the applicant.")

        
        subject = "Screen Test Invitation"
        # test_link = get_url(f"/test?applicant={applicant.name}") 
        test_link = "Test Link Url"
        content = f"""
            Dear {applicant.applicant_name},<br><br>
            You are invited to take a screen test for the position of <b>{applicant.job_title}</b>.<br>
            Please click the link below to take the test:<br>
            LINK
            Regards,<br>
            HR Team
        """
    # <a href="{test_link}">{test_link}</a><br><br>
        frappe.sendmail(
            recipients=[applicant.email_id],
            subject=subject,
            message=content
        )
        
        frappe.db.set_value("Job Applicant", job_applicant, "status", "Screening Test Scheduled")
        
        return {"error":0, "message":"invited"}
    except Exception as e:
        frappe.log_error(f"Error in check_test_and_invite", frappe.get_traceback())
        return {"error": 1, "message": str(e)}

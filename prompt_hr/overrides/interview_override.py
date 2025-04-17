import frappe
from frappe import _
from hrms.hr.doctype.interview.interview import Interview, get_recipients
from hrms.hr.doctype.job_offer.job_offer import JobOffer
from hrms.hr.doctype.appointment_letter.appointment_letter import AppointmentLetter



class CustomInterview(Interview):
    
    
    def show_job_applicant_update_dialog(self):
        """Override the show_job_applicant_update_dialog method to stop calling update_job_applicant which updates the status of the job applicant.
        """
        pass
        # job_applicant_status = self.get_job_applicant_status()
        # if not job_applicant_status:
        #     return

        # job_application_name = frappe.db.get_value("Job Applicant", self.job_applicant, "applicant_name")

        # frappe.msgprint(
        #     _("Do you want to update the Job Applicant {0} as {1} based on this interview result?").format(
        #         frappe.bold(job_application_name), frappe.bold(job_applicant_status)
        #     ),
        #     title=_("Update Job Applicant"),
        #     primary_action={
        #         "label": _("Mark as {0}").format(job_applicant_status),
        #         "server_action": "hrms.hr.doctype.interview.interview.update_job_applicant_status",
        #         "args": {"job_applicant": self.job_applicant, "status": job_applicant_status},
        #     },
        # )
    
    
    
    
    @frappe.whitelist()
    def reschedule_interview(self, scheduled_on, from_time, to_time):
        """ Override this method to Reschedule the interview and send notification to the interviewee."""
        
        if scheduled_on == self.scheduled_on and from_time == self.from_time and to_time == self.to_time:
            frappe.msgprint(
                _("No changes found in timings."), indicator="orange", title=_("Interview Not Rescheduled")
            )
            return

        original_date = self.scheduled_on
        original_from_time = self.from_time
        original_to_time = self.to_time

        job_applicant_status = frappe.get_value("Job Applicant", self.job_applicant, "custom_interview_status") or None
        
        job_applicant_status_field = frappe.get_meta("Job Applicant").get_field("status")
        
        if job_applicant_status:
            if self.status == "Pending" and job_applicant_status != "Rescheduled":
                    
                    new_job_applicant_status = f"{self.interview_round}-Rescheduled"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                    else:
                        print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", self.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", self.job_applicant, "custom_interview_status", "Rescheduled")
                    frappe.db.set_value("Job Applicant", self.job_applicant, "custom_interview_round", self.interview_round)
        else:
            if self.status == "Pending":
                    
                    new_job_applicant_status = f"{self.interview_round}-Rescheduled"
                    
                    if new_job_applicant_status not in job_applicant_status_field.options:
                        options = job_applicant_status_field.options+"\n"+new_job_applicant_status
                        print(f"\n\n Setting options to {options} \n\n")
                    
                        if property_setter:= frappe.db.exists("Property Setter", {"doc_type": "Job Applicant", "field_name": "status", "property": "options"}):
                            print(f"\n\n Creating Property Setter {property_setter}\n\n")
                            frappe.db.set_value("Property Setter", property_setter, "value", options)
                        else:
                            property_setter = frappe.new_doc("Property Setter")
                            property_setter.doctype_or_field = "DocField"
                            property_setter.doc_type = "Job Applicant"
                            property_setter.field_name = "status"
                            property_setter.property = "options"
                            property_setter.property_type = "Select"
                            property_setter.value = options
                            property_setter.insert(ignore_permissions=True)
                        frappe.clear_cache(doctype="Job Applicant")   
                        
                    # else:
                    #     print(f"\n\n {new_job_applicant_status} already exists in options \n\n")    
                    
                    frappe.db.set_value("Job Applicant", self.job_applicant, "status", new_job_applicant_status)
                    frappe.db.set_value("Job Applicant", self.job_applicant, "custom_interview_status", "Scheduled")
                    frappe.db.set_value("Job Applicant", self.job_applicant, "custom_interview_round", self.interview_round)
        
        


        self.db_set({"scheduled_on": scheduled_on, "from_time": from_time, "to_time": to_time})
        self.notify_update()

        recipients = get_recipients(self.name)

        try:
            frappe.sendmail(
                recipients=recipients,
                subject=_("Interview: {0} Rescheduled").format(self.name),
                message=_("Your Interview session is rescheduled from {0} {1} - {2} to {3} {4} - {5}").format(
                    original_date,
                    original_from_time,
                    original_to_time,
                    self.scheduled_on,
                    self.from_time,
                    self.to_time,
                ),
                reference_doctype=self.doctype,
                reference_name=self.name,
            )
        except Exception:
            frappe.msgprint(
                _(
                    "Failed to send the Interview Reschedule notification. Please configure your email account."
                )
            )

        frappe.msgprint(_("Interview Rescheduled successfully"), indicator="green")

class CustomJobOffer(JobOffer):
    def on_change(self):
        """Override the on_change method to stop calling update_job_applicant which updates the status of the job applicant.
        This is to prevent the status from being updated when the job offer status is set to either Accepted or Rejected.
        """
        pass

class CustomAppointmentLetter(AppointmentLetter):
    @frappe.whitelist()
    def send_appointment_letter(self):
        print("\n\n  override successful \n\n")
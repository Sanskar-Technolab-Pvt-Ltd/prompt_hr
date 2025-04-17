import frappe
from frappe import _
from hrms.hr.doctype.job_offer.job_offer import JobOffer

class CustomJobOffer(JobOffer):
    def on_change(self):
        """Override the on_change method to stop calling update_job_applicant which updates the status of the job applicant.
        This is to prevent the status from being updated when the job offer status is set to either Accepted or Rejected.
        """
        pass
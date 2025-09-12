import frappe
from frappe import _
from datetime import datetime, timedelta, time
from frappe.utils import getdate, date_diff, add_days, format_date, add_to_date, today
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest
from prompt_hr.py.auto_mark_attendance import mark_attendance
from hrms.hr.utils import validate_active_employee, validate_dates
from frappe.model.workflow import apply_workflow

class CustomAttendanceRequest(AttendanceRequest):
    def before_insert(self):
        # ? MAKE CUSTOM STATUS PENDING AS WHILE AMENDING IS REMAIN THE PREVIOUS STATUS
        self.custom_status = "Pending"

    def after_insert(self):
        # === SAFE PARSING ===
        if not self.from_date or not self.to_date:
            frappe.msgprint("From Date and To Date are mandatory for Attendance Request.")
            return

        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        today = getdate()
        # === EDGE CASE: FROM > TO ===
        if from_date > to_date:
            frappe.throw("From Date cannot be after To Date.")

        # === MAIN LOGIC: ONLY SWITCH IF TODAY FALLS IN RANGE ===
        if from_date <= today <= to_date:
            if self.reason in ["On Duty", "Work From Home"]:
                frappe.db.set_value(
                    "Employee",
                    self.employee,
                    "custom_attendance_capture_scheme",
                    "Mobile-Web Checkin-Checkout",
                )

    def validate(self):
        validate_active_employee(self.employee)
        validate_dates(self, self.from_date, self.to_date, False)
        self.validate_half_day()
        self.validate_request_overlap()

        if self.custom_status == "Pending":
            self.validate_no_attendance_to_create()
            attendance_exists = get_existing_attendance(self.employee, self.from_date, self.to_date)
            if attendance_exists:
                attendance_list_str = "<br>".join(
                    [f"{format_date(a['attendance_date'])} - {a['name']} ({a['status']})" for a in attendance_exists]
                )
                frappe.throw(
                    f"Attendance already exists for the following date(s):<br>{attendance_list_str}",
                )

    def on_submit(self):
        pass

    def on_cancel(self):
        if self.workflow_state:
            self.db_set("workflow_state", "Cancelled")
        return super().on_cancel()

@frappe.whitelist()
def handle_custom_workflow_action(doc, action, reason_for_rejection=None):
    try:
        if isinstance(doc, str):
            doc = frappe.parse_json(doc)
        if action == "Approve":
            #! ENQUEUE BACKGROUND JOB
            frappe.enqueue(
                process_attendance_and_penalties,
                doc=doc,
                now=False,
            )

            #! GIVE USER MESSAGE
            frappe.msgprint(
                "Your request has been approved and is being processed in the background. "
                "It may take a few minutes to update attendance and penalties. "
                "If it is still not approved after some time, please contact the HR Department."
            )
        elif action == "Reject":
            frappe.enqueue(
                process_rejection_penalties,
                doc=doc,
                now=False,
            )
            if doc.get("doctype") == "Attendance Request" and doc.get("name") and reason_for_rejection:
                frappe.db.set_value("Attendance Request", doc.get("name"),"custom_reason_for_rejection", reason_for_rejection)
                
            frappe.msgprint(
                "Your request has been rejected. No-attendance penalties are being processed "
                "in the background."
            )
        else:
            apply_workflow(doc, action)
    except Exception as e:
        frappe.log_error(
            f"Error in handle_custom_workflow_action",str(e)
        )


def process_attendance_and_penalties(doc):
    try:
        from_date = getdate(doc.get("from_date"))
        to_date = min(getdate(doc.get("to_date")), getdate(add_to_date(today(), days=-1, as_string=True)))
        frappe.db.set_value("Attendance Request", doc.get("name"), "custom_status", "Approved")
        process_attendance_request(from_date, to_date, doc, approved_attendance_request=doc.get("name"))
        apply_workflow(doc, "Approve")
    except Exception as e:
        frappe.log_error(
            f"Error in process_attendance_and_penalties",str(e)
        )

def process_rejection_penalties(doc):
    try:
        from_date = getdate(doc.get("from_date"))
        to_date = min(getdate(doc.get("to_date")), getdate(add_to_date(today(), days=-1, as_string=True)))
        frappe.db.set_value("Attendance Request", doc.get("name"), "custom_status", "Rejected")

        if doc.get("reason") == "Partial Day":
            process_attendance_request(from_date, to_date, doc)
        else:
            today_date = getdate()
            if getdate(doc.get("to_date")) >= today_date:
                delete_employee_checkin(today_date, doc.get("employee"))
    except Exception as e:
        frappe.log_error(
            f"Error in process_rejection_penalties",str(e)
        )
    
    apply_workflow(doc, "Reject")


def process_attendance_request(from_date, to_date, doc, approved_attendance_request=None):
    """
    PROCESS ATTENDANCE REQUEST WITH PENALTY AND WARNING LOGIC

    ARGS:
        FROM_DATE (DATE): START DATE OF ATTENDANCE PROCESSING
        TO_DATE (DATE): END DATE OF ATTENDANCE PROCESSING
        DOC (DOCUMENT): EMPLOYEE DOCUMENT REFERENCE
        APPROVED_ATTENDANCE_REQUEST (STR, OPTIONAL): LINKED APPROVED REQUEST
    """

    #! DATE RANGE
    dates = [add_days(from_date, i) for i in range(date_diff(to_date, from_date) + 1)]

    for date in dates:
        try:
            #? MARK ATTENDANCE
            mark_attendance(
                attendance_date=date,
                company=doc.company,
                is_scheduler=0,
                regularize_attendance=0,
                attendance_id=None,
                regularize_start_time=None,
                regularize_end_time=None,
                emp_id=doc.employee,
                approved_attendance_request=approved_attendance_request
            )
        except Exception as e:
            frappe.log_error(
                f"Error in Merk Attendance for date {date}", str(e)
            )
            continue


def get_existing_attendance(employee, from_date, to_date):
    """
    Returns a list of Attendance names for the employee between from_date and to_date,
    excluding cancelled records (docstatus != 2)
    """
    # if from_date == to_date:

    attendance_list = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": ["!=", 2]
        },
        fields=["name", "attendance_date", "status"],
        order_by = "attendance_date asc"
    )

    return attendance_list


def delete_employee_checkin(date, employee):
    """
    DELETES ALL EMPLOYEE CHECKIN RECORDS FOR THE GIVEN DATE AND EMPLOYEE,
    WHERE DEVICE_ID IS NOT SET. RETURNS A DICT WITH 'TIME' AS KEY AND 'LOG_TYPE' AS VALUE.
    RETURNS EMPTY DICT IF NO RECORDS FOUND.
    """
    try:
        if not employee or not date:
            return {}

        start_datetime = datetime.combine(date, time.min)  # 00:00:00
        end_datetime = datetime.combine(date, time.max)    # 23:59:59.999999
        # Fetch checkins including the 'time' and 'log_type' fields
        employee_checkins = frappe.db.get_all(
            "Employee Checkin",
            filters={
                "employee": employee,
                "device_id": ["is", "not set"],
                "time": ["between", [start_datetime, end_datetime]],
            },
            fields=["name", "time", "log_type"],
        )

        # Build dictionary {time: log_type}
        time_log_dict = {checkin['time']: checkin['log_type'] for checkin in employee_checkins}

        # Delete all matching checkins by filters, in one call
        frappe.db.delete(
            "Employee Checkin",
            filters={
                "employee": employee,
                "device_id": ["is", "not set"],
                "time": ["between", [start_datetime, end_datetime]],
            },
        )

        return time_log_dict

    except Exception as e:
        frappe.log_error(f"Error in delete_employee_checkin: {str(e)}")
        return {}

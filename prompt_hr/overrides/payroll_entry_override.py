import frappe
from frappe import _
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry, get_employee_list
from prompt_hr.py.salary_slip_overriden_methods import custom_create_salary_slips_for_employees
from frappe.query_builder.functions import Coalesce
from hrms.payroll.doctype.salary_withholding.salary_withholding import link_bank_entry_in_salary_withholdings


class CustomPayrollEntry(PayrollEntry):

    def before_save(self):
        # ? Track seen combinations of (employee, lop_month)
        seen = set()

        for row in self.custom_lop_reversal_details:
            # * Ensure default values if None
            actual_lop_days = row.actual_lop_days or 0
            lop_reversal_days = row.lop_reversal_days or 0

            # ! Check if LOP Reversal Days exceed Actual LOP Days
            if lop_reversal_days > actual_lop_days:
                frappe.throw(
                    _("Row {0}: LOP Reversal Days ({1}) cannot be greater than Actual LOP Days ({2}).").format(
                        row.idx, lop_reversal_days, actual_lop_days
                    )
                )

            # ! Check for duplicate Employee + Month
            key = (row.employee, row.lop_month)
            if key in seen:
                frappe.throw(
                    _("Row {0}: Duplicate combination of Employee '{1}' and LOP Month '{2}' is not allowed.").format(
                        row.idx, row.employee, row.lop_month
                    )
                )
            seen.add(key)
        
        # ? VALIDATE ADHOC SALARY DETAILS BEFORE SAVE
        if self.custom_adhoc_salary_details:
            adhoc_salary_pair = set()
            for row in self.custom_adhoc_salary_details:

                # ! Ensure mandatory fields are filled if the row exists
                if not row.employee or not row.salary_component:
                    frappe.throw(
                        _("Row {0}: 'Employee' and 'Salary Component' are required fields.").format(row.idx)
                    )

                # * Assign a default of 0 if amount is None
                amount = row.amount or 0

                # ! Prevent records with zero amount
                if amount == 0:
                    frappe.throw(
                        _("{0}: Amount cannot be zero.").format(row.salary_component)
                    )

                # ! Check for duplicate Employee + Salary Component
                key = (row.employee, row.salary_component)
                if key in adhoc_salary_pair:
                    frappe.throw(
                        _("Row {0}: Duplicate combination of Employee '{1}' and Salary Component '{2}' is not allowed.").format(
                            row.idx, row.employee, row.salary_component
                        )
                    )
                adhoc_salary_pair.add(key)
    
    
    def before_submit(self):
        super().before_submit()
        check_step_completed(self)
    
    def on_submit(self):
        super().on_submit()

        # * Get PROMPT abbreviation from HR Settings
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")

        # * Get abbreviation of the company selected in the payroll entry
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")

        # ? APPLY RESTRICTION ONLY FOR PROMPT
        if company_abbr == prompt_abbr:
            restricted_employees = list({
                row.employee for row in self.custom_remaining_payroll_details if row.employee
            })

            if restricted_employees:
                # Update employees list on current doc (self), so it's saved correctly and reflected on frontend
                self.set("employees", [])

                for emp in restricted_employees:
                    self.append("employees", {
                        "employee": emp
                    })

                # Save current doc with updated employee list
                self.save(ignore_permissions=True)

    def get_sal_slip_list(self, ss_status, as_dict=False):
        """
        Returns list of salary slips based on selected criteria
        """
        ss = frappe.qb.DocType("Salary Slip")
        ss_list = (
            frappe.qb.from_(ss)
            .select(ss.name, ss.salary_structure)
            .where(
                (ss.docstatus == ss_status)
                # & (ss.start_date >= self.start_date)
                # & (ss.end_date <= self.end_date)
                & (ss.payroll_entry == self.name)
                & ((ss.journal_entry.isnull()) | (ss.journal_entry == ""))
                & (Coalesce(ss.salary_slip_based_on_timesheet, 0) == self.salary_slip_based_on_timesheet)
            )
        ).run(as_dict=as_dict)
        return ss_list

    @frappe.whitelist()
    def fill_employee_details(self):
        # * Get PROMPT abbreviation from HR Settings
        prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")

        # * Get abbreviation of the company selected in the payroll entry
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")

        # ? APPLY LOGIC ONLY FOR PROMPT
        if company_abbr == prompt_abbr and self.custom_is_salary_slip_created:
            result = self.update_fill_employee_details()

            # Get restricted employees from child table
            restricted_employees = {
                row.employee for row in self.custom_remaining_payroll_details if row.employee
            }

            # Filter employees to keep only restricted ones
            self.employees = [
                emp for emp in self.employees if emp.get("employee") in restricted_employees
            ]

            # Update employee count
            self.number_of_employees = len(self.employees)

            return result

        # Fallback to default behavior for other companies
        return self.update_fill_employee_details()
    
    def update_fill_employee_details(self):
        filters = self.make_filters()
        # ! Add custom employment type and custom business unit filter if available
        if filters:
            filters.update(dict(employment_type=self.custom_employment_type))
            filters.update(dict(custom_business_unit=self.custom_business_unit))

        employees = get_employee_list(filters=filters, as_dict=True, ignore_match_conditions=True)
        self.set("employees", [])

        if not employees:
            error_msg = _(
                "No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
            ).format(
                frappe.bold(self.company),
                frappe.bold(self.currency),
                frappe.bold(self.payroll_payable_account),
            )
            if self.branch:
                error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
            if self.department:
                error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
            # ? ADD ERROR MESSAGE FOR EMPLOYMENT TYPE
            if self.custom_employment_type:
                error_msg += "<br>" + _("Employment Type: {0}").format(frappe.bold(self.custom_employment_type))
            # ? ADD ERROR MESSAGE FOR BUSINESS UNIT
            if self.custom_business_unit:
                error_msg += "<br>" + _("Business Unit: {0}").format(frappe.bold(self.custom_business_unit))
            if self.designation:
                error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
            if self.start_date:
                error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
            if self.end_date:
                error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
            frappe.throw(error_msg, title=_("No employees found"))

        self.set("employees", employees)
        self.number_of_employees = len(self.employees)
        self.update_employees_with_withheld_salaries()

        if employees:
            # ? SET EMPLOYEE COUNT AND APPEND IN PENDING FNF TABLE
            self.append_exit_employees(employees)
        
        
        return self.get_employees_with_unmarked_attendance()
    

    @frappe.whitelist()
    def make_bank_entry(self, for_withheld_salaries=False, is_withheld_salary=0, selected_employees=[]):
        self.check_permission("write")
        self.employee_based_payroll_payable_entries = {}

        employee_wise_accounting_enabled = frappe.db.get_single_value(
            "Payroll Settings",
            "process_payroll_accounting_entry_based_on_employee"
        )

        # ? NOT CREATE BANK ENTRY FOR WITHHELD EMPLOYEE
        pending_withheld =  completed_withheld = []
        try:
            salary_withheld = frappe.get_all(
                "Hold Salary",
                filters={
                    "parent": self.name,
                    "parentfield": "custom_salary_withholding_details"
                },
                fields=["employee", "is_bank_entry_created"]
            )
            pending_withheld = [
                row.employee for row in salary_withheld
                if not row.is_bank_entry_created
            ]

            completed_withheld = [
                row.employee for row in salary_withheld
                if row.is_bank_entry_created
            ]

        except Exception as e:
            frappe.log_error("Error in make_bank_entry", e)
        
        # ! REMOVE EMPLOYEE IN WITHHELD SALARY FROM MAKING BANK ENTRY
        salary_slip_total = 0
        salary_details = self.get_salary_slip_details(for_withheld_salaries)

        if not is_withheld_salary:
            salary_details = [
                d for d in salary_details
                if d.employee not in pending_withheld and d.employee not in completed_withheld
            ]

        else:
            salary_details = get_remaining_bank_entry_salary_slip_details(self)
            salary_details = [
                d for d in salary_details
                if d.employee in pending_withheld and d.employee in selected_employees
            ]


        for salary_detail in salary_details:

            # ✅ Earnings
            if salary_detail.parentfield == "earnings":
                (
                    is_flexible_benefit,
                    only_tax_impact,
                    create_separate_je,
                    statistical_component,
                ) = frappe.db.get_value(
                    "Salary Component",
                    salary_detail.salary_component,
                    (
                        "is_flexible_benefit",
                        "only_tax_impact",
                        "create_separate_payment_entry_against_benefit_claim",
                        "statistical_component",
                    ),
                    cache=True,
                )

                if only_tax_impact != 1 and statistical_component != 1:
                    if is_flexible_benefit == 1 and create_separate_je == 1:
                        self.set_accounting_entries_for_bank_entry(
                            salary_detail.amount,
                            salary_detail.salary_component
                        )
                    else:
                        if employee_wise_accounting_enabled:
                            self.set_employee_based_payroll_payable_entries(
                                "earnings",
                                salary_detail.employee,
                                salary_detail.amount,
                                salary_detail.salary_structure,
                            )
                        salary_slip_total += salary_detail.amount

            # ✅ Deductions
            if salary_detail.parentfield == "deductions":
                statistical_component = frappe.db.get_value(
                    "Salary Component",
                    salary_detail.salary_component,
                    "statistical_component",
                    cache=True
                )

                if not statistical_component:
                    if employee_wise_accounting_enabled:
                        self.set_employee_based_payroll_payable_entries(
                            "deductions",
                            salary_detail.employee,
                            salary_detail.amount,
                            salary_detail.salary_structure,
                        )

                    salary_slip_total -= salary_detail.amount

        # ? Loan Repayment
        total_loan_repayment = (
            self.process_loan_repayments_for_bank_entry(salary_details) or 0
        )
        salary_slip_total -= total_loan_repayment

        # ? Create Bank Entry
        bank_entry = None
        if salary_slip_total > 0:
            remark = "withheld salaries" if for_withheld_salaries else "salaries"
            bank_entry = self.set_accounting_entries_for_bank_entry(
                salary_slip_total,
                remark
            )

            if for_withheld_salaries:
                link_bank_entry_in_salary_withholdings(salary_details, bank_entry.name)

        if is_withheld_salary:
            # ? After successfully making bank entry check bank entry created in Salary Withholding Details
            for emp in pending_withheld:
                if emp in selected_employees:
                    frappe.db.set_value(
                        "Hold Salary",
                        {
                            "parent": self.name,
                            "parentfield": "custom_salary_withholding_details",
                            "employee": emp
                        },
                        "is_bank_entry_created",
                        1
                    )


        return bank_entry


    def append_exit_employees(self, employees):                        
        eligible_employees = [row.get("employee") for row in employees]
        
        if not eligible_employees:
            # ? CLEAR EXISTING CHILD TABLE
            # frappe.db.delete("Pending FnF Details", {"parent": self.name})
            self.custom_pending_fnf_details = []
            self.custom_exit_employees_count = 0
            # frappe.db.set_value("Payroll Entry", self.name, "custom_exit_employees_count", 0)

        exit_employees = frappe.get_all(
            "Employee",
            filters={
                "name": ["in", eligible_employees],
                "relieving_date": ["between", [self.start_date, self.end_date]],
            },
            fields=["name", "employee_name"],
        )
        
        exit_employee_ids = [emp["name"] for emp in exit_employees]
        
        # ? FETCH FULL AND FINAL STATEMENTS FOR THESE EMPLOYEES
        fnf_records = frappe.get_all(
            "Full and Final Statement",
            filters={"employee": ["in", exit_employee_ids], "docstatus": 0, "custom_payroll_entry": self.name},
            fields=["employee", "name"],
        )
        
        # ? MAP EMPLOYEE → FNF RECORD
        fnf_record_map = {record["employee"]: record["name"] for record in fnf_records}
        fnf_employees = set(fnf_record_map.keys())
        
        # ? SET EMPLOYEE COUNT
        # frappe.db.set_value(
        #     "Payroll Entry", self.name, "custom_exit_employees_count", len(exit_employee_ids)
        # )
        self.custom_exit_employees_count = len(exit_employee_ids)
        
        self.custom_pending_fnf_details = []
        
        for emp in exit_employees:
            self.append("custom_pending_fnf_details",{
                "employee": emp["name"],
                "employee_name": emp.get("employee_name") or "Unknown",
                "is_fnf_processed": 1 if emp["name"] in fnf_employees else 0,
                "fnf_record": fnf_record_map.get(emp["name"]),
            })
            # frappe.get_doc(
            #     {
            #         "doctype": "Pending FnF Details",
            #         "parent": self.name,
            #         "parenttype": "Payroll Entry",
            #         "parentfield": "custom_pending_fnf_details",
            #         "employee": emp["name"],
            #         "employee_name": emp.get("employee_name") or "Unknown",
            #         "is_fnf_processed": 1 if emp["name"] in fnf_employees else 0,
            #         "fnf_record": fnf_record_map.get(emp["name"]),
            #     }
            # ).insert(ignore_permissions=True)
        
        #? LINK PAYROLL ENTRY TO ALL THE FNF RECORDS LINKED IN THE PENDING FNF DETAILS TABLE
        for fnf_id in fnf_records:
            frappe.db.set_value("Full and Final Statement", fnf_id.get("name"), "custom_payroll_entry", self.name)
            
            
    @frappe.whitelist()
    def create_salary_slips(self):  
        """
        Creates salary slip for selected employees if already not created
        """
        
        self.check_permission("write")

        check_step_completed(self)
        not_create_slips = []
        # if self.custom_salary_withholding_details:
        #     not_create_slips = [
        #         emp.employee for emp in self.custom_salary_withholding_details if (self.start_date <= emp.from_date <= self.end_date and self.start_date <= emp.to_date <= self.end_date) and emp.withholding_type == "Hold Salary Processing"
        #     ]
        
        skip_salary_slip_creation = False
        for emp in self.employees:
            
            skip_salary_slip_creation = False
            for fnf in self.custom_pending_fnf_details:
                print(f"\n\n Teressfdfsd \n\n")
                if fnf.employee == emp.employee:
                    print(f"\n\n FOUND EMP \n\n")
                    if fnf.fnf_record:
                        fnf_status = frappe.db.get_value("Full and Final Statement", fnf.fnf_record, "docstatus")
                        if fnf_status != 1:
                            frappe.msgprint(f"Please Submit Full and Final Statement for employee {emp.employee}")
                            skip_salary_slip_creation = True
                            break
                    else:
                        print(f"\n\n fnf Records not Found \n\n")
                        frappe.msgprint(f"Please Create and Submit Full and Final Statement for employee {emp.employee}")						
                        skip_salary_slip_creation = True
                        break

            if skip_salary_slip_creation:
                continue
                    
        
        employees = [emp.employee for emp in self.employees if emp.employee not in not_create_slips] 

        if employees:
            args = frappe._dict(
                {
                    "salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
                    "payroll_frequency": self.payroll_frequency,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "company": self.company,
                    "posting_date": self.posting_date,
                    "deduct_tax_for_unclaimed_employee_benefits": self.deduct_tax_for_unclaimed_employee_benefits,
                    "deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
                    "payroll_entry": self.name,
                    "exchange_rate": self.exchange_rate,
                    "currency": self.currency,
                }
            )
            if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
                self.db_set("status", "Queued")
                frappe.enqueue(
                    custom_create_salary_slips_for_employees,
                    timeout=3000,
                    employees=employees,
                    args=args,
                    publish_progress=False,
                )
                frappe.msgprint(
                    _("Salary Slip creation is queued. It may take a few minutes"),
                    alert=True,
                    indicator="blue",
                )
            else:
                custom_create_salary_slips_for_employees(employees, args, publish_progress=False)
                # since this method is called via frm.call this doc needs to be updated manually
                self.reload()

def custom_set_filter_conditions(query, filters, qb_object):
    """Append optional filters to employee query"""

    if filters.get("employees"):
        query = query.where(qb_object.name.notin(filters.get("employees")))
        print("employees filter:", filters.get("employees"))
    # ? ADD EMPLOYMENT TYPE AND BUSINESS UNIT in LIST
    for fltr_key in ["branch", "department", "designation", "grade", "employment_type", "custom_business_unit"]:
        if filters.get(fltr_key):
            query = query.where(qb_object[fltr_key] == filters[fltr_key])

    return query

def check_step_completed(self):
    """
    #! CHECK IF ALL REQUIRED PAYROLL STEPS ARE COMPLETED BEFORE FINALIZATION
    """
    #? REQUIRED PAYROLL STEPS WITH USER MESSAGES
    step_fields = {
        "custom_new_joinee_and_exit_step_completed": "New Joinee and Exit step is incomplete.",
        "custom_leave_and_attendance_step_completed": "Leave and Attendance step is incomplete.",
        "custom_adhoc_salary_adjustment_step_completed": "Adhoc Salary Adjustment step is incomplete.",
        "custom_restricted_salary_step_completed": "Restricted Salary step is incomplete.",
        "custom_salary_withholding_step_completed": "Salary Withholding step is incomplete.",
    }

    #? COLLECT INCOMPLETE STEPS
    messages = [msg for field, msg in step_fields.items() if not self.get(field)]

    #? THROW IF ANY STEP IS INCOMPLETE
    if messages:
        frappe.throw("<br>".join(messages), title="Incomplete Payroll Steps")


# ? TO GET SALARY SLIP DETAILS OF ONLY PENDING BANKE ENTRY EMPLOYEE
def get_remaining_bank_entry_salary_slip_details(self):
    SalarySlip = frappe.qb.DocType("Salary Slip")
    SalaryDetail = frappe.qb.DocType("Salary Detail")

    query = (
        frappe.qb.from_(SalarySlip)
        .join(SalaryDetail)
        .on(SalarySlip.name == SalaryDetail.parent)
        .select(
            SalarySlip.name,
            SalarySlip.employee,
            SalarySlip.salary_structure,
            SalarySlip.salary_withholding_cycle,
            SalaryDetail.salary_component,
            SalaryDetail.amount,
            SalaryDetail.parentfield,
        )
        .where(
            (SalarySlip.docstatus == 1)
            & (SalarySlip.start_date >= self.start_date)
            & (SalarySlip.end_date <= self.end_date)
            & (SalarySlip.payroll_entry == self.name)
            & (
                (SalaryDetail.do_not_include_in_total == 0)
                | (
                    (SalaryDetail.do_not_include_in_total == 1)
                    & (SalaryDetail.do_not_include_in_accounts == 0)
                )
            )
        )
    )

    if "lending" in frappe.get_installed_apps():
        query = query.select(SalarySlip.total_loan_repayment)


    return query.run(as_dict=True)

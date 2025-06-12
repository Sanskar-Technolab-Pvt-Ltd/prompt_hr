from hrms.hr.doctype.leave_allocation.test_leave_allocation import TestLeaveAllocation, create_leave_allocation
import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, add_months, getdate, nowdate, flt
import unittest
import erpnext
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.leave_allocation.leave_allocation import (
	BackDatedAllocationError,
	OverAllocationError,
)
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import process_expired_allocation
from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type
from prompt_hr.py.leave_allocation import check_carry_forward_criteria

class CustomTestLeaveAllocation(unittest.TestCase):
    def setUp(self):
        frappe.db.delete("Leave Period")
        frappe.db.delete("Leave Allocation")
        frappe.db.delete("Leave Application")
        frappe.db.delete("Leave Ledger Entry")

        emp_id = make_employee("test_leave_allocation@salary.com", company="_Test Company")
        self.employee = frappe.get_doc("Employee", emp_id)


    def test_carry_forward_leaves_expiry(self):
        # Create leave type with carry forward and expiry rule
        create_leave_type(
            leave_type_name="_Test_CF_leave_expiry",
            is_carry_forward=1,
            expire_carry_forwarded_leaves_after_days=90,
        )

        # Initial leave allocation (past year, no carry forward)
        leave_allocation = create_leave_allocation(
            employee=self.employee.name,
            employee_name=self.employee.employee_name,
            leave_type="_Test_CF_leave_expiry",
            from_date=add_months(nowdate(), -24),
            to_date=add_months(nowdate(), -12),
            carry_forward=0,
        )
        leave_allocation.submit()

        # Current leave allocation with carry forward enabled
        leave_allocation = create_leave_allocation(
            employee=self.employee.name,
            employee_name=self.employee.employee_name,
            leave_type="_Test_CF_leave_expiry",
            from_date=add_days(nowdate(), -90),
            to_date=add_days(nowdate(), 100),
            carry_forward=1,
        )
        leave_allocation.submit()

        # Expire old carry forwarded leaves
        process_expired_allocation()

        # New future leave allocation (should carry forward only remaining valid leaves)
        leave_allocation_1 = create_leave_allocation(
            employee=self.employee.name,
            employee_name=self.employee.employee_name,
            leave_type="_Test_CF_leave_expiry",
            from_date=add_months(nowdate(), 6),
            to_date=add_months(nowdate(), 12),
            carry_forward=1,
        )
        leave_allocation_1.submit()

        # Validate carry forward logic
        if leave_allocation_1.carry_forward:
            employee_doc = frappe.get_doc("Employee", leave_allocation_1.employee)
            leave_type = frappe.get_doc("Leave Type", leave_allocation_1.leave_type)

            # Check limit for carry forward
            carry_forward_limit = check_carry_forward_criteria(employee_doc, leave_type)

            if carry_forward_limit:
                # If within allowed limit
                if not (leave_allocation_1.unused_leaves > carry_forward_limit):
                    self.assertEqual(
                        leave_allocation_1.unused_leaves, leave_allocation.new_leaves_allocated
                    )

                # If CTC limit exists and is exceeded
                if leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                        leave_allocation_1.unused_leaves = min(
                            leave_allocation_1.unused_leaves,
                            leave_type.maximum_carry_forwarded_leaves,
                        )
                    else:
                        self.assertEqual(
                            leave_allocation_1.unused_leaves, leave_allocation.new_leaves_allocated
                        )
                else:
                    self.assertEqual(
                        leave_allocation_1.unused_leaves, leave_allocation.new_leaves_allocated
                    )

    def test_carry_forward_leaves_expiry_after_partially_used_leaves(self):
        from hrms.payroll.doctype.salary_slip.test_salary_slip import make_leave_application

        # Create carry-forward enabled leave type with expiry after 90 days
        leave_type = create_leave_type(
            leave_type_name="_Test_CF_leave_expiry",
            is_carry_forward=1,
            expire_carry_forwarded_leaves_after_days=90,
        )

        # Initial leave allocation of 5 days (no carry forward)
        leave_allocation = create_leave_allocation(
            employee=self.employee.name,
            leave_type="_Test_CF_leave_expiry",
            from_date=add_months(nowdate(), -24),
            to_date=add_months(nowdate(), -12),
            new_leaves_allocated=5,
            carry_forward=0,
        )
        leave_allocation.submit()

        # Next allocation that carries forward previous 5 + 15 new = 20 (potential)
        leave_allocation = create_leave_allocation(
            employee=self.employee.name,
            leave_type="_Test_CF_leave_expiry",
            from_date=add_days(nowdate(), -90),
            to_date=add_days(nowdate(), 100),
            carry_forward=1,
        )
        leave_allocation.submit()

        # Apply for 3 days leave — leaves used
        make_leave_application(
            self.employee.name,
            leave_allocation.from_date,
            add_days(leave_allocation.from_date, 2),
            leave_type.name,
        )

        # Process expiry of carry-forwarded leaves after 90 days
        process_expired_allocation()

        # Fetch expired leave entry
        expired_leaves = frappe.db.get_value(
            "Leave Ledger Entry",
            dict(
                transaction_name=leave_allocation.name,
                is_expired=1,
                is_carry_forward=1,
            ),
            "leaves",
        )

        if leave_allocation.carry_forward:
            # Get related docs
            employee_doc = frappe.get_doc("Employee", leave_allocation.employee)
            leave_type = frappe.get_doc("Leave Type", leave_allocation.leave_type)

            # Get carry forward criteria
            carry_forward_limit = check_carry_forward_criteria(employee_doc, leave_type)

            if carry_forward_limit:
                if not (leave_allocation.unused_leaves > carry_forward_limit):
                    self.assertEqual(expired_leaves, -2)  # 5 carried - 3 used = 2 expired

                if leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                        leave_allocation.unused_leaves = min(
                            leave_allocation.unused_leaves,
                            leave_type.maximum_carry_forwarded_leaves,
                        )
                    else:
                        self.assertEqual(expired_leaves, -2)
                else:
                    self.assertEqual(expired_leaves, -2)

    def test_leave_addition_after_submit_with_carry_forward(self):
        from hrms.hr.doctype.leave_application.test_leave_application import create_carry_forwarded_allocation

        leave_type = create_leave_type(
            leave_type_name="_Test_CF_leave_expiry",
            is_carry_forward=1,
            include_holiday=True,
        )

        leave_allocation = create_carry_forwarded_allocation(self.employee, leave_type)

        if leave_allocation.carry_forward:
            employee_doc = frappe.get_doc("Employee", leave_allocation.employee)
            leave_type = frappe.get_doc("Leave Type", leave_allocation.leave_type)
            carry_forward_limit = check_carry_forward_criteria(employee_doc, leave_type)

            if carry_forward_limit and not (leave_allocation.unused_leaves > carry_forward_limit):
                self.assertEqual(leave_allocation.total_leaves_allocated, 30)

                leave_allocation.new_leaves_allocated = 32
                leave_allocation.save()
                leave_allocation.reload()

                updated_entry = frappe.db.get_all(
                    "Leave Ledger Entry",
                    {"transaction_name": leave_allocation.name},
                    pluck="leaves",
                    order_by="creation desc",
                    limit=1,
                )

                self.assertEqual(updated_entry[0], 17)
                self.assertEqual(leave_allocation.total_leaves_allocated, 47)

            if leave_type.custom_maximum_ctc_limit_for_carry_forward:
                if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    leave_allocation.unused_leaves = min(
                        leave_allocation.unused_leaves,
                        leave_type.maximum_carry_forwarded_leaves,
                    )
                else:
                    self.assertEqual(leave_allocation.total_leaves_allocated, 30)

                    leave_allocation.new_leaves_allocated = 32
                    leave_allocation.save()
                    leave_allocation.reload()

                    updated_entry = frappe.db.get_all(
                        "Leave Ledger Entry",
                        {"transaction_name": leave_allocation.name},
                        pluck="leaves",
                        order_by="creation desc",
                        limit=1,
                    )

                    self.assertEqual(updated_entry[0], 17)
                    self.assertEqual(leave_allocation.total_leaves_allocated, 47)
            else:
                self.assertEqual(leave_allocation.total_leaves_allocated, 30)

                leave_allocation.new_leaves_allocated = 32
                leave_allocation.save()
                leave_allocation.reload()

                updated_entry = frappe.db.get_all(
                    "Leave Ledger Entry",
                    {"transaction_name": leave_allocation.name},
                    pluck="leaves",
                    order_by="creation desc",
                    limit=1,
                )

                self.assertEqual(updated_entry[0], 17)
                self.assertEqual(leave_allocation.total_leaves_allocated, 47)

    def test_leave_subtraction_after_submit(self):
        leave_allocation = create_leave_allocation(
            employee=self.employee.name,
            employee_name=self.employee.employee_name
        )
        leave_allocation.submit()
        leave_allocation.reload()

        if leave_allocation.carry_forward:
            employee_doc = frappe.get_doc("Employee", leave_allocation.employee)
            leave_type = frappe.get_doc("Leave Type", leave_allocation.leave_type)
            carry_forward_limit = check_carry_forward_criteria(employee_doc, leave_type)

            if carry_forward_limit and not (leave_allocation.unused_leaves > carry_forward_limit):
                self.assertEqual(leave_allocation.total_leaves_allocated, 15)

                leave_allocation.new_leaves_allocated = 10
                leave_allocation.submit()
                leave_allocation.reload()

                updated_entry = frappe.db.get_all(
                    "Leave Ledger Entry",
                    {"transaction_name": leave_allocation.name},
                    pluck="leaves",
                    order_by="creation desc",
                    limit=1,
                )

                self.assertEqual(updated_entry[0], -5)
                self.assertEqual(leave_allocation.total_leaves_allocated, 10)

            if leave_type.custom_maximum_ctc_limit_for_carry_forward:
                if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    leave_allocation.unused_leaves = min(
                        leave_allocation.unused_leaves,
                        leave_type.maximum_carry_forwarded_leaves,
                    )
                else:
                    self.assertEqual(leave_allocation.total_leaves_allocated, 15)

                    leave_allocation.new_leaves_allocated = 10
                    leave_allocation.submit()
                    leave_allocation.reload()

                    updated_entry = frappe.db.get_all(
                        "Leave Ledger Entry",
                        {"transaction_name": leave_allocation.name},
                        pluck="leaves",
                        order_by="creation desc",
                        limit=1,
                    )

                    self.assertEqual(updated_entry[0], -5)
                    self.assertEqual(leave_allocation.total_leaves_allocated, 10)
            else:
                self.assertEqual(leave_allocation.total_leaves_allocated, 15)

                leave_allocation.new_leaves_allocated = 10
                leave_allocation.submit()
                leave_allocation.reload()

                updated_entry = frappe.db.get_all(
                    "Leave Ledger Entry",
                    {"transaction_name": leave_allocation.name},
                    pluck="leaves",
                    order_by="creation desc",
                    limit=1,
                )

                self.assertEqual(updated_entry[0], -5)
                self.assertEqual(leave_allocation.total_leaves_allocated, 10)

    def test_leave_subtraction_after_submit_with_carry_forward(self):
        from hrms.hr.doctype.leave_application.test_leave_application import create_carry_forwarded_allocation

        leave_type = create_leave_type(
            leave_type_name="_Test_CF_leave_expiry",
            is_carry_forward=1,
            include_holiday=True,
        )

        leave_allocation = create_carry_forwarded_allocation(self.employee, leave_type)

        if leave_allocation.carry_forward:
            employee_doc = frappe.get_doc("Employee", leave_allocation.employee)
            leave_type = frappe.get_doc("Leave Type", leave_allocation.leave_type)
            carry_forward_limit = check_carry_forward_criteria(employee_doc, leave_type)

            if carry_forward_limit and not (leave_allocation.unused_leaves > carry_forward_limit):
                self.assertEqual(leave_allocation.total_leaves_allocated, 30)

                leave_allocation.new_leaves_allocated = 8
                leave_allocation.save()

                updated_entry = frappe.db.get_all(
                    "Leave Ledger Entry",
                    {"transaction_name": leave_allocation.name},
                    pluck="leaves",
                    order_by="creation desc",
                    limit=1,
                )

                self.assertEqual(updated_entry[0], -7)
                self.assertEqual(leave_allocation.total_leaves_allocated, 23)

            if leave_type.custom_maximum_ctc_limit_for_carry_forward:
                if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    leave_allocation.unused_leaves = min(
                        leave_allocation.unused_leaves,
                        leave_type.maximum_carry_forwarded_leaves,
                    )
                else:
                    self.assertEqual(leave_allocation.total_leaves_allocated, 30)

                    leave_allocation.new_leaves_allocated = 8
                    leave_allocation.save()

                    updated_entry = frappe.db.get_all(
                        "Leave Ledger Entry",
                        {"transaction_name": leave_allocation.name},
                        pluck="leaves",
                        order_by="creation desc",
                        limit=1,
                    )

                    self.assertEqual(updated_entry[0], -7)
                    self.assertEqual(leave_allocation.total_leaves_allocated, 23)
            else:
                self.assertEqual(leave_allocation.total_leaves_allocated, 30)

                leave_allocation.new_leaves_allocated = 8
                leave_allocation.save()

                updated_entry = frappe.db.get_all(
                    "Leave Ledger Entry",
                    {"transaction_name": leave_allocation.name},
                    pluck="leaves",
                    order_by="creation desc",
                    limit=1,
                )

                self.assertEqual(updated_entry[0], -7)
                self.assertEqual(leave_allocation.total_leaves_allocated, 23)

    @change_settings("System Settings", {"float_precision": 2})
    def test_precision(self):
        create_leave_type(
            leave_type_name="_Test_CF_leave",
            is_carry_forward=1,
        )

        # Initial leave allocation = 0.416333
        leave_allocation = create_leave_allocation(
            employee=self.employee.name,
            new_leaves_allocated=0.416333,
            leave_type="_Test_CF_leave",
            from_date=add_months(nowdate(), -12),
            to_date=add_months(nowdate(), -1),
            carry_forward=0,
        )
        leave_allocation.submit()

        # Carry forwarded leaves scenario:
        # new_leaves = 0.58, carry_forwarded = 0.42
        leave_allocation_1 = create_leave_allocation(
            employee=self.employee.name,
            new_leaves_allocated=0.58,
            leave_type="_Test_CF_leave",
            carry_forward=1,
        )
        leave_allocation_1.submit()
        leave_allocation_1.reload()

        if leave_allocation.carry_forward:
            employee_doc = frappe.get_doc("Employee", leave_allocation.employee)
            leave_type = frappe.get_doc("Leave Type", leave_allocation.leave_type)

            carry_forward_limit = check_carry_forward_criteria(employee_doc, leave_type)
            if carry_forward_limit and not (leave_allocation.unused_leaves > carry_forward_limit):
                self.assertEqual(leave_allocation_1.unused_leaves, 0.42)
                self.assertEqual(leave_allocation_1.total_leaves_allocated, 1)

                if leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                        leave_allocation.unused_leaves = min(
                            leave_allocation.unused_leaves,
                            leave_type.maximum_carry_forwarded_leaves
                        )
                    else:
                        self.assertEqual(leave_allocation_1.unused_leaves, 0.42)
                        self.assertEqual(leave_allocation_1.total_leaves_allocated, 1)
                else:
                    self.assertEqual(leave_allocation_1.unused_leaves, 0.42)
                    self.assertEqual(leave_allocation_1.total_leaves_allocated, 1)





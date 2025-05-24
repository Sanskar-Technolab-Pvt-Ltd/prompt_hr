# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    """
    * Main execution function for the loan report
    * @param filters: Filter parameters for the report
    * @return: Tuple of (columns, data)
    """
    columns = get_columns()
    data = get_data(filters)
    # ! IMPORTANT: Ensure we only get submitted documents
    if filters is None:
        filters = {}
    filters["docstatus"] != 2
    return columns, data

def get_columns():
    """
    * Define the column structure for the loan report
    * @return: List of column definitions with labels, fieldnames, and types
    """
    return [
        {"label": "Loan Record", "fieldname": "name", "fieldtype": "Link", "options": "Loan", "width": 150},
        {"label": "Loan Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": "Guarantor", "fieldname": "guarantor", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Loan Type", "fieldname": "loan_type", "fieldtype": "Link", "options": "Loan Product", "width": 150},
        {"label": "Loan Amount", "fieldname": "loan_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Paid Amount", "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Remaining Amount", "fieldname": "remaining_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Paid Installment Count", "fieldname": "paid_count", "fieldtype": "Int", "width": 150},
        {"label": "Remaining Installment Count", "fieldname": "remaining_count", "fieldtype": "Int", "width": 180},
        {"label": "Loan Application", "fieldname": "loan_application", "fieldtype": "Link", "options": "Loan Application", "width": 150},
        {"label": "Repayment Start Date", "fieldname": "repayment_start_date", "fieldtype": "Date", "width": 140},
        {"label": "Repayment End Date", "fieldname": "repayment_end_date", "fieldtype": "Date", "width": 140}
    ]

def get_data(filters):
    """
    * Fetch and process loan data based on filters
    * @param filters: Dictionary containing filter criteria
    * @return: List of processed loan records
    """
    # TODO: Add proper error handling for database queries
    
    # ! CRITICAL: Initialize filters if None to prevent errors
    if filters is None:
        filters = {}
    
    # * Ensure we only get submitted documents (not draft or cancelled)
    filters["docstatus"] = 1
    
    # ? Fetch loan records with required fields
    loans = frappe.get_all("Loan", filters=filters, fields=[
        "name", "status", "applicant", "applicant_name", "company",
        "loan_amount", "total_amount_paid", "loan_product",
        "loan_application", "repayment_start_date", "custom_guarantor"])

    data = []
    
    for loan in loans:
        # * Initialize variables with default values
        repayment_end_date = None
        total_installments = 0
        paid_installments = 0
        
        try:
            # ? Get loan repayment schedule (only submitted documents)
            loan_repayment_schedule = frappe.get_all(
                "Loan Repayment Schedule", 
                filters={"loan": loan.name, "docstatus": 1}, 
                fields=["name"]
            )
            
            if loan_repayment_schedule:
                # * Get repayment schedules sorted by payment date (only submitted)
                repayment_schedules = frappe.get_all(
                    "Repayment Schedule", 
                    filters={
                        "parent": loan_repayment_schedule[0].name, 
                        "docstatus": 1
                    }, 
                    fields=["name", "payment_date"], 
                    order_by="payment_date"
                )
                
                # ! FIX: Check if repayment_schedules exists before using
                if repayment_schedules:
                    repayment_end_date = repayment_schedules[-1].payment_date
                    total_installments = len(repayment_schedules)
            
            # ? Get loan repayments (only submitted documents)
            loan_repayments = frappe.get_all(
                "Loan Repayment", 
                filters={
                    "against_loan": loan.name, 
                    "docstatus": 1,  # * Only submitted repayments
                    "loan_product": loan.loan_product
                }, 
                fields=["name"]
            )
            
            paid_installments = len(loan_repayments)
            
        except Exception as e:
            # ! ERROR: Log the error but continue processing
            frappe.log_error(f"Error processing loan {loan.name}: {str(e)}", "Loan Report Error")
            # * Set default values in case of error
            total_installments = 0
            paid_installments = 0
            repayment_end_date = None
        
        # * Calculate remaining installments
        remaining_installments = max(0, total_installments - paid_installments)
        
        # * Calculate remaining amount safely
        loan_amount = loan.loan_amount or 0
        paid_amount = loan.total_amount_paid or 0
        remaining_amount = max(0, loan_amount - paid_amount)
        
        # ? Append processed loan data
        data.append({
            "name": loan.name,
            "status": loan.status,
            "employee": loan.applicant,
            "employee_name": loan.applicant_name,
            "company": loan.company,
            "guarantor": loan.custom_guarantor,
            "loan_type": loan.loan_product,
            "loan_amount": loan_amount,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
            "paid_count": paid_installments,
            "remaining_count": remaining_installments,
            "loan_application": loan.loan_application,
            "repayment_start_date": loan.repayment_start_date,
            "repayment_end_date": repayment_end_date,
        })

    return data
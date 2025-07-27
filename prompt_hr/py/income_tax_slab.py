import frappe
from frappe import _

def validate(doc, method=None):
    #! CHECK IF ANOTHER DEFAULT REGIME EXISTS FOR THE SAME COMPANY
    existing_default = frappe.db.exists(
        "Income Tax Slab",
        {
            "company": doc.company,
            "custom_is_default_regime": 1,
            "disabled": 0,
            "docstatus": 1,
            "name": ["!=", doc.name],
        }
    )

    #? THROW ERROR IF DEFAULT REGIME ALREADY EXISTS
    if existing_default and doc.custom_is_default_regime:
        frappe.throw(_("Default regime is already set for the company: {0}").format(doc.company))

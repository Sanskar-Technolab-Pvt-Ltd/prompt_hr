import frappe

def before_save(doc, method):

    # ? POPULATE DECLARATIONS FROM TAX REGIME
    populate_tax_exemption_declarations(doc)

def on_submit(doc, method=None):
    """
    SHARE DOC WITH EMPLOYEE'S USER ID ON SUBMIT
    """
    if not doc.employee:
        return

    #! FETCH USER ID OF EMPLOYEE
    user_id = frappe.db.get_value("Employee", doc.employee, "user_id")
    if user_id:
        #! SHARE DOCUMENT WITH READ ONLY PERMISSION
        frappe.share.add(
            doctype=doc.doctype,
            name=doc.name,
            user=user_id,
            read=1,
        )

# ? FUNCTION TO POPULATE DECLARATIONS FROM TAX REGIME
def populate_tax_exemption_declarations(doc):
    if not doc.custom_tax_regime:
        frappe.throw("Tax Regime is mandatory")

    # ? FETCH ACTIVE SUB-CATEGORIES FOR THE SELECTED TAX REGIME
    sub_categories = frappe.get_all(
        "Employee Tax Exemption Sub Category",
        filters={"custom_tax_regime": doc.custom_tax_regime, "is_active": 1},
        fields=["name", "exemption_category","max_amount"]
    )

    # ? BUILD A SET OF EXISTING SUB-CATEGORY NAMES TO AVOID DUPLICATES
    existing_sub_cats = {d.exemption_sub_category for d in doc.declarations}

    # ? APPEND ONLY MISSING SUB-CATEGORIES TO THE DECLARATIONS TABLE
    for sub_category in sub_categories:
        if sub_category.name not in existing_sub_cats:
            doc.append("declarations", {
                "exemption_sub_category": sub_category.name,
                "exemption_category": sub_category.exemption_category,
                "amount": 0,
                "max_amount": sub_category.max_amount
            })

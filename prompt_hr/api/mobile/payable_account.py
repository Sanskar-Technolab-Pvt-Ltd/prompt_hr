import frappe

# ! prompt_hr.api.mobile.account.list
# ? GET PAYABLE ACCOUNT LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        
        # Parse inputs
        filters = frappe.parse_json(filters) if filters else []
        fields = frappe.parse_json(fields) if fields else ["*"]
        or_filters = frappe.parse_json(or_filters) if or_filters else []

        # Get default company from Global Defaults
        default_company = frappe.defaults.get_global_default("company")
        if not default_company:
            frappe.throw("No default company set in Global Defaults.")

        # Base filters
        base_filters = [
            ["report_type", "=", "Balance Sheet"],
            ["account_type", "=", "Payable"],
            ["company", "=", default_company],
            ["is_group", "=", 0]
        ]

        # Merge filters
        combined_filters = base_filters + filters

        # Fetch account list
        account_list = frappe.get_list(
            "Account",
            filters=combined_filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=int(limit_page_length),
            limit_start=int(limit_start),
        )

        # Count total
        total_names = frappe.get_list(
            "Account",
            filters=combined_filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)

    except Exception as e:
        frappe.log_error("Error While Getting Account List", str(e))
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Account List: {str(e)}",
            "data": None,
        }
    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Payable Account List Loaded Successfully!",
            "data": account_list,
            "count": total_count,
        }
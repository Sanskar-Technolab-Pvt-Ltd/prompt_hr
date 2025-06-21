import frappe

# ! prompt_hr.api.mobile.cost_center.list
# ? GET COST CENTER LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        # Parse input JSON values
        filters = frappe.parse_json(filters) if filters else []
        or_filters = frappe.parse_json(or_filters) if or_filters else []
        fields = frappe.parse_json(fields) if fields else ["*"]

        # Get default company
        default_company = frappe.defaults.get_global_default("company")
        if not default_company:
            frappe.throw("No default company found in Global Defaults.")

        # Base filters to match UI
        base_filters = [
            ["company", "=", default_company],
            ["disabled", "=", 0],  # Optional: Only active cost centers
        ]

        # Merge all filters
        combined_filters = base_filters + filters

        # Fetch data
        cost_centers = frappe.get_list(
            "Cost Center",
            filters=combined_filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=int(limit_page_length),
            limit_start=int(limit_start)
        )

        # Get total count
        total_names = frappe.get_all(
            "Cost Center",
            filters=combined_filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)

    except Exception as e:
        frappe.log_error("Error While Getting Cost Center List", str(e))
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Cost Center List: {str(e)}",
            "data": None,
        }
    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Cost Center List Loaded Successfully!",
            "data": cost_centers,
            "count": total_count
        }
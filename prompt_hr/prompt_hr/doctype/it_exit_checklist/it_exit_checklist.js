// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("IT Exit Checklist", {
    refresh(frm) {
        make_border_red_for_user_eligible_for_approval_process(frm)
        set_approval_status_and_status_readonly(frm)
    },
    after_save(frm) {
        make_border_red_for_user_eligible_for_approval_process(frm)
    },
});


// Shared function to determine eligibility  
async function checkUserEligibility(frm, rowDoc, tableName) {
    const user = frappe.session.user;
    const allowed_roles = [
        "S - HR Leave Approval",
        "S - HR leave Report",
        "S - HR L6",
        "S - HR L5",
        "S - HR L4",
        "S - HR L3",
        "S - HR L2",
        "S - HR L1",
        "S - HR Director (Global Admin)",
        "S - HR L2 Manager",
        "S - HR Supervisor (RM)",
        "System Manager"
    ];

    const user_roles = frappe.user_roles || [];
    let isReportingManager = false;

    // Check if user is reporting manager  
    if (frm.doc.reports_to) {
        try {
            const res = await frappe.db.get_value("Employee", frm.doc.reports_to, "user_id");
            isReportingManager = res?.message?.user_id === user;
        } catch (e) {
            console.warn("Error fetching reporting manager:", e);
        }
    }

    const hasApprovalRole = frappe.user.has_role(rowDoc?.role_allowed_to_modify_approval_status);
    const hasApprovalRoleStatus = frappe.user.has_role(rowDoc?.role_allowed_to_modify_status);
    const is_hr = user_roles.some(role => allowed_roles.includes(role));

    const hasRMApproval = rowDoc?.approval_status_to_be_filled_by_reporting_manager && isReportingManager;
    const hasRMStatus = rowDoc?.status_to_be_filled_by_reporting_manager && isReportingManager;

    const canModifyApproval =
        rowDoc?.user_allowed_to_modify_approval_status === user ||
        hasApprovalRole || is_hr || user === "Administrator" || hasRMApproval;

    const canModifyStatus =
        rowDoc?.user_allowed_to_modify_status === user ||
        hasApprovalRoleStatus || is_hr || user === "Administrator" || hasRMStatus;

    return { canModifyApproval, canModifyStatus };
}

async function make_border_red_for_user_eligible_for_approval_process(frm) {
    if (!frm) return;

    const tables = ["it", "engineering"];

    for (const tableName of tables) {
        const grid = frm.fields_dict?.[tableName]?.grid;
        if (!grid) continue;

        for (const row of grid.grid_rows || []) {
            const rowDoc = row?.doc;
            if (!rowDoc) continue;

            const $row = $(row.row);
            $row.css("border", "");

            const { canModifyApproval, canModifyStatus } = await checkUserEligibility(frm, rowDoc, tableName);

            // Handle status field placeholder  
            const $statusStatic = $row.find("div[data-fieldname='status'] .static-area");
            if (!rowDoc?.status && canModifyStatus) {
                $statusStatic.text("Please Fill Value")
                    .css({
                        color: "red",
                        "font-weight": "bold",
                        "font-style": "italic"
                    });
            } else {
                $statusStatic.text(rowDoc?.status || "")
                    .css({
                        color: "",
                        "font-weight": "",
                        "font-style": ""
                    });
            }

            // Handle approval_status field placeholder  
            const $approvalStatic = $row.find("div[data-fieldname='approval_status'] .static-area");
            if (rowDoc?.approval_status === "Pending" && canModifyApproval) {
                $approvalStatic.text("Action Required")
                    .css({
                        color: "red",
                        "font-weight": "bold",
                        "font-style": "italic"
                    });
            } else {
                $approvalStatic.text(rowDoc?.approval_status || "")
                    .css({
                        color: "",
                        "font-weight": "",
                        "font-style": ""
                    });
            }

            // Add red border for eligible rows  
            if (canModifyApproval && rowDoc?.approval_status !== "Approved") {
                $row.css("border", "2px solid red");
            }
        }
    }
}

async function set_approval_status_and_status_readonly(frm) {
    if (!frm) return;

    const tables = ["it", "engineering"];

    for (const tableName of tables) {
        const grid = frm.fields_dict?.[tableName]?.grid;
        if (!grid) continue;

        for (const row of grid.grid_rows || []) {
            const rowDoc = row?.doc;
            if (!rowDoc) continue;

            const { canModifyApproval, canModifyStatus } = await checkUserEligibility(frm, rowDoc, tableName);

            // Set readonly on docfield (affects form view)  
            row.docfields.forEach(df => {
                if (df.fieldname === 'approval_status') {
                    df.read_only = !canModifyApproval ? 1 : 0;
                }
                if (df.fieldname === 'status') {
                    df.read_only = !canModifyStatus ? 1 : 0;
                }
            });

            // Refresh grid form if open  
            if (row.grid_form) {
                row.grid_form.refresh();
            }

            // Handle collapsed row (grid view)  
            const $row = $(row.row);

            if (!canModifyApproval) {
                $row.find('[data-fieldname="approval_status"]').css({
                    "pointer-events": "none",
                    "opacity": 0.6,
                    "background-color": "#f9f9f9"
                });
            } else {
                $row.find('[data-fieldname="approval_status"]').css({
                    "pointer-events": "",
                    "opacity": 1,
                    "background-color": ""
                });
            }

            if (!canModifyStatus) {
                $row.find('[data-fieldname="status"]').css({
                    "pointer-events": "none",
                    "opacity": 0.6,
                    "background-color": "#f9f9f9"
                });
            } else {
                $row.find('[data-fieldname="status"]').css({
                    "pointer-events": "",
                    "opacity": 1,
                    "background-color": ""
                });
            }
        }
    }
}

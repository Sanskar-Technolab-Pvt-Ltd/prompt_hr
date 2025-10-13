// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("IT Exit Checklist", {
	refresh(frm) {
        make_border_red_for_user_eligible_for_approval_process(frm)
	},
    after_save(frm) {
        make_border_red_for_user_eligible_for_approval_process(frm)
    },
});

function make_border_red_for_user_eligible_for_approval_process(frm) {
    if (!frm) return;

    const tables = ["it", "engineering"];
    const exceptionMessages = [];
    const user = frappe.session.user;


    const highlightEligibleRows = (tableName) => {
        const grid = frm.fields_dict?.[tableName]?.grid;
        if (!grid) return;

        grid.grid_rows.forEach((row) => {
            const rowDoc = row?.doc;
            const $row = $(row.row);

            // ? Always reset border first
            $row.css("border", "");
            const hasApprovalRole = frappe.user.has_role(rowDoc?.role_allowed_to_modify_approval_status);
            // ? Check eligibility
            const canModify =
                rowDoc?.user_allowed_to_modify_approval_status === user || hasApprovalRole;

            if (canModify) {
                $row.css("border", "2px solid red");
                exceptionMessages.push(
                    `Row ${rowDoc?.idx}: Approval status change is allowed for this user in ${frappe.utils.to_title_case(tableName)} table.`
                );
            }
        });
    };

    // ? Loop through each table
    tables.forEach(highlightEligibleRows);

    const messageField = "approval_access_details";
    const wrapper = frm.fields_dict?.[messageField]?.$wrapper;
    if (!wrapper) return;

    // ? Remove any existing message block first
    wrapper.find(".approval-exception-message").remove();

    // ✅ Prepare message content
    let messageHTML;
    if (exceptionMessages.length > 0) {
        messageHTML = `
            <div class="approval-exception-message" style="
                padding: 14px; background: #fff5f5; border: 1px solid #ffa8a8;
                border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                font-size: 14px; color: #c92a2a; margin-top: 8px;">
                <h3 style="margin: 0 0 12px; font-size: 15px; color: #a61e4d;">
                    ⚠ Approval Exceptions
                </h3>
                <ul style="margin: 0; padding-left: 20px;">
                    ${exceptionMessages
                        .map((msg) => `<li>${frappe.utils.escape_html(msg)}</li>`)
                        .join("")}
                </ul>
            </div>
        `;
    } else {
        messageHTML = `
            <div class="approval-exception-message" style="
                padding: 14px; background: #fff5f5; border: 1px solid #ffa8a8;
                border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                font-size: 14px; color: #c92a2a; margin-top: 8px;">
                <b>You are not allowed for the approval process.</b>
            </div>
        `;
    }

    // ? Append final message
    wrapper.append(messageHTML);
}

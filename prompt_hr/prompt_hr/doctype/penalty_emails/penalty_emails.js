// Copyright (c) 2025, Jignasha Chavda and contributors
// For license information, please see license.txt

frappe.ui.form.on("Penalty Emails", {
    refresh: function (frm) {
        // Add a button to the form
        frm.add_custom_button(__('Send Emails'), function () {
            frappe.call({
                method: "prompt_hr.prompt_hr.doctype.penalty_emails.penalty_emails.send_penalty_emails",
                args: {
                    docname: frm.doc.name
                },
                callback: function (r) {
                    if (!r.exc) {
                        frappe.msgprint(__('Emails sent successfully'));
                        frm.reload_doc();
                    }
                },
            });
        });

        // Add button to view email details in dialog
        view_email_details(frm);
    },
});

function view_email_details(frm) {
    frm.add_custom_button("Extract Penalty Info from Emails", () => {
        let extracted_data = [];
        (frm.doc.email_details || []).forEach((row, idx) => {
            if (!row.data) return;
            let parsed = {};
            try {
                parsed = JSON.parse(row.data);
            } catch (e) {
                console.error("Invalid JSON in row.data:", e);
                return;
            }
            let employeeID = parsed.employee || "";
            let employeeName = parsed.employee_name || "";
            let emailType = parsed.email_type || "";
            let attendanceDate = parsed.attendance_date || "";

            let penalties = [];
            if (parsed.penalties && typeof parsed.penalties === "object") {
                Object.keys(parsed.penalties).forEach((pType) => {
                    let p = parsed.penalties[pType];
                    penalties.push({
                        penalty_type: pType,
                        scheduled_date: p.penalty_date || "",
                        attendance_ref: p.attendance || "",
                    });
                });
            }

            // Determine if this row is already sent - you can set this flag based on your actual data
            // For demo assume if row.selected exists in doc or if you keep a sent flag in penalty data, adjust accordingly
            // Here we check if row has 'sent' property (true/false)
            let already_sent = row.sent ? true : false;

            extracted_data.push({
                row_name: row.name, // unique child table docname
                employeeID,
                employeeName,
                emailType,
                attendanceDate,
                penalties,
                emailIndex: idx + 1,
                selected: already_sent, // mark selected if sent
                already_sent: already_sent,
            });
        });

        // Summary metrics
        const totalEmails = extracted_data.length;
        const totalPenalties = extracted_data.reduce(
            (t, emp) => t + emp.penalties.length,
            0
        );
        const affectedEmployees = extracted_data.filter(
            (emp) => emp.penalties.length > 0
        ).length;

        // Build HTML with enhanced modern UI
        let htmlContent = `
    <div style="max-height: 650px; overflow-y: auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;">
    <style>
      @keyframes slideIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      
      @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
      }

      @keyframes shimmer {
        0% { background-position: -200px 0; }
        100% { background-position: calc(200px + 100%) 0; }
      }

      .penalty-container { 
        margin-bottom: 20px; 
        border: 1px solid #e2e8f0; 
        border-radius: 16px; 
        overflow: hidden; 
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        animation: slideIn 0.5s ease-out forwards;
        position: relative;
      }
      
      .penalty-container:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        border-color: #4f46e5;
      }

      .penalty-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #4f46e5, #7c3aed, #ec4899);
        opacity: 0;
        transition: opacity 0.3s ease;
      }

      .penalty-container:hover::before {
        opacity: 1;
      }

      .employee-header { 
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-bottom: 1px solid #e2e8f0; 
        padding: 16px 20px; 
        display: flex; 
        align-items: center; 
        gap: 16px;
        position: relative;
        overflow: hidden;
      }

      .employee-header::after {
        content: '';
        position: absolute;
        top: 0;
        left: -200px;
        width: 200px;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        animation: shimmer 2s infinite;
      }

      .employee-avatar { 
        width: 48px; 
        height: 48px; 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        color: #fff; 
        font-weight: 700; 
        font-size: 16px;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease;
      }

      .employee-avatar:hover {
        transform: rotate(5deg) scale(1.1);
      }

      .employee-info { 
        flex-grow: 1; 
        z-index: 1;
      }

      .employee-name { 
        font-size: 18px; 
        font-weight: 700; 
        color: #1e293b;
        margin-bottom: 4px;
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .employee-meta { 
        font-size: 13px; 
        color: #64748b; 
        display: flex; 
        align-items: center; 
        gap: 12px;
        margin-bottom: 2px;
      }

      .penalty-table { 
        width: 100%; 
        border-collapse: collapse; 
        margin-top: 0;
        background: #ffffff;
      }

      .penalty-table th { 
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
        border: 1px solid #e2e8f0; 
        padding: 12px 16px; 
        font-size: 13px;
        font-weight: 600;
        color: #374151;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      .penalty-table td { 
        border: 1px solid #e2e8f0; 
        padding: 12px 16px; 
        font-size: 13px;
        transition: background-color 0.2s ease;
      }

      .penalty-table tr:hover td {
        background-color: #f8fafc;
      }

      .status-badge { 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-size: 11px; 
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }

      .status-badge::before {
        content: '';
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
      }

      .status-valid { 
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #065f46;
        border: 1px solid #10b981;
      }

      .status-valid::before {
        background: #10b981;
      }

      .status-invalid { 
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #991b1b;
        border: 1px solid #ef4444;
      }

      .status-invalid::before {
        background: #ef4444;
      }

      .status-missing { 
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        border: 1px solid #f59e0b;
      }

      .status-missing::before {
        background: #f59e0b;
      }

      .status-already-sent { 
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af; 
        font-weight: 700; 
        border: 1px solid #3b82f6;
        animation: pulse 2s infinite;
      }

      .status-already-sent::before {
        background: #3b82f6;
      }

      .no-penalties { 
        text-align: center; 
        color: #64748b; 
        font-style: italic; 
        padding: 32px; 
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px; 
        border: 2px dashed #cbd5e1; 
        margin: 16px;
        position: relative;
        overflow: hidden;
      }

      .no-penalties::before {
        content: '✨';
        font-size: 24px;
        display: block;
        margin-bottom: 8px;
      }

      .checkbox-cell { 
        text-align: center; 
      }

      .select-record-checkbox { 
        margin-right: 16px; 
        cursor: pointer;
        width: 18px;
        height: 18px;
        accent-color: #4f46e5;
        transition: transform 0.2s ease;
      }

      .select-record-checkbox:hover {
        transform: scale(1.2);
      }

      .select-record-checkbox[disabled] { 
        cursor: not-allowed;
        opacity: 0.5;
      }

      .attendance-link { 
        color: #3b82f6; 
        text-decoration: none;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 6px;
        transition: all 0.2s ease;
      }

      .attendance-link:hover {
        background: #dbeafe;
        transform: translateX(2px);
        text-decoration: underline;
      }

      .select-buttons {
        position: sticky;
        top: 0;
        z-index: 10;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        margin-bottom: 16px;
        display: flex;
        gap: 12px;
        padding: 16px 0;
        border-bottom: 1px solid #e2e8f0;
        border-radius: 12px 12px 0 0;
        backdrop-filter: blur(10px);
      }

      .select-buttons button {
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        cursor: pointer;
        position: relative;
        overflow: hidden;
      }

      .select-buttons button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        transition: left 0.5s;
      }

      .select-buttons button:hover::before {
        left: 100%;
      }

      .btn-primary-dialog {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
      }

      .btn-primary-dialog:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4);
      }

      .btn-secondary-dialog {
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
        color: white !important;
        box-shadow: 0 4px 15px rgba(107, 114, 128, 0.3);
      }

      .btn-secondary-dialog:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(107, 114, 128, 0.4);
      }

      .summary-card {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(79, 70, 229, 0.3);
        position: relative;
        overflow: hidden;
      }

      .summary-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: shimmer 3s infinite;
      }

      .summary-card h3 {
        margin: 0 0 12px 0;
        font-size: 20px;
        font-weight: 700;
      }

      .summary-card p {
        margin: 0;
        opacity: 0.9;
        font-size: 14px;
      }

      .summary-stats {
        display: flex;
        gap: 24px;
        margin-top: 16px;
      }

      .stat-item {
        text-align: center;
      }

      .stat-number {
        font-size: 24px;
        font-weight: 700;
        display: block;
      }

      .stat-label {
        font-size: 12px;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      .empty-state {
        text-align: center;
        padding: 60px 40px;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 20px;
        border: 2px dashed #cbd5e1;
      }

      .empty-state-icon {
        font-size: 48px;
        margin-bottom: 16px;
        display: block;
      }

      .empty-state-title {
        font-size: 20px;
        font-weight: 600;
        color: #374151;
        margin-bottom: 8px;
      }

      .empty-state-description {
        color: #6b7280;
        font-size: 14px;
      }
    </style>

    <div class="select-buttons">
      <button type="button" class="btn btn-sm btn-primary btn-primary-dialog" id="select-all-btn">
        <i class="fa fa-check-square" style="margin-right: 6px;"></i>Select All
      </button>
      <button type="button" class="btn btn-sm btn-secondary btn-secondary-dialog" id="unselect-all-btn">
        <i class="fa fa-square-o" style="margin-right: 6px;"></i>Unselect All
      </button>
    </div>
    `;

        if (totalEmails === 0) {
            htmlContent += `
      <div class="empty-state">
        <span class="empty-state-icon">📭</span>
        <div class="empty-state-title">No Emails Found</div>
        <div class="empty-state-description">There are no penalty emails to display at this time.</div>
      </div>`;
        } else {
            htmlContent += `
      <div class="summary-card">
        <h3 style="color:white !important;">📊 Penalty Information Summary</h3>
        <p>Comprehensive overview of penalty data extracted from email communications</p>
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-number">${totalEmails}</span>
            <span class="stat-label">Total Emails</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">${totalPenalties}</span>
            <span class="stat-label">Penalties Found</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">${affectedEmployees}</span>
            <span class="stat-label">Affected Employees</span>
          </div>
        </div>
      </div>
      `;

            extracted_data.forEach((data, dIdx) => {
                const initials = data.employeeName
                    ? data.employeeName
                        .split(" ")
                        .map((n) => n[0])
                        .join("")
                        .toUpperCase()
                        .slice(0, 2)
                    : data.emailIndex.toString();

                htmlContent += `
        <div class="penalty-container" data-email-idx="${dIdx}" style="animation-delay: ${dIdx * 0.1}s">
          <div class="employee-header">
            <input type="checkbox" class="select-record-checkbox" data-row-name="${data.row_name}" 
              ${data.selected ? "checked" : ""} ${data.already_sent ? "disabled" : ""} title="Select this record">
            <div class="employee-avatar">${initials}</div>
            <div class="employee-info">
              <div class="employee-name">${data.employeeName || "Unknown Employee"}</div>
              <div class="employee-meta">
                <span>🆔 ${data.employeeID || "N/A"}</span>
                <span>📧 ${data.emailType}</span>
              </div>
              <div class="employee-meta">
                <span>📅 Penalty recorded for attendance on ${frappe.datetime.str_to_user(data.attendanceDate)}</span>
                ${data.already_sent ? `<span class="status-badge status-already-sent">Already Sent</span>` : ""}
              </div>
            </div>
          </div>
        `;

                if (data.penalties.length > 0) {
                    htmlContent += `
          <table class="penalty-table">
            <thead>
              <tr>
                <th>🚫 Penalty Type</th>
                <th>📅 Scheduled Date</th>
                <th>📋 Attendance Ref</th>
                <th>🔍 Status</th>
              </tr>
            </thead>
            <tbody>
          `;

                    data.penalties.forEach((p) => {
                        let statusClass = "status-valid";
                        let statusText = "Valid";

                        if (!p.scheduled_date) {
                            statusText = "Valid";
                        } else if (
                            !/^\d{4}-\d{2}-\d{2}$|^\d{1,2}[-\/]\d{1,2}[-\/]\d{4}$/.test(p.scheduled_date)
                        ) {
                            statusClass = "status-invalid";
                            statusText = "Invalid Format";
                        }

                        let attendanceLinkHtml = p.attendance_ref
                            ? `<a href="/app/attendance/${p.attendance_ref}" class="attendance-link" target="_blank">${p.attendance_ref}</a>`
                            : "<span style='color: #9ca3af;'>Not Available</span>";

                        htmlContent += `
              <tr>
                <td><strong>${p.penalty_type}</strong></td>
                <td>${p.scheduled_date ? frappe.datetime.str_to_user(p.scheduled_date) : "<em>Applied</em>"}</td>
                <td>${attendanceLinkHtml}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
              </tr>
            `;
                    });

                    htmlContent += `</tbody></table>`;
                } else {
                    htmlContent += `<div class="no-penalties">No penalties found for this employee</div>`;
                }

                htmlContent += `</div>`; // penalty container end
            });
        }

        htmlContent += `</div>`;

        const dialog = new frappe.ui.Dialog({
            title: "🎯 Penalty Information Extraction Results",
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "penalty_results",
                    options: htmlContent,
                },
            ],
            size: "extra-large",
            primary_action_label: "📧 Send Selected Emails",
            primary_action() {
                // Collect selected row names that are not already sent
                let selectedRowNames = [];
                dialog.fields_dict.penalty_results.$wrapper
                    .find(".select-record-checkbox:checked")
                    .each((_, checkbox) => {
                        let $checkbox = $(checkbox);
                        if (!$checkbox.is(":disabled")) {
                            let rowName = $checkbox.attr("data-row-name");
                            if (rowName) {
                                selectedRowNames.push(rowName);
                            }
                        }
                    });

                if (selectedRowNames.length === 0) {
                    frappe.show_alert({
                        message: "Please select at least one record to send mail",
                        indicator: "orange",
                    });
                    return;
                }

                frappe.call({
                    method: "prompt_hr.prompt_hr.doctype.penalty_emails.penalty_emails.send_penalty_emails",
                    args: {
                        docname: frm.doc.name,
                        selected_row_names: selectedRowNames,
                    },
                    freeze: true,
                    freeze_message: "📨 Sending selected penalty emails...",
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.msgprint({
                                title: "Success",
                                message: `Successfully sent emails for ${selectedRowNames.length} selected record(s).`,
                                indicator: "green"
                            });
                            frm.reload_doc();
                            dialog.hide();
                        }
                    },
                    error: function (err) {
                        frappe.msgprint({
                            title: "Error",
                            message: "Error sending emails: " + err.message,
                            indicator: "red"
                        });
                    },
                });
            },
            secondary_action_label: "Close",
            secondary_action() {
                dialog.hide();
            },
        });

        dialog.show();

        // Select all clicked: only select checkboxes not disabled (not already sent)
        dialog.fields_dict.penalty_results.$wrapper.on("click", "#select-all-btn", () => {
            dialog.fields_dict.penalty_results.$wrapper
                .find(".select-record-checkbox:not(:disabled)")
                .prop("checked", true);
        });

        // Unselect all clicked: uncheck all checkboxes even disabled ones
        dialog.fields_dict.penalty_results.$wrapper.on("click", "#unselect-all-btn", () => {
            dialog.fields_dict.penalty_results.$wrapper
                .find(".select-record-checkbox:not(:disabled)")
                .prop("checked", false);
        });
    });
}

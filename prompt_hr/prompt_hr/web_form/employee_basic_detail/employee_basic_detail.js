frappe.ready(function () {
    // INJECT ENHANCED STYLES
    const styles = `
        <style>
            :root {
                --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                --card-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                --card-shadow-hover: 0 15px 40px rgba(0, 0, 0, 0.15);
                --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                --border-radius: 16px;
                --spacing-unit: 1rem;
            }
            .indicator-pill.orange {
                display: none !important;
            }

            .employee-details-container {
                animation: fadeInUp 0.6s ease-out;
                margin-top: 2rem;
            }

            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            .employee-details-container .card {
                border: none;
                border-radius: var(--border-radius);
                box-shadow: var(--card-shadow);
                transition: var(--transition-smooth);
                overflow: hidden;
                margin-bottom: 1.5rem;
                animation: slideIn 0.5s ease-out;
                animation-fill-mode: both;
            }

            .employee-details-container .card:hover {
                box-shadow: var(--card-shadow-hover);
                transform: translateY(-5px);
            }

            .employee-details-container .card:nth-child(1) { animation-delay: 0.1s; }
            .employee-details-container .card:nth-child(2) { animation-delay: 0.2s; }
            .employee-details-container .card:nth-child(3) { animation-delay: 0.3s; }
            .employee-details-container .card:nth-child(4) { animation-delay: 0.4s; }

            .employee-details-container .card-header {
                background: var(--primary-gradient);
                color: white;
                padding: 1.25rem 1.5rem;
                border-bottom: none;
                position: relative;
                overflow: hidden;
            }

            .employee-details-container .card-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
                pointer-events: none;
            }

            .employee-details-container .card-header h5,
            .employee-details-container .card-header h6 {
                margin: 0;
                font-weight: 600;
                letter-spacing: 0.5px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.1);
                position: relative;
                z-index: 1;
            }

            .employee-details-container .card-header.bg-secondary {
                background: var(--secondary-gradient);
            }

            .employee-details-container .table {
                margin-bottom: 0;
            }

            .employee-details-container .table th {
                background: linear-gradient(to right, #f8f9fa 0%, #e9ecef 100%);
                font-weight: 600;
                color: #495057;
                padding: 1rem 1.25rem;
                border-bottom: 2px solid #dee2e6;
                text-transform: uppercase;
                font-size: 0.75rem;
                letter-spacing: 0.5px;
                white-space: nowrap;
            }

            .employee-details-container .table td {
                padding: 1rem 1.25rem;
                vertical-align: middle;
                color: #212529;
                border-color: #e9ecef;
                transition: var(--transition-smooth);
            }

            .employee-details-container .table-hover tbody tr:hover {
                background: linear-gradient(to right, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
                transform: scale(1.01);
            }

            .employee-details-container .table-striped tbody tr:nth-of-type(odd) {
                background-color: rgba(0, 0, 0, 0.02);
            }

            .employee-details-container .card-body {
                padding: 0;
                background: white;
            }

            .employee-details-container .card-body[style*="overflow-y"] {
                scrollbar-width: thin;
                scrollbar-color: #667eea #f1f3f4;
            }

            .employee-details-container .card-body[style*="overflow-y"]::-webkit-scrollbar {
                width: 8px;
            }

            .employee-details-container .card-body[style*="overflow-y"]::-webkit-scrollbar-track {
                background: #f1f3f4;
                border-radius: 10px;
            }

            .employee-details-container .card-body[style*="overflow-y"]::-webkit-scrollbar-thumb {
                background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px;
            }

            .employee-details-container .card-body[style*="overflow-y"]::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(180deg, #764ba2 0%, #667eea 100%);
            }

            .employee-details-container .badge {
                padding: 0.4rem 0.8rem;
                border-radius: 8px;
                font-weight: 500;
                font-size: 0.75rem;
            }

            .employee-details-container .table thead th {
                position: sticky;
                top: 0;
                z-index: 10;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }

            /* Empty state styling */
            .employee-details-container .empty-state {
                text-align: center;
                padding: 3rem 2rem;
                color: #6c757d;
            }

            .employee-details-container .empty-state svg {
                width: 80px;
                height: 80px;
                margin-bottom: 1rem;
                opacity: 0.5;
            }

            /* Loading animation */
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            .loading-skeleton {
                animation: pulse 1.5s ease-in-out infinite;
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: shimmer 1.5s infinite;
                border-radius: 8px;
                height: 20px;
                margin: 0.5rem 0;
            }

            @keyframes shimmer {
                0% { background-position: -200% 0; }
                100% { background-position: 200% 0; }
            }

            /* Responsive design */
            @media (max-width: 768px) {
                .employee-details-container .card-header {
                    padding: 1rem;
                }

                .employee-details-container .table th,
                .employee-details-container .table td {
                    padding: 0.75rem;
                    font-size: 0.875rem;
                }

                .employee-details-container .card {
                    border-radius: 12px;
                }

                .employee-details-container {
                    margin-top: 1rem;
                }
            }

            @media (max-width: 576px) {
                .employee-details-container .table {
                    font-size: 0.8rem;
                }

                .employee-details-container .table th,
                .employee-details-container .table td {
                    padding: 0.5rem;
                }

                .employee-details-container .card-header h5,
                .employee-details-container .card-header h6 {
                    font-size: 1rem;
                }
            }

            /* Accessibility improvements */
            .employee-details-container .table th,
            .employee-details-container .table td {
                outline: none;
            }

            .employee-details-container .table tbody tr:focus-within {
                outline: 2px solid #667eea;
                outline-offset: -2px;
            }

            /* Print styles */
            @media print {
                .employee-details-container .card {
                    box-shadow: none;
                    border: 1px solid #dee2e6;
                    break-inside: avoid;
                }

                .employee-details-container .card-header {
                    background: #667eea !important;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }
            }
        </style>
    `;

    // Inject styles into document
    $('head').append(styles);

    // HIDE DEFAULT BUTTONS
    $(".web-form-actions").hide();

    // SELECT ALL AUTOCOMPLETE INPUTS
    let autocompleteFields = document.querySelectorAll('input[data-fieldname="employee"]');

    autocompleteFields.forEach(field => {
        field.addEventListener('input', function(e) {
            let value = e.target.value;
            let fieldname = "employee"
            // GET THE FRAPPE FIELD CONTROL
            let control = frappe.web_form?.fields_dict[fieldname];
            if (control) {
                // CALL YOUR FUNCTION
                frappe.call({
                    method: "prompt_hr.prompt_hr.web_form.employee_basic_detail.employee_basic_detail.make_autocomplete_options_for_employee",
                    args: {
                        fieldname: fieldname,
                        searchtxt: value
                    },
                    callback: function(r) {
                        if (!r.exc && r.message) {
                            // UPDATE CONTROL OPTIONS
                            if (control.set_data) {  
                                // FOR AUTOCOMPLETE CONTROLS  
                                control.set_data(r.message);  
                            } else if (control.awesomplete) {  
                                // FOR LINK CONTROLS OR DIRECT AWESOMPLETE ACCESS  
                                control.awesomplete.list = r.message;  
                            }  
                        }
                    }
                });
            }
        });
    });

    // LISTEN FOR CHANGE ON EMPLOYEE FIELD
    $(document).on("change", '[data-fieldname="employee"]', function () {
        let employee = $(this).val();
        if (employee) {
            frappe.call({
                method: "prompt_hr.prompt_hr.web_form.employee_basic_detail.employee_basic_detail.get_basic_fields_data",
                args: { employee: employee },
                callback: function (r) {
                    if (r.message) {
                        let details = r.message;

                        // Find the web-form-body container where you want to add the dynamic fields
                        let parentContainer = document.querySelector(".web-form-body") || document.getElementById("web-form-body");

                        if (!parentContainer) {
                            console.error("web-form-body container not found in DOM");
                            return;
                        }

                        // Check if container already exists to avoid duplicates
                        let container = document.getElementById("employee-details-container");
                        if (!container) {
                            container = document.createElement("div");
                            container.id = "employee-details-container";
                            container.classList.add("employee-details-container");
                            parentContainer.appendChild(container);
                        }

                        container.innerHTML = '';
                        // Check if there's any data to display
                        const hasBasicData = details.basic_data && Object.keys(details.basic_data).length > 0;
                        const hasTableData = details.table_datas && Object.keys(details.table_datas).length > 0;

                        // If no data at all, show message
                        if (!hasBasicData && !hasTableData) {
                            container.innerHTML = `
                                <div class="card shadow-sm">
                                    <div class="card-body text-center py-5">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: #adb5bd; margin-bottom: 1rem;">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                            <polyline points="14 2 14 8 20 8"></polyline>
                                            <line x1="12" y1="18" x2="12" y2="12"></line>
                                            <line x1="9" y1="15" x2="15" y2="15"></line>
                                        </svg>
                                        <h5 style="color: #6c757d; font-weight: 600; margin-bottom: 0.5rem;">No Employee Details View is Allowed</h5>
                                        <p style="color: #adb5bd; margin: 0;">There are no configured fields to display for this employee.</p>
                                    </div>
                                </div>
                            `;
                            return;
                        }
                        // Render basic data fields
                        // Now backend sends: { fieldname: [value, label], ... }
                        if (details.basic_data && Object.keys(details.basic_data).length > 0) {
                            const basicData = details.basic_data;
                            let basicHtml = `
                                <div class="card shadow-sm">
                                    <div class="card-header">
                                        <h5 class="mb-0">📋 Basic Details</h5>
                                    </div>
                                    <div class="card-body p-0">
                                        <table class="table table-sm table-hover table-bordered mb-0">
                                            <tbody>
                            `;
                            
                            for (const fieldname in basicData) {
                                if (basicData.hasOwnProperty(fieldname)) {
                                    // basicData[fieldname] is an array: [value, label]
                                    const value = basicData[fieldname][0];
                                    const label = basicData[fieldname][1] || fieldname;
                                    
                                    basicHtml += `
                                        <tr>
                                            <th class="bg-light text-nowrap">${label}</th>
                                            <td style="border: 1px solid #dee2e6;">${value || '<span style="color: #adb5bd;">—</span>'}</td>
                                        </tr>
                                    `;
                                }
                            }
                            basicHtml += `
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            `;
                            container.insertAdjacentHTML('beforeend', basicHtml);
                        }

                        // Render table data if any
                        // Now backend sends: { tablefield: [table_label, { fieldname: [value, label], ... }], ... }
                        if (details.table_datas && Object.keys(details.table_datas).length > 0) {
                            for (const tableFieldname in details.table_datas) {
                                if (details.table_datas.hasOwnProperty(tableFieldname)) {
                                    const tableInfo = details.table_datas[tableFieldname];
                                    
                                    // tableInfo is an array: [table_label, row_with_label]
                                    const tableLabel = tableInfo[0] || tableFieldname;
                                    const rowWithLabel = tableInfo[1];
                                    
                                    if (rowWithLabel && Object.keys(rowWithLabel).length > 0) {
                                        let tableHtml = `
                                            <div class="card shadow-sm">
                                                <div class="card-header bg-secondary">
                                                    <h6 class="mb-0">📊 ${tableLabel}</h6>
                                                </div>
                                                <div class="card-body p-0" style="max-height: 300px; overflow-y: auto;">
                                                    <table class="table table-bordered table-striped table-sm mb-0">
                                                        <thead class="table-light">
                                                            <tr>
                                        `;

                                        // Extract headers (labels) from the first row
                                        const fieldnames = Object.keys(rowWithLabel);
                                        fieldnames.forEach(fieldname => {
                                            // rowWithLabel[fieldname] is [value, label]
                                            const label = rowWithLabel[fieldname][1] || fieldname;
                                            tableHtml += `<th class="text-nowrap">${label}</th>`;
                                        });
                                        
                                        tableHtml += '</tr></thead><tbody>';

                                        // Generate table row with values
                                        tableHtml += '<tr>';
                                        fieldnames.forEach(fieldname => {
                                            const value = rowWithLabel[fieldname][0];
                                            tableHtml += `<td>${value || '<span style="color: #adb5bd;">—</span>'}</td>`;
                                        });
                                        tableHtml += '</tr>';
                                        
                                        tableHtml += `
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        `;

                                        // Append to container
                                        container.insertAdjacentHTML('beforeend', tableHtml);
                                    }
                                }
                            }
                        }
                    }
                }
            });
        }
    });
});

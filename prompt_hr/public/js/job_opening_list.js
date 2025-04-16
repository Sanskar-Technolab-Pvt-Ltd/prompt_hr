frappe.listview_settings['Job Opening'] = {
    onload: function (listview) {
        listview.page.add_inner_button(__('Add to Interview Availability'), () => {
            const selected_jobs = listview.get_checked_items();

            if (!selected_jobs.length) {
                frappe.msgprint(__('Please select at least one Job Opening.'));
                return;
            }

            const dialog = new frappe.ui.Dialog({
                title: 'Select Employees for Interview Availability',
                fields: [
                    {
                        label: 'Employees',
                        fieldname: 'employees',
                        fieldtype: 'Link',
                        options: 'Employee',
                        get_query: function () {
                            return {
                                filters: {
                                    status: 'Active'
                                }
                            };
                        }
                    },
                    {
                        fieldtype: 'HTML',
                        fieldname: 'selected_employees_html',
                        label: 'Selected Employees',
                        options: '<div id="selected_employees_container"></div>'
                    },
                    {
                        fieldtype: 'Button',
                        fieldname: 'add_employee',
                        label: 'Add Employee'
                    },
                    {
                        fieldtype: 'Small Text',
                        fieldname: 'employee_list',
                        label: 'Employee List',
                        hidden: 1
                    }
                ],
                primary_action_label: 'Submit',
                primary_action(values) {
                    const job_opening_ids = selected_jobs.map(row => row.name);
                    const selected_employees_list = values.employee_list ? JSON.parse(values.employee_list) : [];

                    if (!selected_employees_list.length) {
                        frappe.msgprint(__('Please select at least one Employee.'));
                        return;
                    }

                    frappe.call({
                        method: 'prompt_hr.py.job_opening.add_to_interview_availability',
                        args: {
                            job_openings: JSON.stringify(job_opening_ids),
                            employees: JSON.stringify(selected_employees_list)
                        },
                        callback: (r) => {
                            if (!r.exc) {
                                frappe.msgprint(__('Interview Availability updated and shared successfully.'));
                                dialog.hide();
                                listview.refresh();
                            }
                        }
                    });
                }
            });

            const selected_employees = [];
            dialog.fields_dict.employee_list.set_value(JSON.stringify(selected_employees));

            dialog.fields_dict.add_employee.wrapper.onclick = function () {
                const employee = dialog.get_value('employees');
                if (!employee) {
                    frappe.msgprint(__('Please select an Employee first.'));
                    return;
                }

                if (selected_employees.includes(employee)) {
                    frappe.msgprint(__('Employee already added.'));
                    return;
                }

                frappe.db.get_value('Employee', employee, 'employee_name', (r) => {
                    if (r && r.employee_name) {
                        selected_employees.push(employee);
                        dialog.fields_dict.employee_list.set_value(JSON.stringify(selected_employees));
                        updateSelectedEmployeesDisplay();
                        dialog.fields_dict.employees.set_value('');
                    }
                });
            };

            function updateSelectedEmployeesDisplay() {
                const container = $('#selected_employees_container');
                container.empty();

                if (selected_employees.length > 0) {
                    const table = $('<table class="table table-bordered table-hover table-sm"><thead><tr><th>Employee ID</th><th>Employee Name</th><th>Action</th></tr></thead><tbody></tbody></table>');
                    const tbody = table.find('tbody');

                    selected_employees.forEach((emp, index) => {
                        frappe.db.get_value('Employee', emp, 'employee_name', (r) => {
                            if (r && r.employee_name) {
                                const row = $(`<tr>
                                    <td>${emp}</td>
                                    <td>${r.employee_name}</td>
                                    <td><button class="btn btn-xs btn-danger remove-employee" data-index="${index}">Remove</button></td>
                                </tr>`);
                                tbody.append(row);

                                row.find('.remove-employee').click(function () {
                                    const idx = $(this).data('index');
                                    selected_employees.splice(idx, 1);
                                    dialog.fields_dict.employee_list.set_value(JSON.stringify(selected_employees));
                                    updateSelectedEmployeesDisplay();
                                });
                            }
                        });
                    });

                    container.append(table);
                } else {
                    container.append('<div class="text-muted">No employees selected</div>');
                }
            }

            updateSelectedEmployeesDisplay();

            $(dialog.fields_dict.employees.input).on('awesomplete-open', function () {
                setTimeout(() => {
                    const items = dialog.fields_dict.employees.awesomplete.ul.children;
                    for (let i = 0; i < items.length; i++) {
                        const item_value = items[i].dataset.value;
                        if (selected_employees.includes(item_value)) {
                            items[i].style.display = 'none';
                        }
                    }
                }, 100);
            });

            dialog.show();
        });
    }
};

frappe.ui.form.on('Attendance', {
    refresh(frm) {
        if (frm.doc.employee && frm.doc.attendance_date) {

            // * ATTENDANCE REGULARIZATION FLOW

            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Attendance Regularization',
                    filters: {
                        attendance: frm.doc.name
                    },
                    fieldname: 'name'
                },
                callback(r) {
                    // if (!r.message.name) {
                    frm.add_custom_button('Regularize Attendance', () => {
                            
                        if (!r.message.name) {
                            frappe.call({
                                method: "prompt_hr.py.attendance.validate_for_regularization",
                                args: {
                                    attendance_id: frm.doc.name,
                                    attendance_date: frm.doc.attendance_date,
                                    employee_id: frm.doc.employee
                                },
                                callback: function (res) {
                                    
                                    if (!res.message.error && res.message.is_allowed) {
                                        console.log("Is Allowed")
                                        show_checkin_dialog(frm);                                
                                    } else if(res.message.error) {
                                        frappe.throw(res.message.message)
                                    }
                                }
                            })
                        } else {
                            frappe.throw(`Regularization already created: <a href="/app/attendance-regularization/${r.message.name}">${r.message.name}</a>`);
                            
                            }
                        });
                    // } else {
                        // console.log("record found")
                    // }
                }
            });
        }
    }
});

function show_checkin_dialog(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee Checkin',
            filters: {
                employee: frm.doc.employee,
                time: ['between', [
                    `${frm.doc.attendance_date} 00:00:00`,
                    `${frm.doc.attendance_date} 23:59:59`
                ]]
            },
            fields: ['name', 'time', 'log_type'],
            order_by: 'time asc'
        },
        callback(r) {
            const checkins = r.message;
            // if (!checkins.length) {
            //     frappe.msgprint('No check-ins found for this date.');
            //     return;
            // }

            //* Setting in_time or out_time based on log_type
            const table_data = [];
            let last_in = null

            for (let i = 0; i < checkins.length; i++) {
                const current = checkins[i];
                if (current.log_type === 'IN') {
                    if (last_in && !last_in.out_time)
                    {
                        table_data.push(last_in)
                        last_in = null
                    }
                    last_in = {
                        in_time: frappe.datetime.str_to_obj(current.time).toTimeString().split(' ')[0],
                        // in_time: current.time,
                        out_time: '',
                        employee_checkin : current.name
                    }
                } else if (current.log_type === "OUT") {
                    if (last_in) {
                        last_in.out_time = frappe.datetime.str_to_obj(current.time).toTimeString().split(' ')[0]
                        table_data.push(last_in)
                        
                        last_in = null
                    } else {
                        table_data.push({
                            in_time: '',
                            out_time: frappe.datetime.str_to_obj(current.time).toTimeString().split(' ')[0],
                            employee_checkin: current.name
                        })
                        
                    }
                }
            }
            if (last_in) {
                table_data.push(last_in);
            }
            
            const d = new frappe.ui.Dialog({
                title: 'Edit Check-in/Out Records',
                fields: [
                    {
                        fieldtype: 'HTML',
                        fieldname: 'time_format_note',
                        options: `<div style="color:red; font-weight:bold; margin-bottom:10px;">
                                    Please use the 24-hour time format.
                                </div>`
                    },
                    {
                        label: 'Punch Details',
                        fieldname: 'punch_table',
                        fieldtype: 'Table',
                        reqd: 1,
                        // cannot_add_rows: 1,
                        // in_place_edit: true,
                        fields: [
                            {
                                fieldtype: 'Time',
                                fieldname: 'in_time',
                                label: 'In Time',
                                in_list_view: 1
                            },
                            {
                                fieldtype: 'Time',
                                fieldname: 'out_time',
                                label: 'Out Time',
                                in_list_view: 1,
                                width: '1000px' 
                            },
                            {
                                fieldtype: 'Link',
                                fieldname: 'employee_checkin',
                                label: 'Employee Checkin',
                                options: 'Employee Checkin',
                                read_only: 1,
                                // in_list_view: 1
                            }
                        ]
                    },
                    {
                        label: 'Reason',
                        fieldname: 'reason',
                        fieldtype: 'Small Text',
                        reqd: 1
                    }
                ],
                primary_action_label: 'Submit Regularization',
                primary_action(values) {
                    const all_entries = values.punch_table;
                    const reason = values.reason
                    if (!all_entries.length) {
                        frappe.msgprint('No entries to submit.');
                        return;
                    }

                    frappe.call({
                        method: "prompt_hr.py.attendance.create_attendance_regularization",
                        args: {
                            attendance_id: frm.doc.name,
                            update_data: all_entries,
                            reason: reason
                        },
                        callback: function (res) {
                            // frappe.msgprint(`Regularization Created: <a href="/app/attendance-regularization/${res.message.attendance_regularization_id}">${res.message.attendance_regularization_id}</a>`);
                            d.hide();
                            frm.reload_doc();
                        }
                    })
                    // frappe.call({
                    //     method: 'frappe.client.insert',
                    //     args: {
                    //         doc: {
                    //             doctype: 'Attendance Regularization',
                    //             employee: frm.doc.employee,
                    //             attendance: frm.doc.name,
                    //             regularization_date: frm.doc.attendance_date,
                    //             checkinpunch_details: all_entries
                    //         }
                    //     },
                    //     callback(res) {
                    //         console.log(res)
                    //         frappe.msgprint(`Regularization Created: <a href="/app/attendance-regularization/${res.message.name}">${res.message.name}</a>`);
                    //     }
                    // });
                }
            });

            d.show();        
            setTimeout(() => {
                const grid = d.fields_dict.punch_table.grid;
                grid.df.data = table_data;
                grid.refresh();
            }, 100);
        }
    });
}

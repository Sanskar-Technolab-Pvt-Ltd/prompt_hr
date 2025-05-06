frappe.ui.form.on('Payroll Entry', {
    refresh: function(frm) {
        add_main_fnf_button(frm);
        render_fnf_buttons(frm);
        setup_grid_watchers(frm);
    }
});

// ? Add top-level "Process FnF" button
function add_main_fnf_button(frm) {
    frm.add_custom_button('Process FnF', function () {
        window.location.href = `${window.location.origin}/app/full-and-final-statement/new-1`;
    });
}

// ? Render row-wise "Process FnF" button inside grid cell
function render_fnf_buttons(frm) {
    $('.fnf-row-btn').remove(); // clear old buttons

    const rows = frm.doc.custom_pending_fnf_details || [];

    $('.grid-row').each(function () {
        const rowIdx = parseInt($(this).attr('data-idx')) - 1;
        const rowData = rows[rowIdx];

        if (!rowData || rowData.is_fnf_processed !== 0) return;

        const fnfCell = $(this).find('[data-fieldname="fnf_record"] .field-area');
        if (!fnfCell.length || fnfCell.find('.fnf-row-btn').length > 0) return;

        // Ensure container is relatively positioned
        fnfCell.css('position', 'relative');

        // Create button
        const $btn = $(`
            <div class="btn btn-primary btn-xs" style="
                position: absolute;
                top: 50%;
                right: 4px;
                transform: translateY(-50%);
                background-color: black;
                color: white;
                padding: 3px 6px;
                border-radius: 3px;
                font-size: 11px;
                cursor: pointer;
                z-index: 10;
                width: 100%;
            ">
                Process FnF
            </div>
        `);

        $btn.on('click', function (e) {
            e.stopPropagation(); // prevent grid selection
            const emp = encodeURIComponent(rowData.employee || '');
            window.location.href = `${window.location.origin}/app/full-and-final-statement/new-1?employee=${emp}`;
        });

        fnfCell.append($btn);
    });
}

// ? Observe grid changes (row add/delete/edit)
function setup_grid_watchers(frm) {
    const wrapper = frm.fields_dict.custom_pending_fnf_details.grid.wrapper.get(0);

    if (window._fnf_observer) window._fnf_observer.disconnect();

    const observer = new MutationObserver(() => {
        setTimeout(() => render_fnf_buttons(frm), 150);
    });

    observer.observe(wrapper, {
        childList: true,
        subtree: true
    });

    window._fnf_observer = observer;
}

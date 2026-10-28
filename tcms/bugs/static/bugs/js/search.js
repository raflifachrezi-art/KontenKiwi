import { initializeDateTimePicker } from '../../../../static/js/datetime_picker'
import { dataTableJsonRPC } from '../../../../static/js/jsonrpc'
import { exportButtons } from '../../../../static/js/datatables_common'
import { escapeHTML, updateBuildSelectFromVersion, updateVersionSelectFromProduct } from '../../../../static/js/utils'

export function pageBugsSearchReadyHandler () {
    initializeDateTimePicker('#id_before')
    initializeDateTimePicker('#id_after')

    const table = $('#resultsTable').DataTable({
        pageLength: $('#navbar').data('defaultpagesize'),
        ajax: function (data, callback, settings) {
            const params = {}

            if ($('#id_summary').val()) {
                params.summary__icontains = $('#id_summary').val()
            }

            if ($('#id_severity').val()) {
                params.severity = $('#id_severity').val()
            };

            if ($('#id_product').val()) {
                params.product = $('#id_product').val()
            };

            if ($('#id_version').val()) {
                params.version = $('#id_version').val()
            };

            if ($('#id_build').val()) {
                params.build = $('#id_build').val()
            };

            if ($('#id_reporter').val()) {
                params.reporter__username__startswith = $('#id_reporter').val()
            };

            if ($('#id_assignee').val()) {
                params.assignee__username__startswith = $('#id_assignee').val()
            };

            if ($('#id_before').val()) {
                params.created_at__lte = $('#id_before').data('DateTimePicker').date().format('YYYY-MM-DD 23:59:59')
            }

            if ($('#id_after').val()) {
                params.created_at__gte = $('#id_after').data('DateTimePicker').date().format('YYYY-MM-DD 00:00:00')
            }

            if ($('#id_status_code').val()) {
                params.status_code = $('#id_status_code').val()
            }

            dataTableJsonRPC('Bug.filter', params, callback)
        },
        columns: [
            { data: 'pk' },
            {
                data: null,
                render: function (data, type, full, meta) {
                    if (data.severity__name) {
                        return `<span class="${data.severity__icon}" style="color: ${data.severity__color}"></span> ${data.severity__name}`
                    }

                    return ''
                }
            },
            {
                data: null,
                render: function (data) {
                    const status = data.status_code || (data.status ? 'OPEN' : 'CLOSED')
                    const badges = {
                        STUCK: '<span class="label label-danger" style="font-size: 11px;"><i class="fa fa-exclamation-triangle"></i> STUCK</span>',
                        IN_PROGRESS: '<span class="label label-warning" style="font-size: 11px;"><i class="fa fa-clock-o"></i> IN PROGRESS</span>',
                        OPEN: '<span class="label label-primary" style="font-size: 11px;"><i class="fa fa-envelope-open"></i> OPEN</span>',
                        RESOLVED: '<span class="label label-success" style="font-size: 11px;"><i class="fa fa-check-circle"></i> RESOLVED</span>',
                        CLOSED: '<span class="label label-default" style="font-size: 11px;"><i class="fa fa-times-circle"></i> CLOSED</span>',
                        WONT_FIX: '<span class="label label-default" style="font-size: 11px;"><i class="fa fa-ban"></i> WONT FIX</span>'
                    }
                    return badges[status] || `<span class="label label-info">${status}</span>`
                }
            },
            {
                data: null,
                render: function (data, type, full, meta) {
                    return '<a href="/bugs/' + data.pk + '/" target="_parent">' + escapeHTML(data.summary) + '</a>'
                }
            },
            { data: 'created_at' },
            { data: 'product__name' },
            { data: 'version__value' },
            { data: 'build__name' },
            { data: 'reporter__username' },
            { data: 'assignee__username' }
        ],
        dom: 'Biptip',
        buttons: exportButtons,
        language: {
            info: $('#main-element').data('trans-x-records-found'),
            infoEmpty: $('#main-element').data('trans-no-records-found'),
            loadingRecords: '<div class="spinner spinner-lg"></div>',
            processing: '<div class="spinner spinner-lg"></div>',
            thousands: '',
            zeroRecords: $('#main-element').data('trans-no-records-found')
        },
        order: [[0, 'asc']]
    })

    $('#btn_search').click(function () {
        table.ajax.reload()
        return false // so we don't actually send the form
    })

    $('#id_product').change(function () {
        updateVersionSelectFromProduct()
    })

    $('#id_version').change(function () {
        updateBuildSelectFromVersion(true)
    })
}

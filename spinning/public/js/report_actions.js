function get_merge_wise_package_details(batch_no, warehouse) {
	let template = `
		<table class="table table-bordered" style="margin: 0;">
			<thead>
				<th>{{ __("Package") }}</th>
				<th>{{ __("Type") }}</th>
				<th>{{ __("Spools") }}</th>
				<th>{{ __("Gross Weight") }}</th>
				<th>{{ __("Net Weight") }}</th>
				<th>{{ __("Reamining Qty") }}</th>
				<th>{{ __("Status") }}</th>
			</thead>
			<tbody>
				{% for (let row of data ) { %}
					<tr>
						<td>{{ __(row['name']) }}</td>
						<td>{{ __(row['package_type']) }}</td>
						<td>{{ __(row['spools']) }}</td>
						<td>{{ __(row['gross_weight']) }}</td>
						<td>{{ __(row['net_weight']) }}</td>
						<td>{{ __(row['remaining_qty']) }}</td>
						<td>{{ __(row['status']) }}</td>
						
					</tr>
				{% } %}
			</tbody>
		</table>`;

	frappe.call({
		method: "spinning.api.get_merge_wise_package_details",
		args: {
			batch_no: batch_no,
			warehouse: warehouse
		},
		callback: function(r){
			let message = frappe.template.compile(template)({'data': r.message});
			frappe.msgprint({
				message: message, 
				title: "Package Details",
				wide: true,
			});
		}
	})
}
frappe.listview_settings['Package'] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		return [__(doc.status), {
			"In Stock": "green",
			"Partial Stock": "orange",
			"Out of Stock": "red"
		}[doc.status], "status,=," + doc.status];
	}
};
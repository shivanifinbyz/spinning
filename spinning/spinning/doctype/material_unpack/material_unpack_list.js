frappe.listview_settings['Material Unpack'] = {	
	add_fields: ["status"],		
	get_indicator: function (doc) {
		return [__(doc.status), {
			"Unpacked": "blue",
			"Partially Repacked":"orange",
			"Repacked": "green",
			
		}[doc.status], "status,=," + doc.status];
	}
};
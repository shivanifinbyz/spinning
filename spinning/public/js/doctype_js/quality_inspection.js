cur_frm.fields_dict.reference_name.get_query = function(doc){
	if(doc.reference_type == "Work Order"){
		return {
			"filters": {
				'merge': doc.merge
			}
		}
	}
}

frappe.ui.form.on("Quality Inspection", {
	reference_name: function(frm){
		frm.set_value('merge', "")
 		if(frm.doc.reference_type == "Work Order"){
 			frappe.db.get_value('Work Order',frm.doc.reference_name,"merge",function(r){
 				frm.set_value('merge',r.merge)
 			})
 		}
 	},
});
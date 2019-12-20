// Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Merge', {
	refresh: function(frm) {
		frm.fields_dict.quality_inspection_template.get_query = function(doc) {
			return {
				filters: {
					"merge": frm.doc.merge,
					"item": frm.doc.item_code
				}
			}
		};
	},
	onload: function(frm){
		frm.trigger('override_quality_inspection_template_new_doc');
	},
	override_quality_inspection_template_new_doc: function(frm){
		let quality_inspection_template_field = frm.get_docfield("quality_inspection_template");
		let merge = frm.doc.merge;
		let join = "_";
		let item = frm.doc.item_code;
		let quality_inspection_template_name = merge.concat(join, item);
		quality_inspection_template_field.get_route_options_for_new_doc = function(field){
			return {
				'quality_inspection_template_name': quality_inspection_template_name,
				'item': item,
				'merge': merge,
			}
		}
	},
});

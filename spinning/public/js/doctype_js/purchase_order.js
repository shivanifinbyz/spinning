
frappe.ui.form.on("Purchase Order", {
	onload: function(frm){
		cur_frm.remove_custom_button('Material to Supplier', 'Transfer');
	},
	refresh: function (frm) {
		cur_frm.remove_custom_button('Material to Supplier', 'Transfer');
		var me = this;
		if(frm.doc.status != "Closed") {
			if (frm.doc.status != "On Hold") {
				if(frm.doc.is_subcontracted === "Yes" && frm.doc.docstatus == 1) {
					cur_frm.add_custom_button(__('Material to Supplier'),
						function() { frm.trigger('make_transfer'); }, __("Subcontract"));
				}
			}
		}
	},
	make_transfer: function(frm) {
		var items = $.map(cur_frm.doc.items, function(d) { return d.bom ? d.item_code : false; });
		var me = this;
		
		if(items.length >= 1){
			let raw_material_data = [];
			let show_dialog = 1;
			let title = __('Transfer Material to Supplier');
			let fields = [
			{fieldtype:'Section Break', label: __('Raw Materials')},
			{fieldname: 'sub_con_rm_items_', fieldtype: 'Table', label: __('Items'),
				fields: [
					{
						fieldtype:'Data',
						fieldname:'item_code',
						label: __('Item'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Data',
						fieldname:'rm_item_code',
						label: __('Raw Material'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'qty',
						label: __('Quantity'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Data',
						read_only:1,
						fieldname:'warehouse',
						label: __('Reserve Warehouse'),
						in_list_view:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'rate',
						label: __('Rate'),
						hidden:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'amount',
						label: __('Amount'),
						hidden:1
					},
					{
						fieldtype:'Link',
						read_only:1,
						fieldname:'uom',
						label: __('UOM'),
						hidden:1
					}
				],
				data: raw_material_data,
				get_data: function() {
					return raw_material_data;
				}
			}
		]

		var dialog = new frappe.ui.Dialog({
			title: title, fields: fields
		});

		if (frm.doc['supplied_items']) {
			frm.doc['supplied_items'].forEach((item, index) => {
			if (item.rm_item_code && item.main_item_code) {
					raw_material_data.push ({
						'name':item.name,
						'item_code': item.main_item_code,
						'rm_item_code': item.rm_item_code,
						'item_name': item.rm_item_code,
						'qty': item.required_qty,
						'warehouse':item.reserve_warehouse,
						'rate':item.rate,
						'amount':item.amount,
						'stock_uom':item.stock_uom
					});
					dialog.fields_dict.sub_con_rm_items_.grid.refresh();
				}
			})
		}

		dialog.show()
		dialog.set_primary_action(__('Add'), function() {
			var values = dialog.get_values();
			if(values) {
				values.sub_con_rm_items_.map((row,i) => {
					if (!row.item_code || !row.rm_item_code || !row.warehouse || !row.qty || row.qty === 0) {
						frappe.throw(__("Item Code, warehouse, quantity are required on row" + (i+1)));
					}
				})
				
				frm.events._make_rm_mt(frm,dialog.fields_dict.sub_con_rm_items_.grid.get_selected_children())
				dialog.hide()
				}
			});
		}

		dialog.get_close_btn().on('click', () => {
			dialog.hide();
		});

	},

	_make_rm_mt: function(frm,rm_items_) {
		frappe.call({
			method:"spinning.doc_events.purchase_order.create_transfer",
			args: {
				purchase_order: cur_frm.doc.name,
				rm_items: rm_items_
			}
			,
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},
});
/* erpnext.buying.PurchaseOrderController = erpnext.buying.BuyingController.extend({
	refresh: function(doc, cdt, cdn) {
		var me = this;
		this._super();
	}
}) */
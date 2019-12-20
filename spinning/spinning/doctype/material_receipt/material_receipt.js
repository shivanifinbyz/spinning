// Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
// For license information, please see license.txt
frappe.provide("erpnext.stock");

cur_frm.fields_dict['items'].grid.get_field("merge").get_query = function(doc, cdt, cdn) {
	let d = locals[cdt][cdn];

	return {
		filters: {
			"item_code": d.item_code
		}
	}
};
cur_frm.fields_dict['items'].grid.get_field("grade").get_query = function(doc, cdt, cdn) {
	let d = locals[cdt][cdn];

	return {
		query: 'spinning.controllers.queries.grade_query',
		filters: {
			"item_code": d.item_code
		}
	}
};
cur_frm.fields_dict['items'].grid.get_field("t_warehouse").get_query = function(doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};

cur_frm.fields_dict['pallet_item'].grid.get_field("pallet_item").get_query = function(doc) {
	return {
		filters: {
			"item_group": 'Pallet'
		}
	}
};
cur_frm.fields_dict.package_item.get_query = function (doc) {
    return {
        filters: {
            "item_group": doc.package_type
        }
    }
};
frappe.ui.form.on('Material Receipt', {
	validate: function(frm){
		
		$.each(frm.doc.items || [], function(i, d) {
			if(d.merge){	
				/* frappe.call({
					method:"spinning.controllers.merge_validation.validate_merge_with_doc",
					args:{
						doc: d,
						merge: d.merge,
						item_code:d.item_code
					},
					callback: function(r){
						console.log(r)
						frappe.validated = false;
					}
				})  */
				 frappe.db.get_value("Merge",d.merge,'item_code',function(r){
					if(r){
						if(r.item_code!=d.item_code){
							frappe.msgprint(__("Please select correct merge for the item"))
							frappe.validated = false;
						}
					}
				}) 
			}
		});
	},
	company: function(frm) {
		if(frm.doc.company) {
			var company_doc = frappe.get_doc(":Company", frm.doc.company);
			if(company_doc.default_letter_head) {
				frm.set_value("letter_head", company_doc.default_letter_head);
			}
			frm.trigger("toggle_display_account_head");
		}
	},
	set_basic_rate: function(frm, cdt, cdn) {
		const item = locals[cdt][cdn];
		item.transfer_qty = flt(item.qty) * flt(item.conversion_factor);

		const args = {
			'item_code'			: item.item_code,
			'posting_date'		: frm.doc.posting_date,
			'posting_time'		: frm.doc.posting_time,
			'warehouse'			: cstr(item.s_warehouse) || cstr(item.t_warehouse),
			'serial_no'			: item.serial_no,
			'company'			: frm.doc.company,
			'qty'				: item.s_warehouse ? -1*flt(item.transfer_qty) : flt(item.transfer_qty),
			'voucher_type'		: frm.doc.doctype,
			'voucher_no'		: item.name,
			'allow_zero_valuation': 1,
		};

		if (item.item_code || item.serial_no) {
			frappe.call({
				method: "erpnext.stock.utils.get_incoming_rate",
				args: {
					args: args
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, 'basic_rate', (r.message || 0.0));
					frm.events.calculate_basic_amount(frm, item);
				}
			});
		}
	},

	get_warehouse_details: function(frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if(!child.bom_no) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_warehouse_details",
				args: {
					"args": {
						'item_code': child.item_code,
						'warehouse': cstr(child.s_warehouse) || cstr(child.t_warehouse),
						'transfer_qty': child.transfer_qty,
						'serial_no': child.serial_no,
						'qty': child.s_warehouse ? -1* child.transfer_qty : child.transfer_qty,
						'posting_date': frm.doc.posting_date,
						'posting_time': frm.doc.posting_time,
						'company': frm.doc.company,
						'voucher_type': frm.doc.doctype,
						'voucher_no': child.name,
						'allow_zero_valuation': 1
					}
				},
				callback: function(r) {
					if (!r.exc) {
						$.extend(child, r.message);
						frm.events.calculate_basic_amount(frm, child);
					}
				}
			});
		}
	},

	calculate_basic_amount: function(frm, item) {
		item.basic_amount = flt(flt(item.transfer_qty) * flt(item.basic_rate),
			precision("basic_amount", item));

		frm.events.calculate_amount(frm);
	},

	calculate_amount: function(frm) {
		frm.events.calculate_total_additional_costs(frm);

		const total_basic_amount = frappe.utils.sum(
			(frm.doc.items || []).map(function(i) { return i.t_warehouse ? flt(i.basic_amount) : 0; })
		);

		for (let i in frm.doc.items) {
			let item = frm.doc.items[i];

			if (item.t_warehouse && total_basic_amount) {
				item.additional_cost = (flt(item.basic_amount) / total_basic_amount) * frm.doc.total_additional_costs;
			} else {
				item.additional_cost = 0;
			}

			item.amount = flt(item.basic_amount + flt(item.additional_cost),
				precision("amount", item));

			item.valuation_rate = flt(flt(item.basic_rate)
				+ (flt(item.additional_cost) / flt(item.transfer_qty)),
				precision("valuation_rate", item));
		}

		refresh_field('items');
	},

	calculate_total_additional_costs: function(frm) {
		const total_additional_costs = frappe.utils.sum(
			(frm.doc.additional_costs || []).map(function(c) { return flt(c.amount); })
		);

		frm.set_value("total_additional_costs",
			flt(total_additional_costs, precision("total_additional_costs")));
	},

	onload: function(frm){
		frm.trigger('override_merge_new_doc');
		frm.trigger('override_grade_new_doc');
		frm.trigger('set_options_for_row_ref');
	},
	before_save: function(frm){
		frm.trigger('cal_total_package_gross_wt');
		frm.trigger('cal_total_package_net_wt');
		frm.trigger('cal_total');
		frm.trigger('calculate_amount');
	},
	override_merge_new_doc: function(frm){
		let merge_field = cur_frm.get_docfield("items", "merge")

		merge_field.get_route_options_for_new_doc = function(row){
			return {
				'item_code': row.doc.item_code
			}
		}
	},
	
	override_grade_new_doc: function(frm){
		let grade_field = cur_frm.get_docfield("items", "grade")

		grade_field.get_route_options_for_new_doc = function(row){
			return {
				'supplier': frm.doc.supplier
			}
		}
	},

	set_options_for_row_ref: function(frm){
		let options = [];
		let row_ref_doc_field = frm.get_docfield("packages", "row_ref");
		const items_length = frm.doc.items.length;

		for(let i = 1; i <= items_length; i++){
			options.push(i.toString())
		}
		row_ref_doc_field.options = options.join("\n");
	},
	
	cal_total_package_gross_wt: function(frm){
		const total_gross_wt = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.gross_weight }));
		frm.set_value("total_package_gross_weight", flt(total_gross_wt));
	},

	cal_total_package_net_wt: function(frm){
		const total_net_wt = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.net_weight }));
		frm.set_value("total_package_net_weight", flt(total_net_wt));
	},
	cal_total: function(frm){
		let total_amount = 0.0;
		let total_qty = 0.0;
		frm.doc.items.forEach(function (d) {
			frappe.model.set_value(d.doctype,d.name,"amount",flt(d.qty*d.basic_rate));
			total_amount += flt(d.amount);
			total_qty += flt(d.qty)
		});
		frm.set_value("total_amount",total_amount)
		frm.set_value("total_qty",total_qty)
	},
	package_item: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.package_item = frm.doc.package_item;
		});
		refresh_field("packages");
	},
	package_type: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.package_type = frm.doc.package_type;
		});
		refresh_field("packages");
	},
	is_returnable: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.is_returnable = frm.doc.is_returnable;
		});
		refresh_field("packages");
	},
	returnable_by: function(frm) {
		$.each(frm.doc.packages || [], function(i, d) {
			d.returnable_by = frm.doc.returnable_by;
		});
		refresh_field("packages");
	},
});

frappe.ui.form.on('Material Receipt Item', {
	items_add: function(frm, cdt, cdn){
		frm.events.set_options_for_row_ref(frm);
	},

	items_remove: function(frm, cdt, cdn){
		frm.events.set_options_for_row_ref(frm);
	},
	qty: function(frm, cdt, cdn){
		frm.events.cal_total(frm);
		frm.events.set_basic_rate(frm, cdt, cdn);
	},
	conversion_factor: function(frm, cdt, cdn) {
		frm.events.set_basic_rate(frm, cdt, cdn);
	},
	t_warehouse: function(frm, cdt, cdn) {
		frm.events.get_warehouse_details(frm, cdt, cdn);
	},

	basic_rate: function(frm, cdt, cdn) {
		var item = locals[cdt][cdn];
		frm.events.calculate_basic_amount(frm, item);
	},
	rate: function(frm, cdt, cdn){
		frm.events.cal_total(frm);
	},
	uom: function(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.uom && d.item_code){
			return frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_uom_details",
				args: {
					item_code: d.item_code,
					uom: d.uom,
					qty: d.qty
				},
				callback: function(r) {
					if(r.message) {
						frappe.model.set_value(cdt, cdn, r.message);
					}
				}
			});
		}
	},
	item_code: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.item_code) {
			var args = {
				'item_code'			: d.item_code,
				'warehouse'			: cstr(d.s_warehouse) || cstr(d.t_warehouse),
				'transfer_qty'		: d.transfer_qty,
				'serial_no'		: d.serial_no,
				'bom_no'		: d.bom_no,
				'expense_account'	: d.expense_account,
				'cost_center'		: d.cost_center,
				'company'		: frm.doc.company,
				'qty'			: d.qty,
				'voucher_type'		: frm.doc.doctype,
				'voucher_no'		: d.name,
				'allow_zero_valuation': 1,
			};

			return frappe.call({
				doc: frm.doc,
				method: "get_item_details",
				args: args,
				callback: function(r) {
					if(r.message) {
						var d = locals[cdt][cdn];
						$.each(r.message, function(k, v) {
							d[k] = v;
						});
						frm.events.calculate_amount(frm);
						refresh_field("items");
					}
				}
			});
		}
	},
	expense_account: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "expense_account");
	},
	cost_center: function(frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "cost_center");
	},
});

frappe.ui.form.on("Material Receipt Package Detail", {
	gross_weight: function(frm, cdt, cdn){
		frm.events.cal_total_package_gross_wt(frm)
	},

	net_weight: function(frm, cdt, cdn){
		frm.events.cal_total_package_net_wt(frm)
	},

	packages_remove: function(frm, cdt, cdn){
		frm.events.cal_total_package_net_wt(frm)
	},
	packages_add: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		row.package_item = frm.doc.package_item;
		row.package_type = frm.doc.package_type;
		row.is_returnable = frm.doc.is_returnable;
		row.returnable_by = frm.doc.returnable_by;
		frm.refresh_field("packages");
	},
});

erpnext.stock.MaterialReceipt = erpnext.stock.StockController.extend({
	setup: function() {
		var me = this;

		this.setup_posting_date_time_check();

		this.frm.fields_dict.items.grid.get_field('item_code').get_query = function() {
			return erpnext.queries.item({is_stock_item: 1});
		};
		
		if(me.frm.doc.company && erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
			this.frm.add_fetch("company", "stock_adjustment_account", "expense_account");
		}
	
		this.frm.fields_dict.items.grid.get_field('expense_account').get_query = function() {
			if (erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					filters: {
						"company": me.frm.doc.company,
						"is_group": 0
					}
				}
			}
		}
		
		this.frm.set_indicator_formatter('item_code',
			function(doc) {
				if (!doc.s_warehouse) {
					return 'blue';
				} else {
					return (doc.qty<=doc.actual_qty) ? "green" : "orange"
				}
		})

	},
	onload_post_render: function() {
		var me = this;
		this.set_default_account(function() {
			if(me.frm.doc.__islocal && me.frm.doc.company && !me.frm.doc.amended_from) {
				me.frm.trigger("company");
			}
		});

		this.frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},
	set_default_account: function(callback) {
		var me = this;

		if(this.frm.doc.company && erpnext.is_perpetual_inventory_enabled(this.frm.doc.company)) {
			return this.frm.call({
				method: "erpnext.accounts.utils.get_company_default",
				args: {
					"fieldname": "stock_adjustment_account",
					"company": this.frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) {
						$.each(me.frm.doc.items || [], function(i, d) {
							if(!d.expense_account) d.expense_account = r.message;
						});
						if(callback) callback();
					}
				}
			});
		}
	},
	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("items", row, ["expense_account", "cost_center"]);

		if(!row.t_warehouse) row.t_warehouse = this.frm.doc.warehouse;
	},
});	
$.extend(cur_frm.cscript, new erpnext.stock.MaterialReceipt({frm: cur_frm}));
// Copyright (c) 2019, FinByz Tech Pvt Ltd and contributors
// For license information, please see license.txt
frappe.provide("erpnext.stock");

frappe.ui.form.on('Material Transfer', {
	setup: function(frm) {
		frm.set_query('batch_no', 'items', function(doc, cdt, cdn) {
			var item = locals[cdt][cdn];
			if(!item.item_code) {
				frappe.throw(__("Please enter Item Code to get Batch Number"));
			} else {
				var filters = {
					'item_code': item.item_code
				}

				if(doc.warehouse) filters["warehouse"] = doc.warehouse;

				return {
					query : "spinning.controllers.queries.batch_query",
					filters: filters
				}
			}
		})

		frm.fields_dict.packages.grid.get_field('package').get_query = function(doc) {
			return {
				filters: {
					"status": ["!=", "Out of Stock"],
					"warehouse": doc.s_warehouse
				}
			}
		}

		frm.fields_dict.work_order.get_query = function(doc) {
			return {
				filters: {
					'status': "In Process",
					"workstation": doc.workstation
				}
			}
		}

		frm.add_fetch('work_order', 'wip_warehouse', 't_warehouse');
	},
	refresh: function(frm){
		$('*[data-fieldname="packages"]').find('.grid-add-row').hide();
	},
	s_warehouse: function(frm, cdt, cdn){
		// erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "s_warehouse");
		erpnext.utils.copy_parent_value_in_all_row(frm.doc, cdt, cdn, "items", "s_warehouse", "s_warehouse");
	},

	t_warehouse: function(frm, cdt, cdn){
		// erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "t_warehouse");
		erpnext.utils.copy_parent_value_in_all_row(frm.doc, cdt, cdn, "items", "t_warehouse", "t_warehouse");
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

	work_order: function(frm){
		if(cint(frm.doc.is_material_transfer_for_manufacture) && frm.doc.work_order){
			frappe.call({
				doc: frm.doc,
				method: "get_wo_required_items",
				args: {
					work_order: frm.doc.work_order
				},
				callback: function(r){
					if(r.message){
						frm.clear_table('items');
						
						r.message.forEach(function(row){
							let c = frm.add_child('items')
							$.each(row, function(k, v) {
								frappe.model.set_value(c.doctype, c.name, k, v)
							});
						})
						
						frm.refresh_field('items');
					}
				}
			})
		}
	},

	toggle_display_account_head: function(frm) {
		var enabled = erpnext.is_perpetual_inventory_enabled(frm.doc.company);
		frm.fields_dict["items"].grid.set_column_disp(["cost_center", "expense_account"], enabled);
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
						'warehouse': cstr(child.s_warehouse) || cstr(item.t_warehouse),
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

		item.amount = flt(item.basic_amount,
			precision("amount", item));

		frm.events.calculate_totals(frm);
		refresh_field('items');
	},

	calculate_totals: function(frm){
		const total_qty = frappe.utils.sum((frm.doc.items || []).map(function(i){ return i.qty }));
		const total_amount = frappe.utils.sum((frm.doc.items || []).map(function(i){ return i.amount }));

		frm.set_value('total_qty', total_qty);
		frm.set_value('total_amount', total_amount);
	},

	calculate_weights: function(frm){
		const total_gross_weight = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.gross_weight }));
		const total_net_weight = frappe.utils.sum((frm.doc.packages || []).map(function(i){ return i.net_weight }));
		
		frm.set_value('total_gross_weight', total_gross_weight);
		frm.set_value('total_net_weight', total_net_weight);
	},

	add_packages: function(frm){
		frappe.db.get_value("Company", frm.doc.company, 'default_source_warehouse', function(r){
			let warehouse = frm.doc.s_warehouse ? frm.doc.s_warehouse : r.default_source_warehouse;
			select_packages({frm: frm, warehouse: warehouse});
		})
	}
});


frappe.ui.form.on('Material Transfer Item', {
	qty: function(frm, cdt, cdn) {
		frm.events.set_basic_rate(frm, cdt, cdn);
	},

	conversion_factor: function(frm, cdt, cdn) {
		frm.events.set_basic_rate(frm, cdt, cdn);
	},

	s_warehouse: function(frm, cdt, cdn) {
		frm.events.get_warehouse_details(frm, cdt, cdn);
	},

	t_warehouse: function(frm, cdt, cdn) {
		frm.events.get_warehouse_details(frm, cdt, cdn);
	},

	basic_rate: function(frm, cdt, cdn) {
		var item = locals[cdt][cdn];
		frm.events.calculate_basic_amount(frm, item);
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
				'warehouse'			: cstr(frm.doc.s_warehouse),
				'transfer_qty'		: d.transfer_qty,
				'expense_account'	: d.expense_account,
				'cost_center'		: d.cost_center,
				'company'			: frm.doc.company,
				'qty'				: d.qty,
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
						// console.log("IDX : " + d.idx);
						$.each(r.message, function(k, v) {
							d[k] = v;
							// console.log(k + " : " + v);
						});

						frm.events.set_basic_rate(frm, cdt, cdn);
						
						refresh_field("items");
						
						if(d.has_batch_no){
							setTimeout(function(){
								select_packages({frm: frm, item_code: d.item_code, merge: d.merge, warehouse: frm.doc.s_warehouse});
							}, 500);
						}
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

frappe.ui.form.on("Material Transfer Package", {
	packages_add: function(frm, cdt, cdn){
		frm.events.calculate_weights(frm);
	},

	package: function(frm, cdt, cdn){
		frm.events.calculate_weights(frm);
	},
	
	packages_remove: function(frm, cdt, cdn){
		frm.events.calculate_weights(frm);
	}
});

erpnext.stock.MaterialTransfer = erpnext.stock.StockController.extend({
	setup: function(){
		var me = this;

		this.setup_posting_date_time_check();

		this.frm.fields_dict.items.grid.get_field('item_code').get_query = function() {
			return erpnext.queries.item({is_stock_item: 1});
		};

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
		this.frm.script_manager.copy_from_first_row("items", row, ["expense_account", "cost_center", "s_warehouse", "t_warehouse"]);

		if(!row.s_warehouse) row.s_warehouse = this.frm.doc.s_warehouse;
		if(!row.t_warehouse) row.t_warehouse = this.frm.doc.t_warehouse;
	},
});

const select_packages = (args) => {
	frappe.require("assets/spinning/js/utils/package_selector.js", function() {
		new PackageSelector(args)
	})
}

$.extend(cur_frm.cscript, new erpnext.stock.MaterialTransfer({frm: cur_frm}));

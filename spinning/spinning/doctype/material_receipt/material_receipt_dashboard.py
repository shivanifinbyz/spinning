from frappe import _

def get_data():
	return {
		'fieldname': 'reference_docname',
		'transactions': [
			{	
				'label': _('Stock Entry'),
				'items': ['Stock Entry']
			},	
		]
	}
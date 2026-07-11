{
    'name': 'Manual Fixed Tax (GST Adjustment)',
    'version': '17.0.1.0.0',
    'summary': 'Fixed-amount taxes computed on Price Unit instead of Quantity, '
                'for entering arbitrary manual GST/tax amounts per line.',
    'description': """
Manual Fixed Tax
================
Odoo's native "Fixed" tax computation type always calculates the tax as:

    Quantity x Fixed Amount

This module adds an option on account.tax, "Manual Fixed Tax", which,
when enabled on a Fixed tax, changes the calculation to:

    Price Unit x Fixed Amount

This allows creating a single "GST - Manual" tax (with Fixed Amount = 1)
that lets users type the exact manual GST/tax figure directly into the
Price Unit field of a line, while Quantity stays locked at 1 - exactly
like a normal priced line, and fully compliant with tax reports since
it is a genuine account.tax with real tax move lines and tax grid tags.
    """,
    'category': 'Accounting',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account', 'sale', 'purchase'],
    'data': [
        'views/account_tax_views.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'data/account_tax_data.xml',
    ],
    'installable': True,
    'application': False,
}

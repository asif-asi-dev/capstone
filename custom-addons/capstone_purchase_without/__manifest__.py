# -*- coding: utf-8 -*-
{
    'name': 'Capstone Purchase Without',
    'summary': 'Purchase orders without standard purchase flow',
    'description': """
        Adds a separate Orders (Without) menu under Purchase and tracks
        purchase orders/lines flagged as without purchase.
    """,
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Purchase',
    'version': '17.0.0.1',
    'depends': [
        'purchase',
        'account',
    ],
    'data': [
        'data/fiscal_position_data.xml',
        'views/account_fiscal_position_views.xml',
        'views/purchase_order_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

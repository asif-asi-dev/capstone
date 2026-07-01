# -*- coding: utf-8 -*-
{
    'name': 'Capstone Sales Without',
    'summary': 'Sales orders without standard sale flow',
    'description': """
        Adds a separate Orders (Without) menu under Sales and tracks
        sale orders/lines flagged as without sale.
    """,
    'author': 'My Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Sales',
    'version': '17.0.0.1',
    'depends': [
        'sale_management',
        'sale_stock',
        'stock',
        'account',
        'capstone_purchase_without',
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

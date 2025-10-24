# -*- coding: utf-8 -*-
{
    'name': "capstone_sales_return_custom",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '17.0.0.1',

    'depends': [
        'base',
        'sale',
        'stock',
        'sale_stock',
        'product',
        'uom',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/transfer_data.xml',
        # 'views/stock_picking.xml',
        'views/sales_return_order.xml',
        'views/sale_return_request.xml',
        'views/return_reason.xml',
        'views/scrap_sale.xml',
        'views/discount_sale_order.xml',
        'views/stock_warehouse.xml',
        'views/menu.xml',
    ],

}


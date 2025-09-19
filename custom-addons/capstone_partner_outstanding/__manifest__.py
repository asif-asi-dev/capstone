{
    "name": "Customer & Vendor Outstanding",
    "version": "17.0.1.0.0",
    "depends": ["account"],
    "author": "Asif Dev",
    "category": "Accounting",
    "description": """
        Show Outstanding Invoices for Customers and Vendors separately.
    """,
    "data": [
        "security/ir.model.access.csv",
        "views/customer_outstanding.xml",
        "views/account_payment_views.xml",
        "views/account_payment_register_view.xml",
    ],
    "installable": True,
    "application": False,
}

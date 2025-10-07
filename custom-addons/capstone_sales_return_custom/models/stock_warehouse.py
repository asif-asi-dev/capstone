from odoo import api, fields, models,_

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    discount_location_id = fields.Many2one(
        'stock.location',
        string='Discount Location',
        domain="[('usage','=','internal')]",
        help="Location to source products/lots for Discount Sales."
    )


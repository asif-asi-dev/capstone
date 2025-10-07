from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    mrp = fields.Float(
        string="MRP",
        help="Maximum Retail Price of the product."
    )
    net_rate_based_on = fields.Selection(
        [
            ('net_rate', 'Net Rate (Sales Price)'),
            ('margin', 'Margin'),
        ],
        string="Net Rate Based On",
        default='net_rate',
        required=True
    )

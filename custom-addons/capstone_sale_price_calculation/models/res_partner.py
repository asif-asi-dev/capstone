from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    margin_percent = fields.Float(
        string="Margin (%)",
        help="Margin percentage to apply for this partner."
    )
    discount_percent = fields.Float(
        string="Discount (%)",
        help="Discount percentage to be applied for this partner.")

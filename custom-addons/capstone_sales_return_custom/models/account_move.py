from odoo import models, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    is_scrap_sale_invoice = fields.Boolean(
        string="Is Scrap Sale Invoice",
        default=False
    )
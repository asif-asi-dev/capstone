from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    fsm_visit_id = fields.Many2one('fsm.shop.visit', string='Visit Reference')
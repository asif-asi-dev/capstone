from odoo import models, fields

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    fsm_visit_id = fields.Many2one('fsm.shop.visit', string='Visit Reference')
    route_id = fields.Many2one('fsm.route', string='Route')

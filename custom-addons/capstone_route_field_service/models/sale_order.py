from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_visit_id = fields.Many2one('fsm.shop.visit', string='Visit Reference')
    route_id = fields.Many2one('fsm.route', string='Route')

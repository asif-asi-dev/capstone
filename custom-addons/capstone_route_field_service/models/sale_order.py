from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_visit_id = fields.Many2one('fsm.shop.visit', string='Visit Reference', index=True)
    route_id = fields.Many2one('fsm.route', string='Sales Route', index=True)
    delivery_route_id = fields.Many2one('shop.delivery.route', string="Delivery Route", related='partner_id.delivery_route_id', store=True, index=True)
    shop_sequence = fields.Integer(string="Shop Sequence", compute="_compute_shop_sequence", store=True, index=True)

    @api.depends('partner_id', 'delivery_route_id')
    def _compute_shop_sequence(self):
        Line = self.env['shop.delivery.route.line']
        for order in self:
            if order.delivery_route_id and order.partner_id:
                line = Line.search([
                    ('route_id', '=', order.delivery_route_id.id),
                    ('shop_id', '=', order.partner_id.id)
                ], limit=1)
                order.shop_sequence = line.sequence or 0
            else:
                order.shop_sequence = 0


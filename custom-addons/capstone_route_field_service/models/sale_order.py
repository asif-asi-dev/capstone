from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fsm_visit_id = fields.Many2one('fsm.shop.visit', string='Visit Reference')
    route_id = fields.Many2one('fsm.route', string='Route')
    delivery_route_id = fields.Many2one('shop.delivery.route', string="Delivery Route", related='partner_id.delivery_route_id', store=True)

    shop_sequence = fields.Integer(
        string="Shop Sequence",
        compute="_compute_shop_sequence",
        store=True
    )

    @api.depends('partner_id', 'delivery_route_id')
    def _compute_shop_sequence(self):
        for order in self:
            sequence = 0
            if order.delivery_route_id and order.partner_id:
                line = self.env['shop.delivery.route.line'].search(
                    [
                        ('route_id', '=', order.delivery_route_id.id),
                        ('shop_id', '=', order.partner_id.id)
                    ],
                    limit=1
                )
                sequence = line.sequence or 0
            order.shop_sequence = sequence


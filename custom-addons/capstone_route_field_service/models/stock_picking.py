from odoo import models, fields,api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_route_id = fields.Many2one('shop.delivery.route', string="Delivery Route", related='partner_id.delivery_route_id', store=True, index=True)
    shop_sequence = fields.Integer(string="Shop Sequence", compute="_compute_shop_sequence", store=True, index=True)

    @api.depends('partner_id', 'delivery_route_id')
    def _compute_shop_sequence(self):
        Line = self.env['shop.delivery.route.line']
        for picking in self:
            if picking.delivery_route_id and picking.partner_id:
                line = Line.search([
                    ('route_id', '=', picking.delivery_route_id.id),
                    ('shop_id', '=', picking.partner_id.id)
                ], limit=1)
                picking.shop_sequence = line.sequence or 0
            else:
                picking.shop_sequence = 0

from odoo import models, fields,api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_route_id = fields.Many2one('shop.delivery.route', string="Delivery Route", related='partner_id.delivery_route_id', store=True)
    shop_sequence = fields.Integer(
        string="Shop Sequence",
        compute="_compute_shop_sequence",
        store=True
    )

    @api.depends('partner_id', 'delivery_route_id')
    def _compute_shop_sequence(self):
        for picking in self:
            sequence = 0
            if picking.delivery_route_id and picking.partner_id:
                line = self.env['shop.delivery.route.line'].search(
                    [
                        ('route_id', '=', picking.delivery_route_id.id),
                        ('shop_id', '=', picking.partner_id.id)
                    ],
                    limit=1
                )
                sequence = line.sequence or 0
            picking.shop_sequence = sequence

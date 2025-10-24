from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    route_id = fields.Many2one('fsm.route', string='Sales Route', index=True)
    distance_from_company = fields.Integer(string="Distance")
    delivery_route_id = fields.Many2one('shop.delivery.route', string="Delivery Route", index=True)

    def write(self, vals):
        res = super().write(vals)
        if 'delivery_route_id' in vals:
            for partner in self:
                # Remove from old routes if changed
                self.env['shop.delivery.route.line'].search([
                    ('shop_id', '=', partner.id),
                    ('route_id', '!=', partner.delivery_route_id.id)
                ]).unlink()
                # Add to new route
                if partner.delivery_route_id:
                    self.env['shop.delivery.route.line'].sudo().create({
                        'route_id': partner.delivery_route_id.id,
                        'shop_id': partner.id
                    }) if not self.env['shop.delivery.route.line'].search([
                        ('shop_id', '=', partner.id),
                        ('route_id', '=', partner.delivery_route_id.id)
                    ], limit=1) else None
        return res



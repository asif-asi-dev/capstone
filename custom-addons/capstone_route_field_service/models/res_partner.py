from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    route_id = fields.Many2one('fsm.route', string='Route')
    distance_from_company = fields.Integer(string="Distance")
    delivery_route_id = fields.Many2one('shop.delivery.route', string="Delivery Route")

    def write(self, vals):
        res = super().write(vals)
        if 'delivery_route_id' in vals:
            for partner in self:
                # Remove from old route if changed
                self.env['shop.delivery.route.line'].search([
                    ('shop_id', '=', partner.id),
                    ('route_id', '!=', partner.delivery_route_id.id)
                ]).unlink()

                # Add to new route if set
                if partner.delivery_route_id:
                    existing_line = self.env['shop.delivery.route.line'].search([
                        ('shop_id', '=', partner.id),
                        ('route_id', '=', partner.delivery_route_id.id)
                    ], limit=1)
                    if not existing_line:
                        self.env['shop.delivery.route.line'].create({
                            'route_id': partner.delivery_route_id.id,
                            'shop_id': partner.id
                        })
        return res


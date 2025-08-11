from odoo import models, fields,api
from odoo.exceptions import ValidationError





class ShopDeliveryRoute(models.Model):
    _name = 'shop.delivery.route'
    _description = 'Shop Delivery Route'

    name = fields.Char(required=True)
    sales_incharge_id = fields.Many2one(
        'res.users',
        string="Sales Incharge",
        help="The person responsible for managing this delivery route."
    )
    line_ids = fields.One2many('shop.delivery.route.line', 'route_id', string="Route Shops")


class ShopDeliveryRouteLine(models.Model):
    _name = 'shop.delivery.route.line'
    _description = 'Shop Delivery Route Line'
    _order = 'sequence'

    route_id = fields.Many2one('shop.delivery.route', required=True, ondelete='cascade')
    shop_id = fields.Many2one('res.partner', domain="[('is_company','=',True)]", required=True)
    sequence = fields.Integer(default=1)

    @api.constrains('shop_id')
    def _check_unique_shop_in_routes(self):
        for rec in self:
            if rec.shop_id:
                existing = self.search([
                    ('shop_id', '=', rec.shop_id.id),
                    ('route_id', '!=', rec.route_id.id)
                ], limit=1)
                if existing:
                    raise ValidationError(
                        f"The shop '{rec.shop_id.display_name}' "
                        "is already assigned to another delivery route."
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto set sequence as last if not provided
            if not vals.get('sequence') and vals.get('route_id'):
                last_seq = self.search(
                    [('route_id', '=', vals['route_id'])],
                    order="sequence desc",
                    limit=1
                ).sequence or 0
                vals['sequence'] = last_seq + 1

        records = super().create(vals_list)

        # Sync delivery route to partner
        for rec in records:
            if rec.shop_id and rec.route_id:
                rec.shop_id.delivery_route_id = rec.route_id
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.shop_id and rec.route_id:
                rec.shop_id.delivery_route_id = rec.route_id
        return res

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_discount_sale = fields.Boolean("Is Discount Sale")
    sale_return_ids = fields.One2many(
        'sale.return.request.line',
        'sale_order_id'
    )
    sale_return_count = fields.Integer(
        string='Sale Returns',
        compute='_compute_sale_return_count'
    )

    def get_available_sale_qty(self, product_id,product_template_id):
        """
        Return available sale quantity for given product template.
        available_qty = total ordered qty - total returned qty
        """
        self.ensure_one()

        # 1️⃣ Total ordered qty from sale.order.line
        order_lines = self.order_line.filtered(
            lambda l: l.product_template_id.id == product_template_id
        )
        ordered_qty = sum(order_lines.mapped('product_uom_qty'))

        # 2️⃣ Total returned qty from sale_return_ids
        return_lines = self.sale_return_ids.filtered(
            lambda r: r.product_id.id == product_id
        )
        returned_qty = sum(return_lines.mapped('return_qty'))

        # 3️⃣ Calculate available sale quantity
        available_qty = ordered_qty - returned_qty

        return available_qty


    def _compute_sale_return_count(self):
        for order in self:
            order.sale_return_count = len(order.sale_return_ids)

    def action_view_sale_returns(self):
        """Open sale return lines related to this order"""
        self.ensure_one()
        action = self.env.ref('capstone_sales_return_custom.action_sale_return_request_line').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {'default_sale_order_id': self.id}
        return action

    def action_confirm(self):
        """Override action_confirm to handle discount sale locations"""
        result = super(SaleOrder, self).action_confirm()
        if self.is_discount_sale:
            if self.warehouse_id.discount_location_id:
                self._update_picking_locations()
            else:
                raise ValidationError("Discount location not found for warehouse %s." % self.warehouse_id.name)
        return result


    def _update_picking_locations(self):
        """Update picking and move locations for discount sales"""
        for picking in self.picking_ids.filtered(lambda p: p.state in ['waiting', 'confirmed', 'assigned']):
            picking.write({'location_id': self.warehouse_id.discount_location_id.id})
            picking.move_ids.write({'location_id': self.warehouse_id.discount_location_id.id})
            move_lines = picking.move_ids.mapped('move_line_ids')
            if move_lines:
                move_lines.write({'location_id': self.warehouse_id.discount_location_id.id})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    def _prepare_procurement_values(self, group_id=False):
        """Pass discount location through procurement values"""
        res = super(SaleOrderLine, self)._prepare_procurement_values(group_id)

        if self.order_id.is_discount_sale and self.order_id.warehouse_id.discount_location_id:
            res.update({
                'discount_location_id': self.order_id.warehouse_id.discount_location_id.id,
                'location_id': self.order_id.warehouse_id.discount_location_id.id
            })

        return res





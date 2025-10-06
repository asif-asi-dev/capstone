from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_discount_sale = fields.Boolean("Is Discount Sale")

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





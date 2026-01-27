from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    return_order_ids = fields.Many2many(
        'sales.return.order',
        'sales_return_order_rel',
        'source_model_id',
        'return_order_id',
        string="Return Orders",
        readonly=True
    )
    return_order_id = fields.Many2one(
        'sales.return.order',
        string="Return Order",
        readonly=True)
    is_replacement = fields.Boolean(default = False)


    def action_open_sales_return_order(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("You can only create returns for done transfers."))

        return {
            'name': _('Create Sales Return'),
            'view_mode': 'form',
            'res_model': 'sales.return.order',
            'type': 'ir.actions.act_window',
            'context': {
                'default_picking_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
            'target': 'current',
        }

    def action_view_return_picking(self):
        self.ensure_one()

        if not self.return_order_ids:
            raise UserError(_("No return orders found for this transfer."))

        # If there's exactly one return order, open it in form view
        if len(self.return_order_ids) == 1:
            return {
                'name': _('Return Transfer'),
                'view_mode': 'form',
                'res_model': 'sales.return.order',
                'type': 'ir.actions.act_window',
                'res_id': self.return_order_ids[0].id,
                'views': [(self.env.ref('capstone_sales_return_custom.view_sales_return_order_form').id, 'form')],
                'context': {'create': False},
                'target': 'current',
            }

        # For multiple return orders, show tree view
        return {
            'name': _('Return Transfers'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sales.return.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.return_order_ids.ids)],
            'context': {
                'create': False,
                'search_default_picking_id': self.id,  # Default filter
            },
            'target': 'current',
        }

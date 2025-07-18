# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SalesReturnOrder(models.Model):
    _name = 'sales.return.order'
    _description = 'Sales Return Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    @api.model
    def default_get(self, fields):
        res = super(SalesReturnOrder, self).default_get(fields)
        picking_id = self.env.context.get('default_picking_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', picking.picking_type_id.warehouse_id.id)
            ], limit=1)
            if not picking_type:
                raise UserError(_("No return picking type found for this warehouse."))
            if not picking.exists():
                return res

            lines = []
            for move in picking.move_line_ids_without_package:
                if not move.product_id:
                    continue
                lines.append((0, 0, {
                    'product_id': move.product_id.id,
                    'quantity': move.quantity,
                    'lot_id':move.lot_id.id,
                    'uom_id': move.product_uom_id.id,
                }))
            res.update({
                'line_ids': lines,
                'picking_id': picking_id,
                'partner_id': picking.partner_id.id,
                'location_id': picking.location_dest_id.id,
                'location_dest_id':picking_type.default_location_dest_id.id
            })
        return res

    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    picking_id = fields.Many2one('stock.picking', string="Delivery")
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)

    return_reason = fields.Selection([
        ('no_sale', 'No Sale'),
        ('wrong_delivery', 'Wrong Delivery'),
        ('manufacturing_defect', 'Manufacturing Defect'),
        ('damaged', 'Damaged'),
    ], string="Return Reason", required=True, tracking=True)

    inspection_result = fields.Selection([
        ('salable', 'Salable'),
        ('manufacturing_defect_return', 'Manufacturing Defect'),
        ('recyclable', 'Recyclable'),
        ('dump', 'Dump'),
        ('no_complaints', 'No Complaints'),
    ], string="Inspection Result", required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('inspected', 'Inspected'),
        ('completed', 'Completed'),
    ], string="Status", default='draft', tracking=True)

    line_ids = fields.One2many('sales.return.order.line', 'return_order_id', string="Return Lines")
    return_picking_id = fields.Many2one('stock.picking', string="Return Transfer", readonly=True)
    location_id = fields.Many2one(
        'stock.location',
        string="Source Location",
        help="Location from which the product is taken."
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        string="Destination Location",
        help="Location to which the product is moved."
    )


    def action_view_return_picking(self):
        self.ensure_one()
        return {
            'name': _('Return Transfer'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.return_picking_id.id,
            'context': {'create': False, 'edit': False}
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.name == _('New'):
                record.name = self.env['ir.sequence'].next_by_code('sales.return.order') or _('New')
            if record.picking_id:
                record.picking_id.write({
                    'return_order_ids': [(4, record.id)]
                })

        return records
    def action_inspect(self):
        self.write({'state': 'inspected'})

    def action_complete(self):
        self.create_return_picking()
        self.write({'state': 'completed'})

    def create_return_picking(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add return lines before completing."))

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', self.picking_id.picking_type_id.warehouse_id.id)
        ], limit=1)

        if not picking_type:
            raise UserError(_("No return picking type found for this warehouse."))

        move_lines = []
        for line in self.line_ids:
            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id':self.location_dest_id.id,
            }

            # Add lot/serial number if tracking is enabled
            if line.product_id.tracking != 'none' and line.lot_id:
                move_vals['move_line_ids'] = [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.uom_id.id,
                    'location_id': self.picking_id.location_dest_id.id,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                    'quantity': line.quantity,
                    'lot_id': line.lot_id.id,
                })]

            move_lines.append((0, 0, move_vals))

        return_picking = self.env['stock.picking'].create({
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': self.picking_id.location_dest_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'origin': self.name,
            'move_ids_without_package': move_lines,
        })

        # Automatically validate the picking
        if return_picking.state != 'done':
            return_picking.button_validate()

        self.return_picking_id = return_picking.id

        return {
            'name': _('Return Transfer'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': return_picking.id,
            'type': 'ir.actions.act_window',
            'context': {'create': False},
        }

class SalesReturnOrderLine(models.Model):
    _name = 'sales.return.order.line'
    _description = 'Sales Return Order Line'

    return_order_id = fields.Many2one('sales.return.order', string="Return Order", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float(string="Return Quantity", required=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure", required=True)
    lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")
    reason = fields.Char(string="Remarks")
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SalesReturnOrder(models.Model):
    _name = 'sales.return.order'
    _description = 'Sales Return Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    picking_id = fields.Many2one('stock.picking', string="Delivery")
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Under Inspection'),
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
    return_request_id = fields.Many2one(
        'sale.return.request',
        string='Return Request'
    )
    picking_ids = fields.One2many('stock.picking', 'return_order_id', string='Pickings')

    def action_view_return_pickings(self):
        self.ensure_one()
        return {
            'name': _('Return Transfers'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.picking_ids.ids)],
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
    def action_process(self):
        self.return_request_id.state = 'processing'
        self.write({'state': 'processing'})


    def action_complete(self):
        self.create_return_picking()
        self.return_request_id.state = 'done'
        self.write({'state': 'completed'})

    def create_return_picking(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add return lines before completing."))

        move_lines = []
        pickings_to_add = []
        for line in self.line_ids:
            warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            if not warehouse:
                raise UserError(_("No warehouse found for the current company."))

            # Get incoming picking type for that warehouse
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)

            if not picking_type:
                raise UserError(_("No return picking type found for this warehouse."))
            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id':line.location_dest_id.id,
            }

            # Add lot/serial number if tracking is enabled
            if line.product_id.tracking != 'none' and line.lot_id:
                move_vals['move_line_ids'] = [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'quantity': line.quantity,
                    'lot_id': line.lot_id.id,
                })]

            # move_lines.append((0, 0, move_vals))

            return_picking = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': self.location_id.id,
                'location_dest_id': line.location_dest_id.id,
                'origin': self.name,
                'move_ids_without_package': [(0, 0, move_vals)],
            })

        # Automatically validate the picking
            if return_picking.state != 'done':
                return_picking.button_validate()
            pickings_to_add.append((4, return_picking.id))

        self.picking_ids = pickings_to_add

class SalesReturnOrderLine(models.Model):
    _name = 'sales.return.order.line'
    _description = 'Sales Return Order Line'
    _order = 'id'

    return_order_id = fields.Many2one('sales.return.order', string="Return Order", required=True, ondelete='cascade')
    quantity = fields.Float(string="Return Quantity", required=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure", required=True)
    lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")
    remarks = fields.Char(string="Remarks")
    location_dest_id = fields.Many2one(
        'stock.location',
        string="Destination Location",
        help="Location to which the product is moved.",
        default=lambda self: self._default_location_dest_id()
    )
    inspection_result = fields.Selection([
        ('salable', 'Salable'),
        ('scrap', 'Scrap'),
        ('scrap_dump', 'Scrap Dump'),
        ('recyclable', 'Recyclable'),
        ('manufacturing_defect', 'Manufacturing Defect'),
    ], string="Inspection Result",default='salable')
    product_id = fields.Many2one('product.product', string="Product")
    return_reason = fields.Char(string="Return Reason")
    return_qty = fields.Float(string="Return Quantity", required=True, digits='Product Unit of Measure')



    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

    @api.onchange('inspection_result')
    def _onchange_inspection_result(self):
        if not self.inspection_result:
            return

        # Get current company's warehouse
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not warehouse:
            return

        # Map selection values to location boolean fields
        result_to_field = {
            'scrap': 'is_scrap_location',
            'scrap_dump': 'is_scrap_dump_location',
            'recyclable': 'is_recyclable_location',
            'manufacturing_defect': 'is_manufacturing_defect_location',
        }

        if self.inspection_result == 'salable':
            # Lot stock location for the warehouse
            self.location_dest_id = warehouse.lot_stock_id.id
        else:
            # Find the corresponding location by boolean field
            boolean_field = result_to_field.get(self.inspection_result)
            if boolean_field:
                location = self.env['stock.location'].search([
                    (boolean_field, '=', True),
                    ('company_id', '=', self.env.company.id),
                    ('location_id', '=', warehouse.view_location_id.id)
                ], limit=1)
                self.location_dest_id = location.id if location else False

    @api.model
    def _default_location_dest_id(self):
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if warehouse:
            lot_stock = warehouse.lot_stock_id.id
        return lot_stock if lot_stock else False
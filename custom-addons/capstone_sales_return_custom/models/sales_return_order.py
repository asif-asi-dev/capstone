# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError
from collections import defaultdict


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

    allowed_product_ids = fields.Many2many("product.product", compute="_compute_allowed_product_ids")


    def _compute_allowed_product_ids(self):
        for rec in self:
            rec.allowed_product_ids = rec.line_ids.mapped("product_id")

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
        for line in self.line_ids:
            if line.return_qty <= 0:
                raise ValidationError(_("Return quantity must be greater than zero for product %s.") % line.product_id.display_name)
        self.write({'state': 'processing'})


    def action_complete(self):
        self.create_return_picking()
        self.return_request_id.state = 'done'
        self.write({'state': 'completed'})

    def create_return_picking(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Please add return lines before completing."))

        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not warehouse:
            raise UserError(_("No warehouse found for the current company."))

        # Group lines by destination location
        lines_by_location = defaultdict(list)
        for line in self.line_ids:
            if not line.location_dest_id:
                raise UserError(_("Destination location is missing for product %s.") % line.product_id.display_name)
            lines_by_location[line.location_dest_id.id].append(line)

        pickings_to_add = []
        for location_dest_id, lines in lines_by_location.items():
            move_vals_list = []

            # Check if any of the lines in this group are "no_complaints_with_return"
            is_customer_return = any(l.inspection_result == "no_complaints_with_return" for l in lines)

            # Select picking type based on inspection result
            picking_type_code = "outgoing" if is_customer_return else "incoming"
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', picking_type_code),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)

            if not picking_type:
                raise UserError(_("No %s picking type found for warehouse %s.") %
                                (picking_type_code, warehouse.name))

            for line in lines:
                move_vals = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.return_qty,
                    'product_uom': line.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': location_dest_id,
                }

                # Add lot/serial number if tracking is enabled
                if line.product_id.tracking != 'none' and line.lot_id:
                    move_vals['move_line_ids'] = [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_id': line.uom_id.id,
                        'location_id': self.location_id.id,
                        'location_dest_id': location_dest_id,
                        'quantity': line.return_qty,
                        'lot_id': line.lot_id.id,
                    })]

                move_vals_list.append((0, 0, move_vals))

            # Create picking
            return_picking = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': self.location_id.id,
                'location_dest_id': location_dest_id,
                'origin': self.name,
                'move_ids_without_package': move_vals_list,
            })

            # For incoming → auto validate, for outgoing → leave in ready
            if not is_customer_return and return_picking.state != 'done':
                return_picking.button_validate()

            pickings_to_add.append((4, return_picking.id))

        # Handle Replacements: creating extra out picking
        replacement_lines = self.line_ids.filtered(lambda l: l.return_type == 'replacement')
        if replacement_lines:
            customer_location = self.partner_id.property_stock_customer
            if not customer_location:
                raise UserError(_("Customer location is missing for partner %s.") % self.partner_id.name)

            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)

            if not picking_type:
                raise UserError(_("No outgoing picking type found for warehouse %s.") % warehouse.name)

            move_vals_list = []
            for line in replacement_lines:
                move_vals = {
                    'name': _("Replacement: %s") % line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.return_qty,
                    'product_uom': line.uom_id.id,
                    'location_id': warehouse.lot_stock_id.id,
                    'location_dest_id': customer_location.id,
                }
                move_vals_list.append((0, 0, move_vals))

            replacement_picking = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': customer_location.id,
                'origin': _("Replacement for %s") % self.name,
                'move_ids_without_package': move_vals_list,
                'is_locked': False,  # Allow manual editing and lot selection
            })

            # Action confirm and assign - Odoo will handle reservaion and move lines
            replacement_picking.action_confirm()
            replacement_picking.action_assign()

            pickings_to_add.append((4, replacement_picking.id))

        # Link all pickings to this return order
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
        ('discount_sale', 'Discount Sale'),
        ('no_complaints_with_return', 'No Complaints With Return'),
        ('no_complaints_with_dump', 'No Complaints With Dump')
    ], string="Inspection Result",default='salable')
    product_id = fields.Many2one('product.product', string="Product")
    # return_reason = fields.Char(string="Return Reason")
    return_reason_id = fields.Many2one('return.reason',string='Return Reason')
    return_qty = fields.Float(string="Return Quantity", required=True, digits='Product Unit of Measure')
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order Reference',
        domain="[('partner_id', '=', parent.partner_id)]"
    )
    invoice_id = fields.Many2one('account.move', string='Invoice Reference')
    return_type = fields.Selection([
        ('return', 'Return'),
        ('replacement', 'Replacement')
    ], string='Return Type', default='return', required=True)




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
            'discount_sale':'is_discount_sale_location',
            'no_complaints_with_dump':'is_no_complaint_with_dump_location'
        }

        if self.inspection_result == 'salable':
            # Lot stock location for the warehouse
            self.location_dest_id = warehouse.lot_stock_id.id
        elif self.inspection_result == 'no_complaints_with_return':
            customer_location = self.env['stock.location'].search([
                ('usage', '=', 'customer'),
            ], limit=1)

            if not customer_location:
                raise UserError(_("Please configure a Customer Location"))

            self.location_dest_id = customer_location.id
        else:
            # Find the corresponding location by boolean field
            boolean_field = result_to_field.get(self.inspection_result)
            if boolean_field:
                location = self.env['stock.location'].search([
                    (boolean_field, '=', True),
                    ('company_id', '=', self.env.company.id),
                    ('location_id', '=', warehouse.view_location_id.id)
                ], limit=1)

                if not location:
                    raise UserError(_(
                        "Please configure a location with '%s' enabled "
                        "under warehouse '%s' for company '%s'."
                    ) % (self.inspection_result, warehouse.name, self.env.company.name))

                self.location_dest_id = location.id

    @api.model
    def _default_location_dest_id(self):
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if warehouse:
            lot_stock = warehouse.lot_stock_id.id
        return lot_stock if lot_stock else False

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """ If product already exists in another line, copy its quantity """
        for line in self:
            if not line.product_id or not line.return_order_id:
                continue

            # find first existing line with same product (excluding current line)
            existing_line = line.return_order_id.line_ids.filtered(
                lambda l: l.product_id == line.product_id and l.id != line.id
            )[:1]

            if existing_line:
                line.quantity = existing_line.quantity if existing_line.quantity else 0
                line.uom_id = existing_line.uom_id if existing_line.uom_id else False
                line.return_reason_id = existing_line.return_reason_id if existing_line.return_reason_id else False
    @api.onchange("return_qty")
    def _onchange_return_qty(self):
        """Ensure total return_qty for a product does not exceed original quantity"""
        for line in self:
            if not line.product_id or not line.return_order_id:
                continue

            # Find the matching reference line (with same product + optional sale/invoice link)
            reference_lines = line.return_order_id.line_ids.filtered(
                lambda l: l.product_id == line.product_id
                          and (not line.sale_order_id or l.sale_order_id == line.sale_order_id)
                          and (not line.invoice_id or l.invoice_id == line.invoice_id)
            )

            reference_line = reference_lines[:1]
            if not reference_line or not reference_line.quantity:
                continue

            allowed_qty = reference_line.quantity

            # Total return qty for this product (all lines in the return order)
            total_return = sum(
                l.return_qty for l in line.return_order_id.line_ids if l.product_id == line.product_id
            )

            if total_return > allowed_qty:
                # rollback only the current line’s return_qty
                line.return_qty = max(0.0, allowed_qty - (total_return - line.return_qty))
                raise ValidationError(_(
                    "Total return quantity for %s cannot exceed %s."
                ) % (line.product_id.display_name, allowed_qty))

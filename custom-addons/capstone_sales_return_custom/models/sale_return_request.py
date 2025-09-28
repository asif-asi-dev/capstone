from odoo import models, fields, api, Command,_
import json
import logging
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleReturnRequest(models.Model):
    _name = 'sale.return.request'
    _description = 'Sales Return Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        required=True,
        readonly=True,
        default=lambda self: _('New')
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True
    )

    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch',
        domain="[('product_id', '=', product_id)]"
    )

    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('processing', 'Under Inspection'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    # Related fields for warehouse processing
    return_order_id = fields.Many2one(
        'sales.return.order',
        string='Return Order',
        readonly=True
    )
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        readonly=True,
        compute='_compute_source_location',
    )

    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=True,
        readonly=True,
        compute='_compute_destination_location',    )
    return_request_picking_id = fields.Many2one('stock.picking', string='Return Request Picking')
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        readonly=True,
        default=lambda self: self.env.ref(
            'capstone_sales_return_custom.picking_type_sales_return', raise_if_not_found=False
        )
    )
    line_ids = fields.One2many(
        'sale.return.request.line',
        'request_id',
        string="Return Lines"
    )

    @api.depends('picking_type_id')
    def _compute_destination_location(self):
        for rec in self:
            if rec.picking_type_id and rec.picking_type_id.default_location_dest_id:
                rec.destination_location_id = rec.picking_type_id.default_location_dest_id
            else:
                raise ValidationError(_('NO default destination location is set for the picking type Sales Return Transfer'))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.name == _('New'):
                record.name = self.env['ir.sequence'].next_by_code('sale.return.request') or _('New')

        return records


    def action_submit_return_request(self):
        import logging
        _logger = logging.getLogger(__name__)

        StockPicking = self.env['stock.picking']

        for rec in self:
            if rec.state != 'draft':
                continue

            move_vals = []
            for line in rec.line_ids:
                # Base move line values
                move_line_vals = {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.uom_id.id,
                    'quantity': line.return_qty,   # ✅ correct field for move_line_ids
                    'location_id': rec.source_location_id.id,
                    'location_dest_id': rec.destination_location_id.id,
                }
                if line.product_id and line.product_id.tracking != 'none' and not line.lot_id:
                    raise ValidationError(
                        'Lot/Serial Number must be specified for tracked products: %s' % line.product_id.display_name
                    )

                # Add lot if tracked
                if line.product_id.tracking != 'none' and line.lot_id:
                    move_line_vals['lot_id'] = line.lot_id.id

                # Stock move values
                move_vals.append((0, 0, {
                    'name': '/' + (line.product_id.display_name or ''),
                    'location_id': rec.source_location_id.id,
                    'location_dest_id': rec.destination_location_id.id,
                    'product_id': line.product_id.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.return_qty,
                    'move_line_ids': [(0, 0, move_line_vals)],
                }))

            if not move_vals:
                raise ValidationError(_("No return lines found for this request."))

            # Create picking once per request ✅
            return_picking_request = StockPicking.create({
                'partner_id': rec.partner_id.id,
                'picking_type_id': rec.picking_type_id.id,
                'location_id': rec.source_location_id.id,
                'location_dest_id': rec.destination_location_id.id,
                'origin': rec.name,
                'move_ids_without_package': move_vals,
            })

            # Link picking to request
            rec.return_request_picking_id = return_picking_request.id

            try:
                return_picking_request.action_confirm()
                return_picking_request.action_assign()

                return_picking_request.with_context(
                    skip_immediate=True,
                    skip_expired=True
                ).button_validate()

                rec.state = 'submitted'
                _logger.info(f"Successfully validated picking {return_picking_request.name}")

            except Exception as e:
                _logger.exception("Error validating return picking: %s", e)
                rec.state = 'draft'
                continue
            rec._create_and_link_sales_return_order()
            rec.state = 'submitted'




    def _create_and_link_sales_return_order(self):
        """Create Sales Return Order from the given picking and link it to the record."""
        SalesReturnOrder = self.env['sales.return.order']
        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id if line.product_id else False,
                'quantity': line.return_qty,
                'lot_id': line.lot_id.id if line.product_id.tracking != 'none' and line.lot_id else False,
                'uom_id': line.uom_id.id if line.uom_id else False,
                'return_reason': line.notes if line.notes else False,
            }))
        sales_return_order = SalesReturnOrder.create({
            'line_ids': order_lines,
            'picking_id': self.return_request_picking_id.id,
            'partner_id': self.partner_id.id,
            'location_id': self.destination_location_id.id,
            'return_request_id': self.id,
        })

        self.return_order_id = sales_return_order.id

    def action_view_return_request_picking(self):
        self.ensure_one()
        return {
            'name': _('Return RequestTransfer'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.return_request_picking_id.id,
            'context': {'create': False, 'edit': False}
        }

    def action_view_return_order(self):
        self.ensure_one()
        return {
            'name': _('Return Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sales.return.order',
            'res_id': self.return_order_id.id,
            'context': {'create': False, 'edit': False}
        }


    @api.depends('partner_id')
    def _compute_source_location(self):
        for record in self:
            record.source_location_id = (
                record.partner_id.property_stock_customer.id
                if record.partner_id and record.partner_id.property_stock_customer
                else False
            )







class SaleReturnRequestLine(models.Model):
    _name = 'sale.return.request.line'
    _description = 'Sales Return Request Line'

    request_id = fields.Many2one(
        'sale.return.request',
        string='Return Request',
        required=True,
        ondelete='cascade'
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order Reference',
        domain="[('partner_id', '=', parent.partner_id)]"
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('type', '=', 'product')]"
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch',
        domain="[('product_id', '=', product_id)]"
    )

    product_uom_qty = fields.Float(
        string='Original Quantity',
        readonly=True
    )
    return_qty = fields.Float(
        string='Return Quantity',
        required=True,
        default=1.0
    )
    invoice_id = fields.Many2one('account.move', string='Invoice Reference')
    invoice_ids_domain = fields.Char(compute='_compute_invoice_domain')

    notes = fields.Char(string='Notes')

    @api.depends('request_id.partner_id', 'product_id', 'lot_id')
    def _compute_invoice_domain(self):
        for record in self:
            domain = [
                ('partner_id', '=', record.request_id.partner_id.id if record.request_id.partner_id else False),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted')
            ]

            if record.product_id:
                domain.append(('invoice_line_ids.product_id', '=', record.product_id.id))

            # if record.lot_id:
            #     domain.append(('invoice_line_ids.lot_ids', '=', record.lot_id.id))

            record.invoice_ids_domain = json.dumps(domain)

    @api.onchange('invoice_id')
    def _onchange_invoice_id_combined(self):
        self.product_uom_qty = 0.0
        self.sale_order_id = False
        if self.invoice_id and self.invoice_id.invoice_origin:
            self._cr.execute("""
                SELECT id FROM sale_order
                WHERE name = %s AND partner_id = %s
                LIMIT 1
            """, (self.invoice_id.invoice_origin, self.request_id.partner_id.id))
            result = self._cr.fetchone()
            self.sale_order_id = result[0] if result else False
        else:
            self.sale_order_id = False

        if self.invoice_id and self.product_id:
            matching_line = self.invoice_id.invoice_line_ids.filtered(
                lambda l: l.product_id.id == self.product_id.id
            )
            if matching_line:
                self.product_uom_qty = matching_line[0].quantity
            else:
                self.product_uom_qty = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id



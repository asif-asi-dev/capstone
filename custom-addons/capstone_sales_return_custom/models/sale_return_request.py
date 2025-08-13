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

    # Invoice or Sale Order reference fields
    invoice_id = fields.Many2one('account.move', string='Invoice Reference')
    invoice_ids_domain = fields.Char(compute='_compute_invoice_domain')
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

    reason_id = fields.Many2one(
        'return.reason',
        string='Return Reason'
    )

    notes = fields.Text(string='Notes')


    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order Reference',
        domain="[('partner_id', '=', partner_id)]"
    )
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
        default=lambda self: self.env.ref('capstone_sales_return_custom.location_virtual_sales_return').id
    )
    return_request_picking_id = fields.Many2one('stock.picking', string='Return Request Picking')


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.name == _('New'):
                record.name = self.env['ir.sequence'].next_by_code('sale.return.request') or _('New')

        return records

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

    def action_submit_return_request(self):
        import logging
        _logger = logging.getLogger(__name__)

        StockPicking = self.env['stock.picking']

        for rec in self:
            if rec.state != 'draft':
                continue
            picking_type = self.env.ref('capstone_sales_return_custom.picking_type_sales_return')
            if not rec.destination_location_id.warehouse_id or not rec.destination_location_id.location_id:
                raise ValidationError(_('The destination location must be assigned to a warehouse and have a parent location.'))


            if rec.product_id.tracking != 'none' and rec.lot_id:
                move_line_vals = {
                    'product_id': rec.product_id.id,
                    'product_uom_id': rec.uom_id.id,
                    'quantity': rec.return_qty,  # ✅ CORRECT FIELD
                    'location_id': rec.source_location_id.id,
                    'location_dest_id': rec.destination_location_id.id,
                    'lot_id': rec.lot_id.id,
                }
            else:
                move_line_vals = {
                    'product_id': rec.product_id.id,
                    'product_uom_id': rec.uom_id.id,
                    'quantity': rec.return_qty,  # ✅ CORRECT FIELD
                    'location_id': rec.source_location_id.id,
                    'location_dest_id': rec.destination_location_id.id,
                }

            # Create everything in one operation ✅
            return_picking_request = StockPicking.create({
                'partner_id': rec.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': rec.source_location_id.id,
                'location_dest_id': rec.destination_location_id.id,
                'origin': rec.name,
                'move_ids_without_package': [(0, 0, {
                    'name': '/' + rec.product_id.name,
                    'location_id': rec.source_location_id.id,
                    'location_dest_id': rec.destination_location_id.id,
                    'product_id': rec.product_id.id,
                    'product_uom': rec.uom_id.id,
                    'product_uom_qty': rec.product_uom_qty,
                    'move_line_ids': [(0, 0, move_line_vals)],  # ✅ DIRECT CREATION
                })],
            })

            try:
                return_picking_request.action_confirm()
                return_picking_request.action_assign()

                return_picking_request.with_context(
                    skip_immediate=True,
                    skip_expired=True
                ).button_validate()

                _logger.info(f"Successfully validated picking {return_picking_request.name}")

            except Exception as e:
                _logger.exception("Error validating return picking: %s", e)
                rec.state = 'draft'
                continue

            rec.return_request_picking_id = return_picking_request.id
            rec._create_and_link_sales_return_order()
            rec.state = 'submitted'




    def _create_and_link_sales_return_order(self):
        """Create Sales Return Order from the given picking and link it to the record."""
        SalesReturnOrder = self.env['sales.return.order']
        order_lines = []
        order_lines.append((0, 0, {
            'product_id': self.product_id.id,
            'quantity': self.return_qty,
            'lot_id': self.lot_id.id,
            'uom_id': self.uom_id.id,
        }))

        sales_return_order = SalesReturnOrder.create({
            'line_ids': order_lines,
            'picking_id': self.return_request_picking_id.id,
            'partner_id': self.partner_id.id,
            'location_id': self.destination_location_id.id,
            'product_id': self.product_id.id,
            'return_request_id': self.id,
            'quantity': self.return_qty,
            'reason_id': self.reason_id.id,
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

    @api.onchange('invoice_id')
    def _onchange_invoice_id_combined(self):
        if self.invoice_id and self.invoice_id.invoice_origin:
            self._cr.execute("""
                SELECT id FROM sale_order
                WHERE name = %s AND partner_id = %s
                LIMIT 1
            """, (self.invoice_id.invoice_origin, self.partner_id.id))
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




    @api.depends('partner_id', 'product_id', 'lot_id')
    def _compute_invoice_domain(self):
        for record in self:
            domain = [
                ('partner_id', '=', record.partner_id.id if record.partner_id else False),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted')
            ]

            if record.product_id:
                domain.append(('invoice_line_ids.product_id', '=', record.product_id.id))

            # if record.lot_id:
            #     domain.append(('invoice_line_ids.lot_ids', '=', record.lot_id.id))

            record.invoice_ids_domain = json.dumps(domain)



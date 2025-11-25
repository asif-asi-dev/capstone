from odoo import models, fields, api, Command,_
import json
import logging
from odoo.exceptions import ValidationError,UserError

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
        ('waiting_for_pickup', 'Waiting For Pickup'),
        ('submitted', 'Collected And Submitted For Approval'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
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
    date_requested = fields.Date(string='Date Requested')
    requested_by = fields.Many2one('res.users',string='Requested By')
    date_approved = fields.Date(string='Date Approved')
    return_available_qty = fields.Float(string='Return Available Quantity')
    collected_by = fields.Many2one('res.users', string='Collected By')
    collected_date = fields.Date(string='Collected Date')
    credit_note_id = fields.Many2one('account.move', string='Credit Note')

    def action_view_credit_note(self):
        self.ensure_one()
        if not self.credit_note_id:
            raise UserError("No credit note found.")

        return {
            'name': 'Credit Note',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.credit_note_id.id,
            'target': 'current',
        }

    def action_create_credit_note(self):
        """ Public button method """
        self.ensure_one()
        credit_note = self._create_custom_credit_note()

        # Return action to open draft credit note
        return {
            'name': 'Credit Note',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': credit_note.id,
            'target': 'current',
        }

    def _create_custom_credit_note(self):
        """ Create draft credit note using return request lines """
        self.ensure_one()

        if not self.line_ids:
            raise UserError("No return request lines found.")

        partner = self.partner_id
        company = self.env.company
        currency = company.currency_id

        credit_note_vals = {
            'move_type': 'out_refund',  # credit note
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'company_id': company.id,
            'currency_id': currency.id,
            'invoice_origin': self.name,
            'invoice_line_ids': [],
        }

        line_vals_list = []

        for line in self.line_ids:
            if line.return_qty <= 0:
                continue

            line_vals = {
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'quantity': line.return_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
            }

            line_vals_list.append((0, 0, line_vals))

        if not line_vals_list:
            raise UserError("There are no valid return quantities to create a credit note.")

        credit_note_vals['invoice_line_ids'] = line_vals_list

        credit_note = self.env['account.move'].create(credit_note_vals)
        self.credit_note_id = credit_note.id

        return credit_note



    def action_collect_and_submit_for_approval(self):
        for rec in self:
            if rec.state == 'waiting_for_pickup':
                rec.collected_by = self.env.user.id
                rec.collected_date = fields.Date.today()
                rec.state = 'submitted'
    def action_submit_for_pickup(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'waiting_for_pickup'
                rec.date_requested = fields.Date.today()
                rec.requested_by = self.env.user.id
    def action_cancel(self):
        for rec in self:
            if rec.state == 'submitted':
                rec.state = 'cancelled'

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
            if rec.state != 'submitted':
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
                _logger.info(f"Successfully validated picking {return_picking_request.name}")

            except Exception as e:
                _logger.exception("Error validating return picking: %s", e)
                rec.state = 'draft'
                continue
            rec._create_and_link_sales_return_order()
            rec.state = 'done'
            rec.date_approved = fields.Date.today()




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
                'return_reason_id': line.return_reason_id.id if line.return_reason_id else False,
                'sale_order_id':line.sale_order_id.id if line.sale_order_id else False,
                'invoice_id':line.invoice_id.id if line.invoice_id else False,
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
            'context': {'create': False, 'edit': True}
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
    return_reason_id = fields.Many2one('return.reason',string='Return Reason')
    return_available_qty = fields.Float(string='Return Available Quantity')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    total_amount = fields.Float(
        string='Total Amount',
        digits='Product Price',
        compute='_compute_total_amount',
        store=True
    )
    price_unit = fields.Float(string='Price Unit', digits='Product Price')

    @api.depends('price_unit', 'return_qty', 'tax_ids', 'invoice_id')
    def _compute_total_amount(self):
        for line in self:
            price_unit = line.price_unit or 0.0
            qty = line.return_qty or 0.0
            taxes = line.tax_ids

            # Priority: invoice currency → environment company currency
            currency = (
                line.invoice_id.currency_id
                if line.invoice_id
                else self.env.company.currency_id
            )

            if taxes:
                tax_data = taxes.compute_all(
                    price_unit,
                    currency=currency,
                    quantity=qty
                )
                line.total_amount = tax_data['total_included']
            else:
                line.total_amount = price_unit * qty

    @api.onchange('product_id', 'invoice_id')
    def _onchange_product_or_invoice(self):

        for line in self:
            price_unit = 0.0
            tax_ids = self.env['account.tax']

            # --------------------------------------
            # 1) Fetch from invoice line if invoice available
            # --------------------------------------
            if line.invoice_id and line.product_id:
                inv_line = line.invoice_id.invoice_line_ids.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if inv_line:
                    # If multiple lines, take the first matching
                    inv_line = inv_line[0]
                    line.price_unit = inv_line.price_unit
                    line.tax_ids = inv_line.tax_ids
                    continue   # ✔ done

            # --------------------------------------
            # 2) Else: fetch from product master
            # --------------------------------------
            if line.product_id:
                line.price_unit = line.product_id.list_price
                line.tax_ids = line.product_id.taxes_id

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
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if self.sale_order_id and self.product_id:
            self.return_available_qty = self.sale_order_id.get_available_sale_qty(self.product_id.id,self.product_id.product_tmpl_id.id)
            if self.return_available_qty < 1:
                raise ValidationError(_("No quantity available for return in the corresponding sale order."))







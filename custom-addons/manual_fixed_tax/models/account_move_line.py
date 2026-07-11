from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    has_manual_gst = fields.Boolean(
        compute='_compute_has_manual_gst',
        store=True,
        help="Technical field: True if this line carries a Manual Fixed Tax. "
             "Used to lock Quantity to 1 in the view."
    )

    @api.depends('tax_ids', 'tax_ids.is_manual_fixed_tax')
    def _compute_has_manual_gst(self):
        for line in self:
            line.has_manual_gst = any(
                tax.amount_type == 'fixed' and tax.is_manual_fixed_tax
                for tax in line.tax_ids
            )

    @api.onchange('tax_ids')
    def _onchange_manual_gst_force_qty(self):
        for line in self:
            if line.has_manual_gst and line.quantity != 1:
                line.quantity = 1

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        super()._compute_totals()
        for line in self:
            if line.display_type == 'product' and line.has_manual_gst:
                # The line's own amount is just a carrier for the manual tax
                # figure (visible in Price Unit for readability) - it must
                # NOT also count as a taxable base / untaxed amount, or the
                # tax gets posted twice: once as 'tax', once as this line's
                # own product/expense account balance.
                tax_amount = line.price_total - line.price_subtotal
                line.price_subtotal = 0.0
                line.price_total = tax_amount

    def _convert_to_tax_base_line_dict(self):
        res = super()._convert_to_tax_base_line_dict()
        if self.has_manual_gst:
            res['extra_context'] = dict(res.get('extra_context') or {}, manual_gst_carrier=True)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._enforce_manual_gst_qty()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'tax_ids' in vals or 'quantity' in vals:
            self._enforce_manual_gst_qty()
        return res

    def _enforce_manual_gst_qty(self):
        """Server-side safety net (covers imports, API calls, and any path
        that bypasses the onchange), so Quantity can never drift away from 1
        on a line carrying a Manual Fixed Tax."""
        for line in self:
            if line.has_manual_gst and line.quantity != 1:
                line.quantity = 1

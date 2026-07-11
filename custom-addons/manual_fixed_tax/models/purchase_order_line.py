from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    has_manual_gst = fields.Boolean(
        compute='_compute_has_manual_gst',
        store=True,
        help="Technical field: True if this line carries a Manual Fixed Tax. "
             "Used to lock Quantity to 1 in the view."
    )

    @api.depends('taxes_id', 'taxes_id.is_manual_fixed_tax')
    def _compute_has_manual_gst(self):
        for line in self:
            line.has_manual_gst = any(
                tax.amount_type == 'fixed' and tax.is_manual_fixed_tax
                for tax in line.taxes_id
            )

    def _convert_to_tax_base_line_dict(self):
        res = super()._convert_to_tax_base_line_dict()
        if self.has_manual_gst:
            res['extra_context'] = dict(res.get('extra_context') or {}, manual_gst_carrier=True)
        return res

    @api.onchange('taxes_id')
    def _onchange_manual_gst_force_qty(self):
        for line in self:
            if line.has_manual_gst and line.product_qty != 1:
                line.product_qty = 1

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._enforce_manual_gst_qty()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'taxes_id' in vals or 'product_qty' in vals:
            self._enforce_manual_gst_qty()
        return res

    def _enforce_manual_gst_qty(self):
        for line in self:
            if line.has_manual_gst and line.product_qty != 1:
                line.product_qty = 1

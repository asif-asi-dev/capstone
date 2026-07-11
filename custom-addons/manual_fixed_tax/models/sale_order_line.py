from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    has_manual_gst = fields.Boolean(
        compute='_compute_has_manual_gst',
        store=True,
        help="Technical field: True if this line carries a Manual Fixed Tax. "
             "Used to lock Quantity to 1 in the view."
    )

    @api.depends('tax_id', 'tax_id.is_manual_fixed_tax')
    def _compute_has_manual_gst(self):
        for line in self:
            line.has_manual_gst = any(
                tax.amount_type == 'fixed' and tax.is_manual_fixed_tax
                for tax in line.tax_id
            )

    def _convert_to_tax_base_line_dict(self, **kwargs):
        if self.has_manual_gst:
            kwargs['extra_context'] = dict(kwargs.get('extra_context') or {}, manual_gst_carrier=True)
        return super()._convert_to_tax_base_line_dict(**kwargs)

    @api.onchange('tax_id')
    def _onchange_manual_gst_force_qty(self):
        for line in self:
            if line.has_manual_gst and line.product_uom_qty != 1:
                line.product_uom_qty = 1

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._enforce_manual_gst_qty()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'tax_id' in vals or 'product_uom_qty' in vals:
            self._enforce_manual_gst_qty()
        return res

    def _enforce_manual_gst_qty(self):
        for line in self:
            if line.has_manual_gst and line.product_uom_qty != 1:
                line.product_uom_qty = 1

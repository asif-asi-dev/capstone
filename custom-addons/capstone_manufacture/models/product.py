from odoo import models
from odoo.tools import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        result = super()._compute_bom_price(bom, boms_to_recompute, byproduct_bom)
        if not bom:
            return result
        quantity = bom.product_uom_id._compute_quantity(bom.product_qty, bom.product_tmpl_id.uom_id)
        extra = sum(op._capstone_estimated_cost(quantity) for op in bom.operation_ids
                    if not op._skip_operation_line(self))
        if byproduct_bom:
            lines = bom.byproduct_ids.filtered(lambda line: line.product_id == self and line.cost_share != 0)
            byproduct_qty = sum(line.product_uom_id._compute_quantity(line.product_qty, self.uom_id, round=False)
                               for line in lines)
            return result + (extra * sum(lines.mapped('cost_share')) / 100 / byproduct_qty if byproduct_qty else 0)
        share = sum(bom.byproduct_ids.mapped('cost_share'))
        extra *= float_round(1 - share / 100, precision_rounding=0.0001)
        return result + bom.product_uom_id._compute_price(extra / bom.product_qty, self.uom_id)

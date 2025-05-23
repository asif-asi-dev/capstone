# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import float_round
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    bom_byproduct_cost = fields.Float(
        string="BoM Byproduct Cost",
        compute='_compute_bom_byproduct_cost',
        store=True,
        help="Sum of the costs of all byproducts in the BoM."
    )

    @api.depends('bom_ids.byproduct_ids', 'bom_ids.byproduct_ids.product_id.standard_price')
    def _compute_bom_byproduct_cost(self):
        for product in self:
            total_cost = 0.0
            # Get all active BoMs for the product
            boms = self.env['mrp.bom'].search([('product_tmpl_id', '=', product.id)])
            for bom in boms:
                for byproduct in bom.byproduct_ids:
                    # Convert byproduct quantity to the same UoM as the product's cost UoM
                    byproduct_qty = byproduct.product_uom_id._compute_quantity(
                        byproduct.product_qty, byproduct.product_id.uom_id
                    )
                    # Calculate the cost for the byproduct
                    total_cost += byproduct.product_id.standard_price * byproduct_qty
            product.bom_byproduct_cost = total_cost

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        self.ensure_one()
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []

        total = 0
        # Calculate the total cost of operations
        for opt in bom.operation_ids:
            if opt._skip_operation_line(self):
                continue

            duration_expected = (
                    opt.workcenter_id._get_expected_duration(self) +
                    opt.time_cycle * 100 / opt.workcenter_id.time_efficiency)
            total += (duration_expected / 60) * opt._total_cost_per_hour()

        # Calculate the total cost of components
        for line in bom.bom_line_ids:
            if line._skip_bom_line(self):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(line.child_bom_id,
                                                                 boms_to_recompute=boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.product_uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price,
                                                               line.product_uom_id) * line.product_qty

        # Handle byproduct logic
        if byproduct_bom:
            byproduct_lines = bom.byproduct_ids.filtered(lambda b: b.product_id == self and b.cost_share != 0)
            product_uom_qty = 0
            for line in byproduct_lines:
                product_uom_qty += line.product_uom_id._compute_quantity(line.product_qty, self.uom_id, round=False)
            byproduct_cost_share = sum(byproduct_lines.mapped('cost_share'))
            if byproduct_cost_share and product_uom_qty:
                return total * byproduct_cost_share / 100 / product_uom_qty
        else:
            byproduct_cost_share = sum(bom.byproduct_ids.mapped('cost_share'))
            if byproduct_cost_share:
                total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)

        # Subtract the byproduct cost from the total BoM cost
        bom_byproduct_cost = self.product_tmpl_id.bom_byproduct_cost
        total -= bom_byproduct_cost

        # Return the final cost after subtracting byproduct costs
        return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)
from odoo import api, models


class BomOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    @api.model
    def _get_operation_line(self, product, bom, qty, level, index):
        lines = super()._get_operation_line(product, bom, qty, level, index)
        quantity = bom.product_uom_id._compute_quantity(qty, bom.product_tmpl_id.uom_id)
        for line in lines:
            operation = line['operation']
            if operation.capstone_cost_method != 'hourly':
                currency = (bom.company_id or self.env.company).currency_id
                line['bom_cost'] = currency.round(operation._capstone_estimated_cost(quantity))
        return lines

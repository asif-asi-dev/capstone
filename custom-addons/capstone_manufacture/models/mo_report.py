from odoo import _, models


class ManufacturingOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _capstone_update_cost_lines(self, data, production, finished=False):
        for line, wo in zip(data['details'], production.workorder_ids):
            if wo.capstone_cost_method == 'hourly':
                continue
            estimated = wo._compute_expected_operation_cost()
            actual = wo._compute_current_operation_cost()
            known = finished or wo.capstone_charge_confirmed or (
                wo.capstone_quantity_basis == 'good' and wo._capstone_good_quantity() > 0)
            cost = actual if known else estimated
            line.update({
                'mo_cost': actual if finished else estimated,
                'real_cost': cost,
                'unit_cost': wo.capstone_cost_rate,
                'quantity': cost / wo.capstone_cost_rate if wo.capstone_cost_rate else 0,
                'uom_name': _('Batch') if wo.capstone_cost_method == 'batch' else wo.product_id.uom_id.name,
            })
        data['summary']['mo_cost'] = sum(line['mo_cost'] for line in data['details'])
        data['summary']['real_cost'] = sum(line['real_cost'] for line in data['details'])
        return data

    def _get_operations_data(self, production, level=0, current_index=False):
        data = super()._get_operations_data(production, level, current_index)
        if production.state == 'done':
            return data
        return self._capstone_update_cost_lines(data, production)

    def _get_finished_operation_data(self, production, level=0, current_index=False):
        data = super()._get_finished_operation_data(production, level, current_index)
        return self._capstone_update_cost_lines(data, production, finished=True)

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from .mrp_routing import COST_METHODS, QUANTITY_BASES


RATE_FIELDS = {'capstone_cost_method', 'capstone_cost_rate', 'capstone_quantity_basis', 'capstone_charge_batch'}
CHARGE_FIELDS = RATE_FIELDS | {'capstone_charge_quantity', 'capstone_charge_confirmed'}


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    capstone_cost_method = fields.Selection(COST_METHODS, default='hourly', required=True, string='Costing Method')
    capstone_cost_rate = fields.Monetary(string='Piece / Batch Rate', currency_field='capstone_currency_id')
    capstone_currency_id = fields.Many2one(related='company_id.currency_id')
    capstone_quantity_basis = fields.Selection(QUANTITY_BASES, default='processed', required=True, string='Charge Quantity Basis')
    capstone_charge_uom_id = fields.Many2one(related='product_id.uom_id', string='Charge Unit')
    capstone_charge_quantity = fields.Float(string='Processed Chargeable Quantity', digits='Product Unit of Measure', copy=False,
        help='Actual pieces processed, including paid rejects, in the product inventory unit. Confirm before finishing.')
    capstone_charge_batch = fields.Boolean(string='Apply Batch Charge', default=True,
        help='One fixed fee for this work order. A manager can waive the fee for a continuation batch.')
    capstone_charge_confirmed = fields.Boolean(string='Charge Confirmed', copy=False,
        help='Confirm the processed quantity or the batch-charge decision before completing this work order.')
    capstone_processing_cost = fields.Monetary(string='Actual Processing Cost', compute='_compute_capstone_processing_cost',
        currency_field='capstone_currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if RATE_FIELDS.intersection(vals) and not self.env.su and not self.env.user.has_group('mrp.group_mrp_manager'):
                raise AccessError(_('Only Manufacturing Administrators can configure processing rates.'))
            operation = self.env['mrp.routing.workcenter'].browse(vals.get('operation_id'))
            if operation:
                for name in ('capstone_cost_method', 'capstone_cost_rate', 'capstone_quantity_basis'):
                    vals.setdefault(name, operation[name])
            prepared.append(vals)
        return super().create(prepared)

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('capstone_charge_quantity', 0)
        default.setdefault('capstone_charge_confirmed', False)
        # Splits/backorders must not inherit the original batch's fixed fee.
        default.setdefault('capstone_charge_batch', False)
        return super().copy_data(default)

    @api.constrains('capstone_cost_rate', 'capstone_charge_quantity')
    def _check_capstone_charge(self):
        if any(wo.capstone_cost_rate < 0 or wo.capstone_charge_quantity < 0 for wo in self):
            raise ValidationError(_('Processing rates and chargeable quantities cannot be negative.'))

    def _capstone_good_quantity(self):
        self.ensure_one()
        mo = self.production_id
        quantity = mo.qty_produced if mo.state == 'done' else (mo.qty_producing or self.qty_produced)
        return mo.product_uom_id._compute_quantity(quantity, self.product_id.uom_id)

    def _capstone_custom_cost(self, estimated=False):
        self.ensure_one()
        if self.state == 'cancel':
            return 0.0
        if self.capstone_cost_method == 'batch':
            return self.capstone_cost_rate if self.capstone_charge_batch else 0.0
        if estimated:
            quantity = self.production_id.product_uom_id._compute_quantity(
                self.qty_production, self.product_id.uom_id)
        elif self.capstone_quantity_basis == 'good':
            quantity = self._capstone_good_quantity()
        else:
            quantity = self.capstone_charge_quantity
        return quantity * self.capstone_cost_rate

    @api.depends('capstone_cost_method', 'capstone_cost_rate', 'capstone_quantity_basis',
                 'capstone_charge_quantity', 'capstone_charge_batch', 'state',
                 'production_id.qty_produced', 'production_id.qty_producing',
                 'production_id.state', 'qty_produced', 'time_ids.date_start', 'time_ids.date_end')
    def _compute_capstone_processing_cost(self):
        for wo in self:
            wo.capstone_processing_cost = wo._compute_current_operation_cost()

    def _compute_expected_operation_cost(self):
        self.ensure_one()
        if self.capstone_cost_method != 'hourly':
            return self._capstone_custom_cost(estimated=True)
        return super()._compute_expected_operation_cost()

    def _compute_current_operation_cost(self):
        self.ensure_one()
        if self.capstone_cost_method != 'hourly':
            return self._capstone_custom_cost()
        return super()._compute_current_operation_cost()

    def _cal_cost(self):
        hourly = self.filtered(lambda wo: wo.capstone_cost_method == 'hourly')
        return super(MrpWorkorder, hourly)._cal_cost() + sum(
            wo._capstone_custom_cost() for wo in self - hourly)

    def _capstone_check_confirmation(self):
        for wo in self.filtered(lambda w: w.state != 'cancel'):
            needs_confirmation = wo.capstone_cost_method == 'batch' or (
                wo.capstone_cost_method == 'piece' and wo.capstone_quantity_basis == 'processed')
            if needs_confirmation and not wo.capstone_charge_confirmed:
                raise ValidationError(_('Confirm the processing charge on work order %s before finishing.', wo.display_name))

    def button_finish(self):
        self._capstone_check_confirmation()
        result = super().button_finish()
        self._create_or_update_analytic_entry()
        return result

    def _create_or_update_analytic_entry(self):
        hourly = self.filtered(lambda wo: wo.capstone_cost_method == 'hourly')
        super(MrpWorkorder, hourly)._create_or_update_analytic_entry()
        custom = (self - hourly).filtered(lambda wo: wo.id and (
            wo.production_id.analytic_distribution or wo.workcenter_id.analytic_distribution
            or wo.wc_analytic_account_line_ids or wo.mo_analytic_account_line_ids))
        for wo in custom:
            value = -wo._capstone_custom_cost()
            # Analytic quantities remain working hours; monetary amounts use the
            # selected charge. This preserves the standard analytic hour UoM.
            hours = wo.duration / 60.0
            for owner, relation in ((wo.production_id, 'mo_analytic_account_line_ids'),
                                    (wo.workcenter_id, 'wc_analytic_account_line_ids')):
                vals = self.env['account.analytic.account']._perform_analytic_distribution(
                    owner.analytic_distribution, value, hours, wo[relation], wo)
                if vals:
                    wo[relation] += self.env['account.analytic.line'].sudo().create(vals)

    def write(self, values):
        # Check before the base implementation changes calendars or related MOs.
        self.check_access_rights('write')
        self.check_access_rule('write')
        if RATE_FIELDS.intersection(values) and not self.env.su and not self.env.user.has_group('mrp.group_mrp_manager'):
            raise AccessError(_('Only Manufacturing Administrators can configure processing rates.'))
        if CHARGE_FIELDS.intersection(values) and any(wo.production_id.state in ('done', 'cancel') for wo in self):
            raise ValidationError(_('Processing charges cannot change after the manufacturing order is closed.'))
        values = dict(values)
        if (RATE_FIELDS | {'capstone_charge_quantity'}).intersection(values) and 'capstone_charge_confirmed' not in values:
            values['capstone_charge_confirmed'] = False
        if values.get('workcenter_id'):
            self.env['mrp.workcenter'].browse(values['workcenter_id']).check_access_rule('read')
        result = super().write(values)
        if CHARGE_FIELDS.intersection(values):
            self._create_or_update_analytic_entry()
        return result

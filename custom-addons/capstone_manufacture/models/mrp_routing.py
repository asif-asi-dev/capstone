from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


COST_METHODS = [('hourly', 'Hourly'), ('piece', 'Per Piece'), ('batch', 'Fixed per Batch')]
QUANTITY_BASES = [('processed', 'Processed Pieces (Including Rejects)'), ('good', 'Good Output Only')]


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    capstone_cost_method = fields.Selection(COST_METHODS, default='hourly', required=True, string='Costing Method')
    capstone_cost_rate = fields.Monetary(string='Piece / Batch Rate', currency_field='capstone_currency_id')
    capstone_currency_id = fields.Many2one(related='company_id.currency_id')
    capstone_quantity_basis = fields.Selection(QUANTITY_BASES, default='processed', required=True, string='Charge Quantity Basis')

    @api.constrains('capstone_cost_rate')
    def _check_capstone_rate(self):
        if any(op.capstone_cost_rate < 0 for op in self):
            raise ValidationError(_('Processing rates cannot be negative.'))

    def _total_cost_per_hour(self):
        self.ensure_one()
        # Custom charges replace, rather than supplement, the hourly BoM charge.
        if self.capstone_cost_method != 'hourly':
            return 0.0
        return super()._total_cost_per_hour()

    def _capstone_estimated_cost(self, quantity):
        """Quantity is in the finished product's inventory UoM."""
        self.ensure_one()
        if self.capstone_cost_method == 'piece':
            return quantity * self.capstone_cost_rate
        if self.capstone_cost_method == 'batch':
            return self.capstone_cost_rate if quantity > 0 else 0.0
        return 0.0

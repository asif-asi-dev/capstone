from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    assignment_id = fields.Many2one(
        'complaint.assignment',
        string='Complaint Assignment',
        ondelete='set null'
    )

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        # Trigger the assignment state check after the picking is validated
        if self.assignment_id:
            self.assignment_id._compute_all_pickings_validated()

        return res


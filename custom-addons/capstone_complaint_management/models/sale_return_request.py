from odoo import models, fields, api, Command,_


class SaleReturnRequest(models.Model):
    _inherit = 'sale.return.request'

    assignment_id = fields.Many2one(
        'complaint.assignment',
        string='Complaint Assignment',
        ondelete='set null'
    )

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'done':
            for rec in self:
                if rec.assignment_id:
                    rec.assignment_id._check_close_return_assignment()
        return res

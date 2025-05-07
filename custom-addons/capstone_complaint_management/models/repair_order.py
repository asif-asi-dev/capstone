from odoo import models, fields

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    assignment_id = fields.Many2one('complaint.assignment', string='Assignment')

    def action_repair_end(self):
        res = super().action_repair_end()

        for repair in self:
            assignment = repair.assignment_id
            if assignment:
                # Check if all related repair orders are done
                all_done = all(r.state == 'done' for r in assignment.repair_order_ids)
                if all_done:
                    assignment.state = 'done'
                    if assignment.complaint_id:
                        assignment.complaint_id.state = 'resolved'

        return res

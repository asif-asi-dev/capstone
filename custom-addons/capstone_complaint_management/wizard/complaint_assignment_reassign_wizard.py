from odoo import models, fields, _
from odoo.exceptions import UserError


class ComplaintAssignmentReassignWizard(models.TransientModel):
    _name = 'complaint.assignment.reassign.wizard'
    _description = 'Reassign Complaint Assignment'

    assignment_id = fields.Many2one(
        'complaint.assignment',
        string='Assignment',
        required=True,
        readonly=True
    )

    new_technician_id = fields.Many2one(
        'res.users',
        string='New Technician',
        required=True,
        domain=[('share', '=', False)]
    )

    reason = fields.Text(string='Reason for Reassignment')

    def action_reassign(self):
        self.ensure_one()
        assignment = self.assignment_id

        # Safety check (backend validation)
        if assignment.state != 'assigned':
            raise UserError(_('Only assigned complaints can be reassigned.'))

        if assignment.picking_ids or assignment.repair_order_ids or assignment.sale_return_request_ids:
            raise UserError(
                _('Reassignment is not allowed once return, replacement, or service has started.')
            )

        if assignment.technician_id == self.new_technician_id:
            raise UserError(_('Please choose a different technician.'))

        assignment.write({
            'technician_id': self.new_technician_id.id
        })

        assignment.message_post(
            body=_(
                "Assignment reassigned to <b>%s</b>.<br/>Reason: %s"
            ) % (
                self.new_technician_id.name,
                self.reason or _('No reason provided')
            )
        )

        return {'type': 'ir.actions.act_window_close'}

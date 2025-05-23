from odoo import models, fields, api

class ComplaintFeedbackWizard(models.TransientModel):
    _name = 'complaint.feedback.wizard'
    _description = 'Feedback Wizard'

    complaint_id = fields.Many2one('complaint.management', required=True, readonly=True)
    technician_id = fields.Many2one('res.users', string='Technician', readonly=True)
    rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Rating', required=True)
    feedback = fields.Text(string='Feedback', required=True)


    def action_submit_feedback(self):
        self.complaint_id.write({
            'customer_rating': self.rating,
            'feedback': self.feedback,
        })
        self.env['complaint.review.line'].create({
            'complaint_id': self.complaint_id.id,
            'technician_id': self.technician_id.id,
            'rating': self.rating,
            'feedback': self.feedback,
        })
        return {'type': 'ir.actions.act_window_close'}

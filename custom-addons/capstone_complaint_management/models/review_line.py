from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ComplaintReviewLine(models.Model):
    _name = 'complaint.review.line'
    _description = 'Complaint Review Line'

    complaint_id = fields.Many2one('complaint.management')
    technician_id = fields.Many2one('res.users')
    rating = fields.Selection([
        ('1', '1 Star'), ('2', '2 Stars'), ('3', '3 Stars'), ('4', '4 Stars'), ('5', '5 Stars')
    ], string='Rating')
    feedback = fields.Text(string='Feedback')

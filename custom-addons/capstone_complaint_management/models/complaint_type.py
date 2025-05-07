from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ComplaintType(models.Model):
    _name = 'complaint.type'
    _description = 'Complaint Type'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description', required=True)
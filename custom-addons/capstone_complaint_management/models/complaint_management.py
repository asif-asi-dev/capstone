from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ComplaintManagement(models.Model):
    _name = 'complaint.management'
    _description = 'Complaint Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    date = fields.Date(string='Complaint Date', default=fields.Date.context_today)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    complaint_type_ids = fields.Many2many('complaint.type', string='Complaint Types')
    purchased_shop_id = fields.Many2one('res.partner', string='Purchased Shop')
    purchase_date = fields.Date(string='Purchase Date')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting for assignment'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    assignment_ids = fields.One2many('complaint.assignment', 'complaint_id', string='Assignments')
    product_line_ids = fields.One2many('complaint.product.line', 'complaint_id', string='Products')
    description = fields.Text(string='Complaint Description')# New field

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('complaint.management') or 'New'
        return super(ComplaintManagement, self).create(vals)

    @api.constrains('purchase_date', 'date')
    def _check_purchase_date(self):
        for record in self:
            if record.purchase_date and record.date and record.purchase_date > record.date:
                raise ValidationError('Purchase Date cannot be after Complaint Date.')

    def action_submit(self):
        for record in self:
            record.state = 'submitted'


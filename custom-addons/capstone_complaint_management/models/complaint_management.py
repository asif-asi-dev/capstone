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
    image_1 = fields.Binary(string="Photo 1", attachment=True)
    image_2 = fields.Binary(string="Photo 2", attachment=True)
    video_file = fields.Binary(string="Complaint Video", attachment=True)
    video_filename = fields.Char(string="Video Filename")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting for assignment'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    assignment_ids = fields.One2many('complaint.assignment', 'complaint_id', string='Assignments')
    assignment_count = fields.Integer(compute='_compute_assignment_count', string='Assignments')
    product_line_ids = fields.One2many('complaint.product.line', 'complaint_id', string='Products')
    description = fields.Text(string='Complaint Description')
    picking_ids = fields.Many2many('stock.picking', compute='_compute_related_pickings', string="Return Pickings", store=True)
    repair_order_ids = fields.Many2many('repair.order', compute='_compute_related_repairs', string="Repairs", store=True)
    picking_count = fields.Integer(compute='_compute_related_pickings', string="Picking Count")
    repair_count = fields.Integer(compute='_compute_related_repairs', string="Repair Count")
    customer_rating = fields.Selection(
        [('1', '1 Star'), ('2', '2 Stars'), ('3', '3 Stars'), ('4', '4 Stars'), ('5', '5 Stars')],
        string="Customer Rating"
    )
    feedback = fields.Text(string="Customer Feedback")
    review_line_ids = fields.One2many('complaint.review.line', 'complaint_id', string="Reviews")
    technician_id = fields.Many2one(
        'res.users',
        string='Technician',
        compute='_compute_technician_id',
        store=True,
        readonly=True
    )

    @api.depends('assignment_ids.technician_id')
    def _compute_technician_id(self):
        for record in self:
            # Set technician from the first assignment that has a technician
            record.technician_id = (
                record.assignment_ids.filtered(lambda a: a.technician_id)[:1].technician_id
            )


    @api.depends('assignment_ids.picking_ids')
    def _compute_related_pickings(self):
        for record in self:
            record.picking_ids = record.assignment_ids.mapped('picking_ids')
            record.picking_count = len(record.assignment_ids.mapped('picking_ids'))

    @api.depends('assignment_ids.repair_order_ids')
    def _compute_related_repairs(self):
        for record in self:
            record.repair_order_ids = record.assignment_ids.mapped('repair_order_ids')
            record.repair_count = len(record.assignment_ids.mapped('repair_order_ids'))

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for rec in self:
            rec.assignment_count = len(rec.assignment_ids)

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
            if not record.product_line_ids:
                raise ValidationError("Please add at least one product before submitting the complaint.")
            record.state = 'submitted'

    def action_view_assignments(self):
        self.ensure_one()
        return {
            'name': 'Assignments',
            'type': 'ir.actions.act_window',
            'res_model': 'complaint.assignment',
            'view_mode': 'tree,form',
            'domain': [('complaint_id', '=', self.id)],
            'context': {'default_complaint_id': self.id},
        }

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'name': 'Related Pickings',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': {'default_origin': self.name},
        }

    def action_view_repairs(self):
        self.ensure_one()
        return {
            'name': 'Related Repairs',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'repair.order',
            'domain': [('id', 'in', self.repair_order_ids.ids)],
            'context': {'default_origin': self.name},
        }

    def action_open_feedback_wizard(self):
        self.ensure_one()
        return {
            'name': 'Provide Feedback',
            'type': 'ir.actions.act_window',
            'res_model': 'complaint.feedback.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_complaint_id': self.id,
                'default_technician_id': self.technician_id.id
            }
        }





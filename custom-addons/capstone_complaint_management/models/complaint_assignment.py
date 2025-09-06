from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ComplaintAssignment(models.Model):
    _name = 'complaint.assignment'
    _description = 'Complaint Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    complaint_id = fields.Many2one(
        'complaint.management',
        string='Complaint',
        required=True,
        domain="[('state', '=', 'submitted')]",
        ondelete='cascade', tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('res.users', string='Technician', tracking=True)
    start_datetime = fields.Datetime(string='Start Time', related='complaint_id.create_date', tracking=True)
    end_datetime = fields.Datetime(string='End Time', tracking=True)
    warranty_status = fields.Selection([
        ('paid', 'Paid'),
        ('non_paid', 'Non-Paid'),
    ], string='Warranty Status', default="paid")
    resolution_type = fields.Selection([
        ('return', 'Return'),
        ('replacement', 'Replacement'),
        ('service', 'Service'),
    ], string='Resolution Type')
    component_ids = fields.Many2many('product.product', string='Components Used')
    component_type = fields.Selection([
        ('sale', 'Sale'),
        ('free', 'Free'),
    ], string='Component Type')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ], string='Payment Status')

    customer_rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], string='Customer Rating')
    customer_feedback = fields.Text(string='Customer Feedback')
    rated_by_customer = fields.Boolean(string='Rated by Customer', default=False)
    return_location_id = fields.Many2one(
        'stock.location',
        string='Return Location',
        domain=[('usage', 'in', ['internal', 'transit'])]
    )
    picking_ids = fields.One2many(
        'stock.picking', 'assignment_id',
        string='Related Pickings', store=True
    )

    picking_count = fields.Integer(
        string="Picking Count", compute="_compute_picking_count"
    )
    repair_count = fields.Integer(
        string="Service Count", compute="_compute_repair_count"
    )
    repair_order_ids = fields.One2many(
        'repair.order', 'assignment_id', string="Repair Orders", compute="_compute_repair_orders", store=True
    )
    hours_taken = fields.Float(string="Hours Taken", compute='_compute_hours_taken', store=True)

    @api.depends('start_datetime', 'end_datetime')
    def _compute_hours_taken(self):
        for record in self:
            if record.start_datetime and record.end_datetime:
                delta = record.end_datetime - record.start_datetime
                record.hours_taken = round(delta.total_seconds() / 3600, 2)
            else:
                record.hours_taken = 0.0

    def write(self, vals):
        # Automatically set end time when state is changed to 'done'
        for record in self:
            if vals.get('state') == 'done' and not record.end_datetime:
                vals['end_datetime'] = fields.Datetime.now()
        return super(ComplaintAssignment, self).write(vals)

    @api.depends('repair_order_ids')
    def _compute_repair_orders(self):
        for record in self:
            record.repair_order_ids = self.env['repair.order'].search([('assignment_id', '=', record.id)])

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.depends('repair_order_ids')
    def _compute_repair_count(self):
        for rec in self:
            rec.repair_count = len(rec.repair_order_ids)

    def action_view_picking(self):
        self.ensure_one()
        return {
            'name': 'Related Return Pickings',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': {'default_assignment_id': self.id},
        }

    def action_view_repairs(self):
        self.ensure_one()
        return {
            'name': 'Related Repair Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'repair.order',
            'domain': [('id', 'in', self.repair_order_ids.ids)],
            'context': {'default_assignment_id': self.id},
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('complaint.assignment') or 'New'
        return super(ComplaintAssignment, self).create(vals)

    def action_assign(self):
        for record in self:
            record.state = 'assigned'
            if record.complaint_id:
                record.complaint_id.state = 'assigned'

    def action_create_logistics(self):
        for record in self:
            if record.resolution_type not in ['return', 'replacement']:
                raise UserError(_('This action only applies for Return or Replacement resolutions.'))

            if not record.return_location_id:
                raise UserError(_('Please specify a location.'))

            complaint = record.complaint_id
            partner_location = complaint.purchased_shop_id.property_stock_customer.id
            assignment_location = record.return_location_id.id

            # 1. Create Return Picking
            return_picking = self.env['stock.picking'].create({
                'picking_type_id': self.env.ref('stock.picking_type_out').id,  # Or define a specific one
                'partner_id': complaint.purchased_shop_id.id,
                'location_id': partner_location,
                'location_dest_id': assignment_location,
                'origin': complaint.name,
                'assignment_id': record.id,
                'move_ids_without_package': [(0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': partner_location,
                    'location_dest_id': assignment_location,
                }) for line in complaint.product_line_ids],
            })
            return_picking.action_confirm()

            # 2. Create Replacement Picking if needed
            if record.resolution_type == 'replacement':
                replacement_picking = self.env['stock.picking'].create({
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'partner_id': complaint.purchased_shop_id.id,
                    'location_id': assignment_location,
                    'location_dest_id': partner_location,
                    'origin': complaint.name + ' - Replacement',
                    'assignment_id': record.id,
                    'move_ids_without_package': [(0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.product_id.name + ' (Replacement)',
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': assignment_location,
                        'location_dest_id': partner_location,
                    }) for line in complaint.product_line_ids],
                })
                replacement_picking.action_confirm()

        return True

    @api.depends('picking_ids.state')
    def _compute_all_pickings_validated(self):
        for record in self:
            # Check if all related pickings are validated

            if all(picking.state == 'done' for picking in record.picking_ids):
                record.state = 'done'
                # Once the assignment is done, resolve the complaint
                record.complaint_id.state = 'resolved'

    def action_create_service(self):
        for record in self:
            complaint = record.complaint_id
            if not complaint.product_line_ids:
                raise UserError("No products to repair.")

            for line in complaint.product_line_ids:
                self.env['repair.order'].create({
                    'product_id': line.product_id.id,
                    'schedule_date': record.start_datetime,
                    'user_id': record.technician_id.id,
                    'under_warranty': True if record.warranty_status == 'non_paid' else False,
                    'product_uom': line.product_id.uom_id.id,
                    'product_qty': line.quantity,
                    'partner_id': complaint.customer_id.id,
                    'assignment_id': record.id,
                    'state': 'draft',
                })





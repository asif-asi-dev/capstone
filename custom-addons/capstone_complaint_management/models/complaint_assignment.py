from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ComplaintAssignment(models.Model):
    _name = 'complaint.assignment'
    _description = 'Complaint Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ---------------- FIELDS ---------------- #

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')

    complaint_id = fields.Many2one(
        'complaint.management',
        string='Complaint',
        required=True,
        domain="[('state', '=', 'submitted')]",
        ondelete='cascade',
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('res.users', string='Technician', tracking=True)

    start_datetime = fields.Datetime(string='Start Time', related='complaint_id.create_date', store=True)
    end_datetime = fields.Datetime(string='End Time')

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

    # Stock / Repair links
    picking_ids = fields.One2many('stock.picking', 'assignment_id', string='Related Pickings')
    picking_count = fields.Integer(string="Picking Count", compute="_compute_picking_count")

    repair_order_ids = fields.One2many('repair.order', 'assignment_id', string="Repair Orders")
    repair_count = fields.Integer(string="Service Count", compute="_compute_repair_count")

    # Sale Return Request links
    sale_return_request_ids = fields.One2many('sale.return.request', 'assignment_id', string="Sale Return Requests")
    sale_return_request_count = fields.Integer(string="Sale Returns", compute="_compute_sale_return_request_count")

    hours_taken = fields.Float(string="Hours Taken", compute='_compute_hours_taken', store=True)
    google_map_link = fields.Char("Google Map Location URL", related='complaint_id.google_map_link')


    # ---------------- COMPUTES (Serialization-safe) ---------------- #

    @api.depends('start_datetime', 'end_datetime')
    def _compute_hours_taken(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.hours_taken = round(delta.total_seconds() / 3600.0, 2)
            else:
                rec.hours_taken = 0.0

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.depends('repair_order_ids')
    def _compute_repair_count(self):
        for rec in self:
            rec.repair_count = len(rec.repair_order_ids)

    @api.depends('sale_return_request_ids')
    def _compute_sale_return_request_count(self):
        for rec in self:
            rec.sale_return_request_count = len(rec.sale_return_request_ids)

    # Replacement closure (triggered after pickings validate)
    @api.depends('picking_ids.state')
    def _compute_all_pickings_validated(self):
        """
        Close assignment ONLY for Replacement when all related pickings are done.
        Return flow is handled by _compute_close_after_return().
        """
        for rec in self:
            if rec.resolution_type == 'replacement':
                if rec.picking_ids and all(p.state == 'done' for p in rec.picking_ids):
                    rec.state = 'done'
                    if rec.complaint_id:
                        rec.complaint_id.state = 'resolved'

    # Return closure (triggered when SRR or their SRO change state)
    def _check_close_return_assignment(self):
        """Close assignment for return flow if SRR and SRO are fully completed"""
        for rec in self:
            if rec.resolution_type != 'return':
                continue
            if not rec.sale_return_request_ids:
                continue

            all_requests_done = all(req.state == 'done' for req in rec.sale_return_request_ids)
            all_orders_done = all(
                req.return_order_id and req.return_order_id.state == 'completed'
                for req in rec.sale_return_request_ids
            )
            if all_requests_done and all_orders_done:
                rec.state = 'done'
                if rec.complaint_id:
                    rec.complaint_id.state = 'resolved'

    # ---------------- OVERRIDES ---------------- #

    def write(self, vals):
        res = super().write(vals)
        # If moved to done, set end time once (no chatter loops here)
        if vals.get('state') == 'done':
            for rec in self:
                if not rec.end_datetime:
                    rec.end_datetime = fields.Datetime.now()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('complaint.assignment') or 'New'
        return super().create(vals_list)

    # ---------------- SMART BUTTON ACTIONS ---------------- #

    def action_view_picking(self):
        self.ensure_one()
        return {
            'name': _('Related Return/Replacement Pickings'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': {'default_assignment_id': self.id,'create': False},
        }

    def action_view_repairs(self):
        self.ensure_one()
        return {
            'name': _('Related Repair Orders'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'repair.order',
            'domain': [('assignment_id', '=', self.id)],
            'context': {'default_assignment_id': self.id, 'create': False},
        }

    def action_view_sale_return_requests(self):
        self.ensure_one()
        return {
            'name': _('Sale Return Requests'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'sale.return.request',
            'domain': [('assignment_id', '=', self.id)],
            'context': {'default_assignment_id': self.id, 'create': False},
        }

    # ---------------- STATE ACTIONS ---------------- #

    def action_assign(self):
        for rec in self:
            rec.state = 'assigned'
            if rec.complaint_id:
                rec.complaint_id.state = 'assigned'

    # ---------------- LOGISTICS ---------------- #

    def action_create_logistics(self):
        for rec in self:
            if rec.resolution_type not in ['return', 'replacement']:
                raise UserError(_('This action only applies for Return or Replacement resolutions.'))

            complaint = rec.complaint_id
            if not complaint:
                raise UserError(_('No complaint linked to this assignment.'))

            partner = complaint.purchased_shop_id or complaint.customer_id
            if not partner:
                raise UserError(_('Please set either Purchased Shop or Customer on the complaint.'))

            # RETURN: create Sale Return Request (one header, multiple lines)
            if rec.resolution_type == 'return':
                if not complaint.product_line_ids:
                    raise UserError(_("No products on the complaint to create a return request."))

                SaleReturnRequest = self.env['sale.return.request']
                req_vals = {
                    'partner_id': partner.id,
                    'assignment_id': rec.id,  # assumes this field exists on SRR
                    'notes': _('Created from Complaint %s / Assignment %s') % (complaint.name, rec.name),
                }
                line_commands = []
                for line in complaint.product_line_ids:
                    if not line.product_id:
                        raise UserError(_("Complaint line has no product."))
                    line_commands.append((0, 0, {
                        'product_id': line.product_id.id,
                        'uom_id': line.product_id.uom_id.id,
                        'return_qty': line.quantity,
                        'notes': _('From Complaint %s') % complaint.name,
                    }))
                req_vals['line_ids'] = line_commands
                SaleReturnRequest.create(req_vals)
                # Do NOT auto-close here; closure is handled by _compute_close_after_return

            # REPLACEMENT: create outgoing picking (assignment -> customer)
            if rec.resolution_type == 'replacement':

                if not rec.return_location_id:
                    raise UserError(_('Please specify a Return Location.'))

                partner_location = partner.property_stock_customer.id
                assignment_location = rec.return_location_id.id

                if not complaint.product_line_ids:
                    raise UserError(_("No products on the complaint for replacement."))

                # 1️⃣ RETURN PICKING (Customer → Return Location)
                return_picking = self.env['stock.picking'].create({
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,  # same as your original
                    'partner_id': partner.id,
                    'location_id': partner_location,  # from customer
                    'location_dest_id': assignment_location,  # to service/return location
                    'origin': complaint.name + " - Return",
                    'assignment_id': rec.id,
                    'move_ids_without_package': [
                        (0, 0, {
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'product_uom_qty': line.quantity,
                            'product_uom': line.product_id.uom_id.id,
                            'location_id': partner_location,
                            'location_dest_id': assignment_location,
                        }) for line in complaint.product_line_ids
                    ],
                })
                return_picking.action_confirm()

                # 2️⃣ REPLACEMENT PICKING (Return Location → Customer)
                replacement_picking = self.env['stock.picking'].create({
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'partner_id': partner.id,
                    'location_id': assignment_location,  # from return location
                    'location_dest_id': partner_location,  # to customer
                    'origin': complaint.name + " - Replacement",
                    'assignment_id': rec.id,
                    'move_ids_without_package': [
                        (0, 0, {
                            'product_id': line.product_id.id,
                            'name': f"{line.product_id.name} (Replacement)",
                            'product_uom_qty': line.quantity,
                            'product_uom': line.product_id.uom_id.id,
                            'location_id': assignment_location,
                            'location_dest_id': partner_location,
                        }) for line in complaint.product_line_ids
                    ],
                })
                replacement_picking.action_confirm()

            return True

    # ---------------- SERVICE ---------------- #

    def action_create_service(self):
        for rec in self:
            complaint = rec.complaint_id
            if not complaint or not complaint.product_line_ids:
                raise UserError(_("No products to repair."))

            for line in complaint.product_line_ids:
                if not line.product_id:
                    raise UserError(_("Complaint line has no product."))
                self.env['repair.order'].sudo().create({
                    'product_id': line.product_id.id,
                    'schedule_date': rec.start_datetime,
                    'user_id': rec.technician_id.id,
                    # Business rule preserved: "non_paid" => under warranty (free)
                    'under_warranty': True if rec.warranty_status == 'non_paid' else False,
                    'product_uom': line.product_id.uom_id.id,
                    'product_qty': line.quantity,
                    'partner_id': complaint.customer_id.id,
                    'assignment_id': rec.id,
                    'state': 'draft',
                })

    def action_open_reassign_wizard(self):
        self.ensure_one()

        if self.state != 'assigned':
            raise UserError(_('Only assigned complaints can be reassigned.'))

        if self.picking_ids or self.repair_order_ids or self.sale_return_request_ids:
            raise UserError(
                _('Reassignment is not allowed once return, replacement, or service has started.')
            )

        return {
            'name': _('Reassign Technician'),
            'type': 'ir.actions.act_window',
            'res_model': 'complaint.assignment.reassign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_assignment_id': self.id,
                'default_new_technician_id': False,
            }
        }


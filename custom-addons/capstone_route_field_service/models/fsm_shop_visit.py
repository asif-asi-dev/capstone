from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FSMShopVisit(models.Model):
    _name = 'fsm.shop.visit'
    _description = 'FSM Shop Visit'
    _order = 'visit_datetime desc'
    _rec_name = 'name'

    name = fields.Char(string="Reference", required=True, readonly=True, default="New")
    visit_datetime = fields.Datetime(string="Visit Date & Time", required=True, default=fields.Datetime.now)
    weekday_id = fields.Many2one('fsm.weekday', string='Weekday', compute="_compute_weekday", store=True)
    route_assignement_id = fields.Many2one(
        'fsm.route.assignment',
        string='Route Assignment',
        domain="[('sales_partner_id', '=', salesperson_id), ('state','=','confirmed'), ('week_day_ids', 'in', weekday_id)]"
    )
    shop_id = fields.Many2one('res.partner', string='Shop', domain="[('id', 'in', shop_domain_ids)]", required=True)
    shop_domain_ids = fields.Many2many('res.partner', compute="_compute_shop_domain_ids", store=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_shop', 'On Shop'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    salesperson_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    feedback = fields.Text(string="Shopkeeper Feedback")
    market_trends = fields.Text(string="Market Trends")
    expense_ids = fields.One2many('hr.expense','fsm_visit_id')
    visit_master_id = fields.Many2one('fsm.shop.visit.master', string='Visit Master')
    prvs_shop_id = fields.Many2one('res.partner', string='Previous Shop', domain="[('id', 'in', shop_domain_ids)]", required=True)
    kilometers_traveled = fields.Float()

    @api.depends('visit_datetime')
    def _compute_weekday(self):
        for rec in self:
            if rec.visit_datetime:
                weekday_str = fields.Date.from_string(rec.visit_datetime.date()).strftime('%A')
                weekday = self.env['fsm.weekday'].search([('name', '=', weekday_str)], limit=1)
                rec.weekday_id = weekday
            else:
                rec.weekday_id = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit') or 'New'
        return super(FSMShopVisit, self).create(vals)

    @api.depends('route_assignement_id')
    def _compute_shop_domain_ids(self):
        for rec in self:
            rec.shop_domain_ids = rec.route_assignement_id.shop_ids if rec.route_assignement_id else False


    def action_create_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.shop_id.id,
                'default_user_id': self.salesperson_id.id,
                'default_fsm_visit_id': self.id,
            },
            'target': 'current',
        }

    def action_create_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.shop_id.id,
                'default_user_id': self.salesperson_id.id,
                'default_fsm_visit_id': self.id,
            },
            'target': 'current',
        }

    def action_create_expense(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'form',
            'context': {
                'default_fsm_visit_id': self.id,
            },
            'target': 'current',
        }

    def action_visit_shop(self):
        for visit in self:
            visit.state = 'on_shop'
            existing_master = self.env['fsm.shop.visit.master'].search([
                ('date', '=', fields.Date.today()),
                ('salesperson_id', '=', self.salesperson_id.id),
                ('route_assignement_id', '=', self.route_assignement_id.id)
            ], limit=1)
            if existing_master:
                self.visit_master_id = existing_master.id
            else:
                vals = {
                    'date': fields.Date.today(),
                    'salesperson_id': self.salesperson_id.id,
                    'route_assignement_id': self.route_assignement_id.id,
                    'weekday_id':self.weekday_id.id
                }

                visit_master = self.env['fsm.shop.visit.master'].create(vals)

                self.visit_master_id = visit_master.id

    def action_open_visit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fsm.shop.visit',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_create_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'context': {
                'default_fsm_visit_id': self.id,
                'default_partner_id': self.shop_id.id,
            },
            'target': 'current',
        }


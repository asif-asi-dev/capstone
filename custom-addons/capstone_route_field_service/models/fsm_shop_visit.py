from odoo import models, fields, api
from odoo.exceptions import ValidationError

from datetime import datetime
from odoo.tools import date_utils

class FSMShopVisit(models.Model):
    _name = 'fsm.shop.visit'
    _description = 'FSM Shop Visit'
    _order = 'visit_datetime desc'
    _rec_name = 'name'

    name = fields.Char(string="Reference", required=True, readonly=True, default="New")
    visit_datetime = fields.Datetime(string="Visit Date & Time", required=True, default=fields.Datetime.now)
    weekday_id = fields.Many2one('fsm.weekday', string='Weekday', compute="_compute_weekday", store=True, index=True)
    route_assignement_id = fields.Many2one(
        'fsm.route.assignment',
        string='Route Assignment',
        domain="[('sales_partner_id', '=', salesperson_id), ('state','=','confirmed'), ('week_day_ids', 'in', [weekday_id])]",
        index=True
    )
    shop_id = fields.Many2one('res.partner', string='Shop', domain="[('id', 'in', shop_domain_ids)]", required=True, index=True)
    shop_domain_ids = fields.Many2many('res.partner', compute="_compute_shop_domain_ids", store=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_shop', 'On Shop'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)

    salesperson_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user, index=True)
    feedback = fields.Text(string="Shopkeeper Feedback")
    market_trends = fields.Text(string="Market Trends")
    expense_ids = fields.One2many('hr.expense','fsm_visit_id')
    visit_master_id = fields.Many2one('fsm.shop.visit.master', string='Visit Master', index=True)
    prvs_shop_id = fields.Many2one('res.partner', string='Previous Shop', domain="[('id', 'in', shop_domain_ids)]")
    kilometers_traveled = fields.Float()

    lead_ids = fields.One2many('crm.lead', 'fsm_visit_id', string="Leads")
    sale_order_ids = fields.One2many('sale.order', 'fsm_visit_id', string="Sales Orders")
    payment_ids = fields.One2many('account.payment', 'fsm_visit_id', string="Payments")

    lead_count = fields.Integer(string="Leads", compute="_compute_counts", store=False)
    sale_count = fields.Integer(string="Sales Orders", compute="_compute_counts", store=False)
    payment_count = fields.Integer(string="Payments", compute="_compute_counts", store=False)

    @api.depends('lead_ids', 'sale_order_ids', 'payment_ids')
    def _compute_counts(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)
            rec.sale_count = len(rec.sale_order_ids)
            rec.payment_count = len(rec.payment_ids)

    def action_view_leads(self):
        self.ensure_one()
        return {
            'name': 'Leads',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'tree,form',
            'domain': [('fsm_visit_id', '=', self.id)],
            'context': {'default_fsm_visit_id': self.id},
        }

    def action_view_sales_orders(self):
        self.ensure_one()
        return {
            'name': 'Sales Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('fsm_visit_id', '=', self.id)],
            'context': {'default_fsm_visit_id': self.id},
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': 'Payments',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('fsm_visit_id', '=', self.id)],
            'context': {'default_fsm_visit_id': self.id},
        }


    @api.depends('visit_datetime')
    def _compute_weekday(self):
        Weekday = self.env['fsm.weekday']
        for rec in self:
            if not rec.visit_datetime:
                rec.weekday_id = False
                continue
            # Convert to user's timezone
            user_dt = fields.Datetime.context_timestamp(rec, rec.visit_datetime)
            weekday_str = user_dt.strftime('%A')
            weekday = Weekday.search([('name', '=', weekday_str)], limit=1)
            rec.weekday_id = weekday.id if weekday else False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit') or 'New'
        # Auto-set prvs_shop_id: last visit in same master or same salesperson on same day
        if not vals.get('prvs_shop_id'):
            domain = []
            if vals.get('visit_master_id'):
                domain = [('visit_master_id', '=', vals['visit_master_id'])]
            else:
                # fallback: same salesperson, same date
                salesperson_id = vals.get('salesperson_id') or self.env.user.id
                dt = vals.get('visit_datetime') or fields.Datetime.now()
                date_local = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(dt)).date()
                date_utc_start = fields.Datetime.to_datetime(f"{date_local} 00:00:00")
                date_utc_end = fields.Datetime.to_datetime(f"{date_local} 23:59:59")
                domain = [
                    ('salesperson_id', '=', salesperson_id),
                    ('visit_datetime', '>=', date_utc_start),
                    ('visit_datetime', '<=', date_utc_end),
                ]
            last_visit = self.search(domain, order='visit_datetime desc', limit=1)
            if last_visit and last_visit.shop_id:
                vals['prvs_shop_id'] = last_visit.shop_id.id
        return super().create(vals)

    def action_cancel_visit(self):
        for rec in self:
            if rec.state in ['done', 'cancel']:
                continue
            rec.state = 'cancel'

    def action_finish_visit(self):
        for rec in self:
            if rec.state != 'on_shop':
                continue
            rec.state = 'done'



    @api.depends('route_assignement_id')
    def _compute_shop_domain_ids(self):
        for rec in self:
            rec.shop_domain_ids = [(6, 0, rec.route_assignement_id.shop_ids.ids)] if rec.route_assignement_id else [(5, 0, 0)]

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
                ('date', '=', fields.Date.context_today(self)),
                ('salesperson_id', '=', visit.salesperson_id.id),
                ('route_assignement_id', '=', visit.route_assignement_id.id),
            ], limit=1)
            if existing_master:
                visit.visit_master_id = existing_master.id
            else:
                visit_master = self.env['fsm.shop.visit.master'].create({
                    'date': fields.Date.context_today(self),
                    'salesperson_id': visit.salesperson_id.id,
                    'route_assignement_id': visit.route_assignement_id.id,
                    'weekday_id': visit.weekday_id.id,
                })
                visit.visit_master_id = visit_master.id

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



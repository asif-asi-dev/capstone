from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FSMShopVisit(models.Model):
    _name = 'fsm.shop.visit'
    _description = 'FSM Shop Visit'
    _order = 'visit_datetime desc'
    _rec_name = 'name'

    name = fields.Char(string="Reference", required=True, readonly=True, default="New")
    visit_datetime = fields.Datetime(string="Visit Date & Time", required=True, default=fields.Datetime.now)
    route_id = fields.Many2one('fsm.route', string='Route', required=True, domain=lambda self: self._get_route_domain())
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

    # @api.model_create_multi
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit') or 'New'
    #     return super(FSMShopVisit, self).create(vals)

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit') or 'New'
    #     return super(ComplaintAssignment, self).create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, list):
            for vals in vals_list:
                if vals.get('name', 'New') == 'New':
                    vals['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit') or 'New'
        else:
            if vals_list.get('name', 'New') == 'New':
                vals_list['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit') or 'New'
        return super(FSMShopVisit, self).create(vals_list)

    @api.depends('route_id')
    def _compute_shop_domain_ids(self):
        for rec in self:
            rec.shop_domain_ids = rec.route_id.shop_ids if rec.route_id else False

    def _get_route_domain(self):
        partner = self.env.user.partner_id
        return [('partner_id', '=', partner.id)]

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
                'default_route_id': self.route_id.id,
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
                'default_route_id': self.route_id.id,
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
                'default_route_id': self.route_id.id,
            },
            'target': 'current',
        }

    def action_visit_shop(self):
        for visit in self:
            visit.state = 'on_shop'


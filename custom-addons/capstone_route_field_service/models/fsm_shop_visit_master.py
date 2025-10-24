from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FSMShopVisitMaster(models.Model):
    _name = 'fsm.shop.visit.master'
    _description = 'Shop Visit Master'

    name = fields.Char(string="Visit Reference", readonly=True, copy=False, default='New')
    salesperson_id = fields.Many2one('res.users', string='Salesperson', required=True, index=True)
    date = fields.Date(string='Visit Date', required=True, index=True)
    weekday_id = fields.Many2one('fsm.weekday', string='Week Day', required=True, index=True)
    route_assignement_id = fields.Many2one(
        'fsm.route.assignment',
        string='Route Assignment',
        domain="[('state', '=', 'confirmed')]",
        index=True
    )
    shop_visit_ids = fields.One2many('fsm.shop.visit', 'visit_master_id', string='Shop Visits')
    total_klm_traveled = fields.Float(
        'Kilometers Traveled',
        digits=(16, 2),
        compute='_compute_total_klm_traveled',
        store=True,
    )

    @api.depends('shop_visit_ids.kilometers_traveled')
    def _compute_total_klm_traveled(self):
        for record in self:
            record.total_klm_traveled = sum(record.shop_visit_ids.mapped('kilometers_traveled'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit.master') or 'New'
        return super().create(vals)

    @api.onchange('salesperson_id', 'weekday_id')
    def _onchange_salesperson_weekday(self):
        if self.salesperson_id and self.weekday_id:
            return {
                'domain': {
                    'route_assignement_id': [
                        ('sales_partner_id', '=', self.salesperson_id.id),
                        ('state', '=', 'confirmed'),
                        # optional: filter by weekday
                        # ('week_day_ids', 'in', [self.weekday_id.id]),
                    ]
                }
            }

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FSMShopVisitMaster(models.Model):
    _name = 'fsm.shop.visit.master'
    _description = 'Shop Visit Master'

    name = fields.Char(string="Visit Reference", readonly=True, copy=False, default='New')
    salesperson_id = fields.Many2one('res.users', string='Salesperson', required=True)
    date = fields.Date(string='Visit Date', required=True)
    weekday_id = fields.Many2one('fsm.weekday', string='Week Day', required=True)
    route_assignment_id = fields.Many2one(
        'fsm.route.assignment',
        string='Route Assignment',
        domain="[('state', '=', 'confirmed')]"
    )
    shop_visit_ids = fields.One2many('fsm.shop.visit', 'visit_master_id', string='Shop Visits')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fsm.shop.visit.master') or 'New'
        return super().create(vals)

    @api.onchange('salesperson_id', 'weekday_id')
    def _onchange_salesperson_weekday(self):
        """Filter route assignments based on salesperson and weekday."""
        if self.salesperson_id and self.weekday_id:
            return {
                'domain': {
                    'route_assignment_id': [
                        ('sales_partner_id', '=', self.salesperson_id.id),
                        ('state', '=', 'confirmed'),
                    ]
                }
            }

from odoo import models, fields,api

class FSMRouteAssignment(models.Model):
    _name = 'fsm.route.assignment'
    _description = 'Field Service Route Assignment'
    _rec_name = 'route_id'

    route_id =  fields.Many2one('fsm.route',string='Route')
    sales_partner_id = fields.Many2one('res.users',string='Sales Person')
    week_day_ids = fields.Many2many('fsm.weekday', string='Week Days')
    shop_ids = fields.Many2many('res.partner', string='Shops in Route',
                               domain="[('is_company', '=', True), ('route_id', '!=', False)]")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string="Status", default='draft', tracking=True)

    @api.onchange('route_id')
    def _onchange_route_id(self):
        if self.route_id:
            shops = self.env['res.partner'].search([
                ('route_id', '=', self.route_id.id),
            ])
            self.shop_ids = [(6, 0, shops.ids)]
        else:
            self.shop_ids = False

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'


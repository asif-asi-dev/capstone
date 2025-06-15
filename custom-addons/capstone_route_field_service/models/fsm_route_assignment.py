from odoo import models, fields,api

class FSMRouteAssignment(models.Model):
    _name = 'fsm.route.assignment'
    _description = 'Field Service Route Assignment'
    _rec_name = 'route_id'

    route_id =  fields.Many2one('fsm.route',string='Route')
    partner_id = fields.Many2one('res.partner',string='Sales Person')
    week_day_ids = fields.Many2many('fsm.weekday', string='Week Days')
    shop_ids = fields.Many2many('res.partner', string='Shops in Route',
                               domain="[('is_company', '=', True), ('route_id', '!=', False)]")

    @api.onchange('route_id')
    def _onchange_route_id(self):
        if self.route_id:
            shops = self.env['res.partner'].search([
                ('route_id', '=', self.route_id.id),
            ])
            self.shop_ids = [(6, 0, shops.ids)]
        else:
            self.shop_ids = False


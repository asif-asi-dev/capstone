from odoo import models, fields

class FSMRoute(models.Model):
    _name = 'fsm.route'
    _description = 'Field Service Route'

    name = fields.Char(string='Route Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Route Responsible')
    shop_ids = fields.Many2many('res.partner', string='Shops in Route',
                                domain="[('is_company', '=', True)]")
    total_km = fields.Float(string='Total Distance (KM)')
    week_day_ids = fields.Many2many('fsm.weekday', string='Week Days')

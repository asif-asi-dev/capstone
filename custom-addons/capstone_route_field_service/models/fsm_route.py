from odoo import models, fields

class FSMRoute(models.Model):
    _name = 'fsm.route'
    _description = 'Field Service Route'

    name = fields.Char(string='Route Name', required=True)
    shop_ids = fields.One2many('res.partner','route_id', string='Shops in Route',
                               domain="[('is_company', '=', True)]")
    total_km = fields.Float(string='Total Distance (KM)')
    area_id =  fields.Many2one('fsm.area',string='Area')
from odoo import models, fields

class FSMArea(models.Model):
    _name = 'fsm.area'
    _description = 'Field Service Route Area'

    name = fields.Char(string='Area Name', required=True)
    country_id = fields.Many2one(comodel_name='res.country', string='Country', required=True ,default=lambda self: self.env.ref('base.in').id)
    state_id = fields.Many2one(comodel_name='res.country.state', string='State', domain="[('country_id', '=', country_id)]")
    city = fields.Char()

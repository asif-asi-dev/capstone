from odoo import models, fields

class FSMArea(models.Model):
    _name = 'fsm.area'
    _description = 'Field Service Route Area'

    name = fields.Char(string='Area Name', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True,
                                 default=lambda self: self.env.ref('base.in').id, index=True)
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id', '=', country_id)]", index=True)
    city = fields.Char()

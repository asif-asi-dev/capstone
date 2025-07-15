from odoo import models, fields

class FSMTerritory(models.Model):
    _name = 'fsm.territory'
    _description = 'Field Service Territory'
    _rec_name = 'name'

    name = fields.Char(string='Territory Name', required=True)
    sales_incharge_id = fields.Many2one('res.users', string='Sales Incharge', required=True)

from odoo import models, fields

class FSMWeekday(models.Model):
    _name = 'fsm.weekday'
    _description = 'Weekday'

    name = fields.Char(string='Day', required=True)
    code = fields.Char(string='Code', required=True)

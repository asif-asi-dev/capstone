from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'res.partner'

    route_id = fields.Many2one('fsm.route', string='Route')
    distance_from_company = fields.Integer(string="Distance")
from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    fsm_visit_id = fields.Many2one('fsm.shop.visit', string='Visit Reference')
    route_id = fields.Many2one('fsm.route', string='Route')

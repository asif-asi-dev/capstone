from odoo import models, fields,api

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class FSMRouteAssignment(models.Model):
    _name = 'fsm.route.assignment'
    _description = 'Field Service Route Assignment'
    _rec_name = 'route_id'

    route_id = fields.Many2one('fsm.route', string='Sales Route', required=True, index=True)
    sales_partner_id = fields.Many2one('res.users', string='Sales Person', required=True, index=True)
    week_day_ids = fields.Many2many('fsm.weekday', string='Week Days', required=True)
    shop_ids = fields.Many2many(
        'res.partner',
        string='Shops in Route',
        domain="[('is_company', '=', True), ('route_id', '!=', False)]"
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string="Status", default='draft', tracking=True, index=True)

    @api.onchange('route_id')
    def _onchange_route_id(self):
        for rec in self:
            rec.shop_ids = [(6, 0, rec.route_id.shop_ids.ids)] if rec.route_id else [(5, 0, 0)]

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    # # OPTIONAL (recommended): avoid overlapping weekday assignments per salesperson
    # @api.constrains('sales_partner_id', 'week_day_ids', 'state')
    # def _check_weekday_overlap(self):
    #     for rec in self:
    #         if rec.state != 'confirmed' or not rec.week_day_ids:
    #             continue
    #         conflict = self.search_count([
    #             ('id', '!=', rec.id),
    #             ('sales_partner_id', '=', rec.sales_partner_id.id),
    #             ('state', '=', 'confirmed'),
    #             ('week_day_ids', 'in', rec.week_day_ids.ids),
    #         ])
    #         if conflict:
    #             raise ValidationError(_(
    #                 "This salesperson already has a confirmed route on one or more of the selected weekdays."
    #             ))



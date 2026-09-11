from odoo import api, fields, models


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    capstone_allowed_employee_ids = fields.Many2many(
        'hr.employee', 'capstone_workcenter_employee_rel', 'workcenter_id',
        'employee_id', string='Allowed Employees', check_company=True,
        groups='mrp.group_mrp_manager',
        domain="[('user_id', '!=', False), ('active', '=', True)]",
        help='Only linked logins of active employees may access this work center '
             'and its work orders. An empty list allows administrators only.',
    )
    capstone_allowed_user_ids = fields.Many2many(
        'res.users', compute='_compute_capstone_allowed_user_ids', store=True,
        compute_sudo=True, groups='mrp.group_mrp_manager',
    )

    @api.depends('capstone_allowed_employee_ids.user_id',
                 'capstone_allowed_employee_ids.active')
    def _compute_capstone_allowed_user_ids(self):
        for center in self:
            center.capstone_allowed_user_ids = center.capstone_allowed_employee_ids.filtered(
                'active').mapped('user_id')

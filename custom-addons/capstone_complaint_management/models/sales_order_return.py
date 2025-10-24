# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SalesReturnOrder(models.Model):
    _inherit = 'sales.return.order'

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] == 'completed':
            for rec in self:
                if rec.return_request_id and rec.return_request_id.assignment_id:
                    rec.return_request_id.assignment_id._check_close_return_assignment()
        return res



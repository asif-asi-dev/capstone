# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    is_without_fiscal_position = fields.Boolean(
        string='Is Without Fiscal Position',
        readonly=True,
    )

    @api.model
    def _get_without_fiscal_position(self):
        return self.search([('is_without_fiscal_position', '=', True)], limit=1)

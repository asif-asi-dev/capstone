# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_sale_without = fields.Boolean(
        string='Is Without Sale',
        compute='_compute_is_sale_without',
        store=True,
    )

    @api.depends('invoice_line_ids.sale_line_ids.order_id.is_sale_without')
    def _compute_is_sale_without(self):
        for move in self:
            move.is_sale_without = any(
                move.invoice_line_ids.mapped('sale_line_ids.order_id.is_sale_without')
            )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_sale_without = fields.Boolean(
        string='Is Without Sale',
        compute='_compute_is_sale_without',
        store=True,
    )

    @api.depends('sale_line_ids.order_id.is_sale_without')
    def _compute_is_sale_without(self):
        for line in self:
            line.is_sale_without = any(
                line.sale_line_ids.mapped('order_id.is_sale_without')
            )

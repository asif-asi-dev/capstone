# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_purchase_without = fields.Boolean(
        string='Is Without Purchase',
        compute='_compute_is_purchase_without',
        store=True,
    )

    @api.depends('invoice_line_ids.purchase_line_id.order_id.is_purchase_without')
    def _compute_is_purchase_without(self):
        for move in self:
            move.is_purchase_without = any(
                move.invoice_line_ids.mapped('purchase_line_id.order_id.is_purchase_without')
            )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_purchase_without = fields.Boolean(
        string='Is Without Purchase',
        related='purchase_line_id.order_id.is_purchase_without',
        store=True,
    )

# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_purchase_without = fields.Boolean(
        string='Is Without Purchase',
        related='purchase_line_id.order_id.is_purchase_without',
        store=True,
    )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_purchase_without = fields.Boolean(
        string='Is Without Purchase',
        related='purchase_id.is_purchase_without',
        store=True,
    )


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_purchase_without = fields.Boolean(
        string='Is Without Purchase',
        related='move_id.purchase_line_id.order_id.is_purchase_without',
        store=True,
    )

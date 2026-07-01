# -*- coding: utf-8 -*-

from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_sale_without = fields.Boolean(
        string='Is Without Sale',
        related='sale_line_id.order_id.is_sale_without',
        store=True,
    )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_sale_without = fields.Boolean(
        string='Is Without Sale',
        related='sale_id.is_sale_without',
        store=True,
    )


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_sale_without = fields.Boolean(
        string='Is Without Sale',
        related='move_id.sale_line_id.order_id.is_sale_without',
        store=True,
    )

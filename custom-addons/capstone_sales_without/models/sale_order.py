# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_sale_without = fields.Boolean(string='Is Without Sale')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('is_sale_without') or self.env.context.get('default_is_sale_without'):
            without_fpos = self.env['account.fiscal.position']._get_without_fiscal_position()
            if without_fpos:
                res['fiscal_position_id'] = without_fpos.id
        return res

    @api.depends('partner_shipping_id', 'partner_id', 'company_id', 'is_sale_without')
    def _compute_fiscal_position_id(self):
        without_fpos = self.env['account.fiscal.position']._get_without_fiscal_position()
        orders_without = self.filtered('is_sale_without')
        other_orders = self - orders_without
        if other_orders:
            super(SaleOrder, other_orders)._compute_fiscal_position_id()
        for order in orders_without:
            order.fiscal_position_id = without_fpos

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_sale_without = fields.Boolean(
        string='Is Without Sale',
        related='order_id.is_sale_without',
    )

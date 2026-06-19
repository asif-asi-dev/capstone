# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_purchase_without = fields.Boolean(string='Is Without Purchase')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('is_purchase_without') or self.env.context.get('default_is_purchase_without'):
            without_fpos = self.env['account.fiscal.position']._get_without_fiscal_position()
            if without_fpos and 'fiscal_position_id' in fields_list:
                res['fiscal_position_id'] = without_fpos.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        without_fpos = self.env['account.fiscal.position']._get_without_fiscal_position()
        for vals in vals_list:
            if vals.get('is_purchase_without') and without_fpos:
                vals['fiscal_position_id'] = without_fpos.id
        return super().create(vals_list)

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        res = super().onchange_partner_id()
        if self.is_purchase_without:
            without_fpos = self.env['account.fiscal.position']._get_without_fiscal_position()
            if without_fpos:
                self.fiscal_position_id = without_fpos
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_purchase_without = fields.Boolean(
        string='Is Without Purchase',
        related='order_id.is_purchase_without',
    )

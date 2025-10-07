from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    def _get_pricelist_price(self):
        self.ensure_one()

        price = super()._get_pricelist_price()

        customer = self.order_id.partner_id
        product = self.product_id

        margin = getattr(customer, "margin_percent", 0.0) or 0.0
        discount = getattr(customer, "discount_percent", 0.0) or 0.0

        if not customer or not product:
            return price
        if margin == 0.0 and discount == 0.0:
            return price
        if product.net_rate_based_on == "net_rate":
            return price

        elif product.net_rate_based_on == "margin":
            mrp = product.mrp or 0.0
            margin_price = mrp - (mrp * margin / 100.0)
            final_price = margin_price - (margin_price * discount / 100.0)
            return final_price

        return price







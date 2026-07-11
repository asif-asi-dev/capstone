import math

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_manual_fixed_tax = fields.Boolean(
        string="Manual Fixed Tax",
        help="Only applies when Tax Computation is 'Fixed'.\n"
             "If enabled, the tax amount is computed as:\n"
             "    Price Unit x Fixed Amount\n"
             "instead of Odoo's default:\n"
             "    Quantity x Fixed Amount\n\n"
             "Typical setup: set Fixed 'Amount' = 1, enable this option, "
             "and let users type the arbitrary manual tax figure directly "
             "into the line's Price Unit (with Quantity locked at 1)."
    )

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None,
                         partner=None, fixed_multiplicator=1):
        self.ensure_one()

        if self.amount_type == 'fixed' and self.is_manual_fixed_tax:
            # Same copysign logic Odoo uses natively for 'fixed' taxes,
            # except price_unit drives the amount instead of quantity.
            if base_amount:
                return math.copysign(price_unit, base_amount) * self.amount * abs(fixed_multiplicator)
            else:
                return price_unit * self.amount * abs(fixed_multiplicator)

        return super()._compute_amount(
            base_amount,
            price_unit,
            quantity=quantity,
            product=product,
            partner=partner,
            fixed_multiplicator=fixed_multiplicator,
        )

    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True,
                                        include_caba_tags=False, early_pay_discount_computation=None,
                                        early_pay_discount_percentage=None):
        """ This is the single shared entry point Odoo uses to compute a line's
        own price_subtotal/price_total AND to build the aggregate 'Untaxed
        Amount' / tax-totals summary widget (both on sale/purchase orders and
        on the invoice's tax_totals widget). Patching it here - instead of
        patching price_subtotal after the fact in each line model - fixes
        every place the amount is shown/used in a single spot.

        Any base line carrying our 'manual_gst_carrier' marker (set via
        _convert_to_tax_base_line_dict on the line models) has its base
        amount excluded from Untaxed Amount; only its tax portion remains,
        and is reported instead as the line's own total.
        """
        to_update_vals, tax_values_list = super()._compute_taxes_for_single_line(
            base_line,
            handle_price_include=handle_price_include,
            include_caba_tags=include_caba_tags,
            early_pay_discount_computation=early_pay_discount_computation,
            early_pay_discount_percentage=early_pay_discount_percentage,
        )
        if base_line.get('extra_context', {}).get('manual_gst_carrier'):
            tax_amount = to_update_vals['price_total'] - to_update_vals['price_subtotal']
            to_update_vals['price_subtotal'] = 0.0
            to_update_vals['price_total'] = tax_amount
        return to_update_vals, tax_values_list

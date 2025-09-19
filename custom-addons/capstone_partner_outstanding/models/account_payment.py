from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    partner_outstanding_amount = fields.Monetary(
        string="Outstanding Balance",
        currency_field="currency_id",
        compute="_compute_partner_outstanding_amount",
        store=False,
    )

    @api.depends("partner_id")
    def _compute_partner_outstanding_amount(self):
        for rec in self:
            if rec.partner_id:
                # sum residuals for this partner
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(amount_residual), 0.0)
                    FROM account_move
                    WHERE partner_id = %s
                      AND state = 'posted'
                      AND payment_state NOT IN ('paid','reversed')
                      AND move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
                """, [rec.partner_id.id])
                result = self.env.cr.fetchone()
                rec.partner_outstanding_amount = result[0] or 0.0
            else:
                rec.partner_outstanding_amount = 0.0

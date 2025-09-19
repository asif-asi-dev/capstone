from odoo import api, fields, models, tools
from datetime import date


class CustomerOutstandingReport(models.Model):
    _name = "customer.outstanding.report"
    _description = "Customer/Vendor Outstanding Report"
    _auto = False
    _order = "invoice_date desc"

    invoice_id = fields.Many2one("account.move", string="Invoice")
    partner_id = fields.Many2one("res.partner", string="Partner")
    move_type = fields.Selection([
        ("out_invoice", "Customer Invoice"),
        ("out_refund", "Customer Credit Note"),
        ("in_invoice", "Vendor Bill"),
        ("in_refund", "Vendor Credit Note"),
    ], string="Type")
    invoice_date = fields.Date("Invoice Date")
    due_date = fields.Date("Due Date")
    amount_total = fields.Monetary("Total", currency_field="currency_id")
    residual = fields.Monetary("Outstanding", currency_field="currency_id")
    age = fields.Integer("Age (Days)")
    currency_id = fields.Many2one("res.currency", string="Currency")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    am.id as id,
                    am.id as invoice_id,
                    am.partner_id,
                    am.move_type,
                    am.invoice_date,
                    am.invoice_date_due as due_date,
                    am.amount_total,
                    am.amount_residual as residual,
                    am.currency_id,
                    (CURRENT_DATE - am.invoice_date)::int as age
                FROM account_move am
                WHERE am.state = 'posted'
                  AND am.payment_state NOT IN ('paid', 'reversed')
                  AND am.move_type IN ('out_invoice','out_refund','in_invoice','in_refund')
            )
        """)

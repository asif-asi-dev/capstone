from odoo import models, fields, api


class ComplaintProductLine(models.Model):
    _name = 'complaint.product.line'
    _description = 'Complaint Product Line'

    complaint_id = fields.Many2one('complaint.management', string='Complaint', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)

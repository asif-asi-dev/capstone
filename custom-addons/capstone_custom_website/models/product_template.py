from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_years = fields.Integer(string='Warranty Years', default=2)
    material_description = fields.Text(string='Material Description')
    technical_specs = fields.Text(string='Technical Specifications')
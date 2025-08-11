from odoo import http
from odoo.http import request


class CapstoneBathFittings(http.Controller):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        # Get all product categories
        categories = request.env['product.category'].sudo().search([])

        category_products = []
        for category in categories:
            # Fetch products under the category
            products = request.env['product.template'].sudo().search([
                ('categ_id', '=', category.id),
                ('detailed_type', '=', 'product'),
                ('active', '=', True)
            ])
            # Append only if there are products
            if products:
                category_products.append({
                    'category': category,
                    'products': products
                })

        return request.render('capstone_custom_website.homepage', {
            'category_products': category_products,
        })

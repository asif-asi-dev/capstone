from odoo import http
from odoo.http import request


class CapstoneBathFittings(http.Controller):

    @http.route('/', type='http', auth="public", website=True)
    def index(self, **kw):
        """Render the public catalogue from products published for this website.

        The website-published field respects the current website, which keeps
        unpublished and other-website products out of the public catalogue.
        """
        products = request.env['product.template'].sudo().with_context(
            website_id=request.website.id,
        ).search([
            ('active', '=', True),
            ('website_published', '=', True),
        ], order='categ_id, name')

        category_products = [
            {
                'category': category,
                'products': products.filtered(lambda product: product.categ_id == category),
            }
            for category in products.mapped('categ_id').sorted('name')
        ]

        return request.render('capstone_custom_website.homepage', {
            'category_products': category_products,
        })

// capstone_custom_website/static/src/js/website.js

$(document).ready(function() {

    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        var target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 80
            }, 800);
        }
    });

    // Animate elements on scroll
    function animateOnScroll() {
        $('.about-card, .product-card').each(function() {
            var elementTop = $(this).offset().top;
            var elementBottom = elementTop + $(this).outerHeight();
            var viewportTop = $(window).scrollTop();
            var viewportBottom = viewportTop + $(window).height();

            if (elementBottom > viewportTop && elementTop < viewportBottom) {
                $(this).addClass('animate-in');
            }
        });
    }

    // Run animation on scroll and page load
    $(window).on('scroll', animateOnScroll);
    animateOnScroll();

    // Product search (if you add search functionality later)
    if ($('#productSearch').length) {
        $('#productSearch').on('input', function() {
            var searchTerm = $(this).val().toLowerCase();
            $('.product-card').each(function() {
                var productName = $(this).find('.product-name').text().toLowerCase();
                var productCode = $(this).find('.product-code').text().toLowerCase();

                if (productName.includes(searchTerm) || productCode.includes(searchTerm)) {
                    $(this).closest('.col-lg-3').show();
                } else {
                    $(this).closest('.col-lg-3').hide();
                }
            });
        });
    }
});

// Product detail modal function
function viewProductDetails(button) {
    var productCard = $(button).closest('.product-card');
    var productName = productCard.find('.product-name').text();
    var productCode = productCard.find('.product-code').text() || 'N/A';
    var productPrice = productCard.find('.product-price').text() || 'Price on Request';
    var productImage = productCard.find('.product-image img').attr('src');

    var modalContent = `
        <div class="row">
            <div class="col-md-6">
                <img src="${productImage}" alt="${productName}" class="img-fluid rounded">
            </div>
            <div class="col-md-6">
                <h5>${productName}</h5>
                <p><strong>${productCode}</strong></p>
                <p class="text-primary fs-5">${productPrice}</p>
                <div class="mt-3">
                    <h6>Features:</h6>
                    <ul class="list-unstyled">
                        <li><i class="fa fa-check text-success me-2"></i>Premium Quality Finish</li>
                        <li><i class="fa fa-check text-success me-2"></i>Water Saving Technology</li>
                        <li><i class="fa fa-check text-success me-2"></i>Extended Warranty</li>
                        <li><i class="fa fa-check text-success me-2"></i>Easy Installation</li>
                    </ul>
                </div>
                <div class="mt-4">
                    <a href="mailto:info@capstonebathfittings.com?subject=Quote Request for ${productName}" class="btn btn-primary me-2">Request Quote</a>
                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;

    $('#productModalTitle').text(productName);
    $('#productModalBody').html(modalContent);
    $('#productModal').modal('show');
}

AOS.init({
    duration: 1200,
    once: true,
    easing: 'ease-out-cubic'
});

$(window).scroll(function() {
    if ($(this).scrollTop() > 50) {
        $('.navbar-premium').addClass('scrolled');
    } else {
        $('.navbar-premium').removeClass('scrolled');
    }
});

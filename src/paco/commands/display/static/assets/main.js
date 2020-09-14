$(document).ready( function() {

    // Variables
    var $nav = $('.navbar'),
        $body = $('body'),
        $window = $(window),
        navOffsetTop = $nav.offset().top,
        $document = $(document),
        entityMap = {
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': '&quot;',
          "'": '&#39;',
          "/": '&#x2F;'
        }

    function init() {
      $window.on('scroll', onScroll)
      $window.on('resize', resize)
    }

    $("#button").click(function() {
      $('html, body').animate({
          scrollTop: $("#elementtoScrollToID").offset().top
      }, 2000);
  });

    function resize() {
      $body.removeClass('has-docked-nav')
      navOffsetTop = $nav.offset().top
      onScroll()
    }

    function onScroll() {
      if(navOffsetTop < $window.scrollTop() && !$body.hasClass('has-docked-nav')) {
        $body.addClass('has-docked-nav')
      }
      if(navOffsetTop > $window.scrollTop() && $body.hasClass('has-docked-nav')) {
        $body.removeClass('has-docked-nav')
      }
    }

    function escapeHtml(string) {
      return String(string).replace(/[&<>"'\/]/g, function (s) {
        return entityMap[s];
      });
    }

    init();

  });

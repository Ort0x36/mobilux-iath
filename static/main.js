(function () {
  'use strict';
  window.mobiluxReady = true;

  // --- Mobile menu -----------------------------------------------------------
  var toggle = document.querySelector('.menu-toggle');
  var nav = document.getElementById('main-nav');
  if (toggle && nav) {
    var label = toggle.querySelector('.sr-only');
    var setOpen = function (open) {
      toggle.setAttribute('aria-expanded', String(open));
      nav.classList.toggle('is-open', open);
      label.textContent = open ? toggle.dataset.labelClose : toggle.dataset.labelOpen;
    };
    toggle.addEventListener('click', function () {
      setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });
    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) setOpen(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && nav.classList.contains('is-open')) {
        setOpen(false);
        toggle.focus();
      }
    });
    window.matchMedia('(min-width: 861px)').addEventListener('change', function (event) {
      if (event.matches) setOpen(false);
    });
  }

  // --- Localized form validation messages --------------------------------------
  // Native messages follow the browser language; these follow the page language.
  document.querySelectorAll('form[data-msg-required]').forEach(function (form) {
    form.querySelectorAll('input, select, textarea').forEach(function (field) {
      field.addEventListener('invalid', function () {
        if (field.validity.valueMissing) field.setCustomValidity(form.dataset.msgRequired);
        else if (field.validity.typeMismatch) field.setCustomValidity(form.dataset.msgEmail);
      });
      field.addEventListener('input', function () { field.setCustomValidity(''); });
    });
  });

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // --- Coach build ---------------------------------------------------------------
  // While the pinned stage scrolls past, map progress (0..1) to the line drawing,
  // the photo reveal, the lights and the active step. Listens to scroll only
  // while the section is near the viewport, and updates once per frame.
  var build = document.querySelector('[data-build]');
  if (build && !reduceMotion && 'IntersectionObserver' in window) {
    var sticky = build.querySelector('.build-sticky');
    var ticking = false;
    var clamp = function (value) { return value < 0 ? 0 : value > 1 ? 1 : value; };
    var range = function (p, start, end) { return clamp((p - start) / (end - start)); };

    var update = function () {
      ticking = false;
      var top = parseFloat(getComputedStyle(sticky).top) || 0;
      var distance = build.offsetHeight - sticky.offsetHeight;
      var p = distance > 0 ? clamp((top - build.getBoundingClientRect().top) / distance) : 1;
      build.style.setProperty('--draw', range(p, 0, 0.2).toFixed(3));
      build.style.setProperty('--reveal', range(p, 0.24, 0.56).toFixed(3));
      build.style.setProperty('--glow', range(p, 0.58, 0.76).toFixed(3));
      build.dataset.step = p < 0.22 ? '0' : p < 0.57 ? '1' : p < 0.8 ? '2' : '3';
    };
    var onScroll = function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    };

    new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) {
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll);
        update();
      } else {
        window.removeEventListener('scroll', onScroll);
        window.removeEventListener('resize', onScroll);
      }
    }, { rootMargin: '50% 0px' }).observe(build);
    update();
  }

  // --- Scroll reveal -------------------------------------------------------------
  // Elements with [data-reveal] start hidden (CSS, only when .js is set and motion
  // is allowed) and are shown once when they enter the viewport. Siblings inside a
  // [data-stagger] parent that appear together get increasing delays.
  var items = document.querySelectorAll('[data-reveal]');
  var show = function (el) { el.classList.add('is-visible'); };

  if (reduceMotion || !('IntersectionObserver' in window)) {
    items.forEach(show);
    return;
  }

  var STAGGER_MS = 110;
  var MAX_STEPS = 5;
  var observer = new IntersectionObserver(function (entries) {
    var steps = new Map();
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var el = entry.target;
      var group = el.parentElement;
      if (group && group.hasAttribute('data-stagger')) {
        var step = steps.get(group) || 0;
        steps.set(group, step + 1);
        el.style.setProperty('--reveal-delay', Math.min(step, MAX_STEPS) * STAGGER_MS + 'ms');
      }
      show(el);
      observer.unobserve(el);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0 });

  items.forEach(function (el) { observer.observe(el); });
})();

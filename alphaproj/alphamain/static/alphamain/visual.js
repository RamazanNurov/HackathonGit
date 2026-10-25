'use strict';
(() => {
 const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
 // Decorative feedback never intercepts submit, navigation or keyboard behavior.
 document.addEventListener('pointerdown', event => {
  if(motion.matches || event.button !== 0) return;
  const button = event.target.closest('.primary, .outline, .nav, .tabs button');
  if(!button) return;
  const rect = button.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 2;
  const wave = document.createElement('span');
  wave.className = 'click-wave';
  wave.setAttribute('aria-hidden','true');
  wave.style.setProperty('--wave-size',`${size}px`);
  wave.style.setProperty('--wave-x',`${event.clientX-rect.left-size/2}px`);
  wave.style.setProperty('--wave-y',`${event.clientY-rect.top-size/2}px`);
  button.append(wave);
  wave.addEventListener('animationend',()=>wave.remove(),{once:true});
  setTimeout(()=>wave.remove(),650);
 });
 // Entrance classes are removed so hover transitions take over after arrival.
 document.addEventListener('animationend', event => {
  if(event.animationName==='rise-in' && event.target.matches('.news-card.entering')) event.target.classList.remove('entering');
 });
})();

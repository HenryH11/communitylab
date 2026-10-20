"use strict";
// Se comparte con las pruebas de Node; no requiere paquetes de frontend.
var CommunityLabInteraction = (() => {
  function hitBox(target, elements, width, height, scale = 1) {
    if (target.tipo !== 'text') return target;
    const boxes = Object.values(elements).filter(e => e.tipo === 'rectangle' &&
      e.w <= 600 && e.h <= 100 && e.x <= target.x && e.y <= target.y &&
      e.x + e.w >= target.x + target.w && e.y + e.h >= target.y + target.h);
    const box = boxes.sort((a, b) => a.w * a.h - b.w * b.h)[0] ?? target;
    const w = Math.min(width, Math.max(box.w, target.w + 24 / scale, 44 / scale));
    const h = Math.min(height, Math.max(box.h, 44 / scale));
    return {...box, w, h,
      x: Math.max(0, Math.min(width - w, box.x + (box.w - w) / 2)),
      y: Math.max(0, Math.min(height - h, box.y + (box.h - h) / 2))};
  }
  function requestGate({post, changed, timedOut, schedule = setTimeout, cancel = clearTimeout,
    identify = () => crypto.randomUUID(), timeout = 15000}) {
    let pending = null, timer;
    function release() { cancel(timer); pending = null; changed(false); }
    return {
      get busy() { return pending !== null; },
      send(action, fields) {
        if (pending) return false;
        pending = {id: identify(), accion: action, ...fields};
        const id = pending.id;
        changed(true);
        timer = schedule(() => { if (pending?.id === id) { release(); timedOut(); } }, timeout);
        post(pending);
        return true;
      },
      acknowledge(id) {
        if (!pending || pending.id !== id) return false;
        release(); return true;
      }
    };
  }
  return {hitBox, requestGate};
})();
if (typeof module !== 'undefined') module.exports = CommunityLabInteraction;

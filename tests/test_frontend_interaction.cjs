const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {hitBox, requestGate} = require('../src/app/frontend/interaction.js');
const design = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/app/frontend/design.json'), 'utf8'));

function harness() {
  const sent = [], states = [], timeouts = [], timers = new Map();
  let sequence = 0;
  const gate = requestGate({post: event => sent.push(event), changed: busy => states.push(busy),
    timedOut: () => timeouts.push(true), identify: () => `event-${++sequence}`,
    schedule: callback => {timers.set(sequence, callback); return sequence;},
    cancel: id => timers.delete(id)});
  return {gate, sent, states, timeouts, timers};
}
test('Un clic doble produce una acción; un render anterior no desbloquea la acción actual', () => {
  const h = harness();
  assert.equal(h.gate.send('ejemplo', {}), true);
  assert.equal(h.gate.send('vaciar', {}), false);
  assert.equal(h.gate.acknowledge('event-anterior'), false);
  assert.equal(h.gate.busy, true);
  assert.deepEqual(h.sent, [{id:'event-1', accion:'ejemplo'}]);
  assert.equal(h.gate.acknowledge('event-1'), true);
  assert.equal(h.gate.busy, false);
  assert.equal(h.timers.size, 0);
  assert.equal(h.gate.send('simular', {formato:'instagram'}), true);
  assert.deepEqual(h.states, [true, false, true]);
});
test('Una respuesta ausente permite volver a actuar y una respuesta tardía no desbloquea otra solicitud', () => {
  const h = harness();
  h.gate.send('ejemplo', {});
  h.timers.get(1)();
  assert.equal(h.gate.busy, false);
  assert.equal(h.timeouts.length, 1);
  h.gate.send('vaciar', {});
  assert.equal(h.gate.acknowledge('event-1'), false);
  assert.equal(h.gate.busy, true);
  assert.equal(h.gate.acknowledge('event-2'), true);
});
test('Los botones de texto abarcan toda su forma original y al menos 44 píxeles de alto', () => {
  const checks = {inicio:['DEMO · SIN CUENTAS'], agente:['+ Nueva consulta','Copiar post','Ver resultado ↗','Crear contenido','Enviar  →'], resultado:['Copiar contenido']};
  for (const [key, labels] of Object.entries(checks)) {
    const v = design[key];
    for (const label of labels) {
      const text = Object.values(v.elementos).find(e => e.texto === label);
      assert.ok(text, `${key}: ${label}`);
      const source = Object.values(v.elementos).filter(e => e.tipo === 'rectangle' && e.w <= 600 && e.h <= 100 &&
        e.x <= text.x && e.y <= text.y && e.x+e.w >= text.x+text.w && e.y+e.h >= text.y+text.h)
        .sort((a,b)=>a.w*a.h-b.w*b.h)[0];
      assert.ok(source, `El botón ${label} tiene una forma en el boceto`);
      const b = hitBox(text, v.elementos, v.width, v.height, 1270/v.width);
      assert.ok(b.x <= source.x && b.y <= source.y);
      assert.ok(b.x+b.w >= source.x+source.w && b.y+b.h >= source.y+source.h);
      assert.ok(b.h*1270/v.width >= 44-1e-8);
    }
  }
});
test('Las zonas del menú no se solapan y no toman toda la cabecera como botón', () => {
  for (const v of Object.values(design).filter(v=>v.width===1440)) {
    const labels = ['Inicio','Plantillas','Agente en vivo','Analíticas','Ayuda'];
    const boxes = labels.map(label => hitBox(Object.values(v.elementos).find(e=>e.texto===label),v.elementos,v.width,v.height,1270/v.width));
    boxes.forEach((b,i)=>{assert.ok(b.w < 160); if(i)assert.ok(boxes[i-1].x+boxes[i-1].w <= b.x);});
  }
});
test('Las tarjetas completas conservan su geometría y el menú móvil queda dentro del marco', () => {
  const v=design.inicio, card=v.elementos['cml-00051'];
  assert.deepEqual(hitBox(card,v.elementos,v.width,v.height,1270/v.width), card);
  for (const key of ['movil_inicio','movil_resultado']) {
    const v=design[key], icon=Object.values(v.elementos).find(e=>e.texto==='≡');
    const b=hitBox(icon,v.elementos,v.width,v.height,390/v.width);
    assert.ok(b.x>=0 && b.y>=0 && b.x+b.w<=v.width && b.y+b.h<=v.height);
    assert.ok(b.w*390/v.width>=44-1e-8 && b.h*390/v.width>=44-1e-8);
  }
});

"""Inicio de Marketing: recorrido editorial y navegación nativa de Streamlit."""

from collections.abc import Callable
from datetime import datetime

import streamlit as st

from src.app import tema


ESTILO = """
<style>
.stApp:has(.st-key-inicio) {
    background: #fcf7ed;
}
.stApp:has(.st-key-inicio) [data-testid="stMain"] {
    background: linear-gradient(180deg, #fcf7ed 0%, #f5efe1 25%,
        #eee4ce 55%, #f5efe1 80%, #fcf7ed 100%);
    background-attachment: local;
}
.stApp:has(.st-key-inicio) .communitylab-brand {
    background: transparent; color: var(--cl-tinta);
    padding: 0; letter-spacing: .08em; margin-bottom: .5rem;
}
.stApp:has(.st-key-inicio) .communitylab-brand .cl-espiral {
    width: 3.5rem; height: 3.5rem; color: var(--cl-miel-oscura);
}
.st-key-inicio { max-width: 1160px; margin: 0 auto; }
.st-key-inicio_portada {
    min-height: calc(100svh - var(--inicio-top, 0px));
    display: flex; flex-direction: column; justify-content: center;
    position: relative; padding: 28px 0 85px;
}
.cl-inicio .scroll-cue {
    display: flex; align-items: center; justify-content: center;
    width: 48px; height: 48px; margin: 0 auto; border-radius: 50%;
    border: 1px solid var(--cl-linea); color: var(--cl-miel-oscura);
    text-decoration: none; font-size: 26px;
    animation: cl-invitar 2.5s ease-in-out infinite;
}
.st-key-inicio_portada > [data-testid="stElementContainer"]:last-child {
    position: absolute; bottom: 20px; width: 100%;
}
@keyframes cl-invitar { 50% { transform: translateY(6px); } }
.cl-inicio a:focus-visible { outline: 3px solid var(--cl-miel-oscura); outline-offset: 5px; }
.cl-inicio { color: var(--cl-tinta); }
.cl-inicio p { color: var(--cl-tinta-suave); line-height: 1.75; }
.cl-inicio .eyebrow {
    font: 700 11px var(--cl-texto); letter-spacing: .2em;
    text-transform: uppercase; color: var(--cl-miel-oscura);
}
.cl-inicio h1, .cl-inicio h2, .cl-inicio h3 {
    font-family: Georgia, serif; font-weight: 400; padding: 0;
}
.cl-inicio h1 {
    font-size: clamp(48px, 6.5vw, 96px); line-height: 1.04;
    letter-spacing: -.045em; margin: 24px 0;
}
.cl-inicio h1 em { color: var(--cl-miel-oscura); font-weight: 400; }
.cl-inicio h2 {
    font-size: clamp(34px, 4vw, 51px); line-height: 1.15;
    letter-spacing: -.025em; margin: 18px 0;
}
.cl-inicio h3 { font-size: 25px; line-height: 1.25; margin: 16px 0; }
.cl-inicio .lead { font-size: 18px; max-width: 590px; }
.cl-inicio .hero { text-align: center; padding: 0; }
.cl-inicio .hero .lead { margin: 26px auto; }
.st-key-inicio_hero_botones {
    display: flex; justify-content: center; flex-wrap: wrap;
    margin-bottom: 1rem;
}
.st-key-inicio_hero_botones button, .st-key-inicio_cierre_botones button {
    min-height: 46px; padding: 10px 21px; border-radius: 7px;
}
.st-key-inicio button[kind="primary"] {
    background: var(--cl-tinta); border-color: var(--cl-tinta);
    color: var(--cl-superficie);
}
.cl-inicio .section { padding: 75px 0; border-top: 1px solid var(--cl-linea); }
.cl-inicio .agent-scene { border-top: 0; padding-top: 65px; }
.cl-inicio .split {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 65px; align-items: center;
}
.cl-inicio .panel, .cl-inicio .card, .cl-inicio .file {
    background: var(--cl-superficie); border: 1px solid var(--cl-linea);
    border-radius: 12px; padding: 26px;
}
.cl-inicio .label {
    font-size: 14px;
    color: var(--cl-miel-oscura); border-bottom: 1px solid var(--cl-linea);
    padding-bottom: 14px; margin-bottom: 20px;
}
.cl-inicio .question {
    margin: 0 0 24px auto; padding: 14px 20px; background: var(--cl-pergamino);
    border-radius: 18px 18px 4px 18px; font-size: 16px;
    max-width: 85%; width: fit-content;
}
.cl-inicio .chat { padding: 30px; border-radius: 20px; }
.cl-inicio .answer { font-size: 16px; margin: 0 20px 28px 0; padding-left: 18px; border-left: 2px solid var(--cl-linea); }
.cl-inicio .answer:last-child { margin-bottom: 0; }
.cl-inicio .answer strong { color: var(--cl-miel-oscura); }
.cl-inicio .answer p { margin: 8px 0 0; }
.cl-inicio .pills { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 25px; }
.cl-inicio .pill {
    border: 1px solid var(--cl-linea); border-radius: 100px;
    padding: 7px 13px; font-size: 12px; color: var(--cl-tinta-suave);
}
.cl-inicio .metric { display: flex; justify-content: space-between; font-size: 13px; margin: 15px 0 6px; }
.cl-inicio .track { height: 7px; background: var(--cl-pergamino); border-radius: 10px; }
.cl-inicio .track span { display: block; height: 100%; background: var(--cl-miel-oscura); border-radius: 10px; }
.cl-inicio .track.green span { background: var(--cl-musgo); }
.cl-inicio .section-head { max-width: 650px; margin-bottom: 40px; }
.cl-inicio .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.cl-inicio .card { display: flex; flex-direction: column; }
.cl-inicio .card p { font-size: 14px; }
.cl-inicio .tag { color: var(--cl-miel-oscura); font-size: 11px; letter-spacing: .12em; }
.cl-inicio .sample {
    border-top: 1px solid var(--cl-linea); padding-top: 17px;
    margin-top: auto; font-size: 13px; color: var(--cl-tinta-suave);
}
.cl-inicio .files { display: grid; gap: 12px; }
.cl-inicio .file { display: flex; gap: 15px; align-items: center; padding: 20px; }
.cl-inicio .ext {
    font-size: 11px; color: var(--cl-miel-oscura);
    border: 1px solid var(--cl-linea); border-radius: 5px; padding: 7px;
}
.cl-inicio .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 35px; }
.cl-inicio .step { border-top: 1px solid var(--cl-linea); padding-top: 23px; }
.cl-inicio .step p { font-size: 14px; }
.cl-inicio .step-number { color: var(--cl-miel-oscura); font-size: 12px; }
.cl-inicio .closing { text-align: center; padding: 65px 0 10px; }
.st-key-inicio_cierre_botones { display: flex; justify-content: center; flex-wrap: wrap; margin-bottom: 65px; }
.st-key-inicio_footer { border-top: 1px solid var(--cl-linea); padding-top: 35px; }
.st-key-inicio_footer button[kind="tertiary"] {
    padding: 4px 0; min-height: 40px; justify-content: flex-start;
    border: none; border-radius: 0; background: transparent; color: var(--cl-tinta-suave);
}
.st-key-inicio_footer button[kind="tertiary"]:hover { color: var(--cl-miel-oscura); text-decoration: underline; }
.st-key-inicio_footer [data-testid="stExpander"] details { background: transparent; border: none; }
.st-key-inicio_footer [data-testid="stExpander"] summary { padding-left: 0; }
.cl-inicio .footer-brand {
    display: flex; gap: 12px; align-items: center; font: 700 22px Georgia, serif;
}
.cl-inicio .footer-brand svg { width: 44px; height: 44px; color: var(--cl-miel-oscura); }
.cl-inicio .footer-bottom {
    border-top: 1px solid var(--cl-linea); margin-top: 25px; padding: 20px 0;
    display: flex; justify-content: space-between; flex-wrap: wrap;
    gap: 15px; font-size: 12px; color: var(--cl-tinta-suave);
}
.cl-inicio .cl-reveal.cl-pending {
    opacity: 0; transform: translateY(24px);
}
.cl-inicio .cl-reveal.cl-animated {
    transition: opacity .75s ease, transform .75s ease;
    transition-delay: var(--delay, 0ms);
}
@media(max-width:800px) {
    .cl-inicio .split { grid-template-columns: 1fr; gap: 30px; }
    .cl-inicio .cards { grid-template-columns: 1fr; }
    .cl-inicio .section { padding: 50px 0; }
    .cl-inicio .lead { font-size: 16px; }
}
@media(max-width:480px) {
    .cl-inicio .steps { grid-template-columns: 1fr; gap: 20px; }
    .cl-inicio .panel { padding: 20px; }
    .stApp:has(.st-key-inicio) .communitylab-brand { font-size: 1.25rem; }
}
@media(prefers-reduced-motion:reduce) {
    .cl-inicio .scroll-cue { animation: none; }
    .cl-inicio .cl-reveal.cl-animated { transition: none; }
    .cl-inicio .cl-reveal.cl-pending { opacity: 1; transform: none; }
}
</style>
"""

ANIMACION = """
<script>
(() => {
    const root = document.querySelector('.st-key-inicio');
    if (!root) return;
    if (window.clInicioCleanup) window.clInicioCleanup();
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const cover = root.querySelector('.st-key-inicio_portada');
    const main = root.closest('[data-testid="stMain"]');
    const sizeCover = () => {
        if (!cover || !main) return;
        const top = cover.getBoundingClientRect().top + main.scrollTop;
        cover.style.setProperty('--inicio-top', Math.max(0, top) + 'px');
    };
    sizeCover();
    const resize = new ResizeObserver(sizeCover);
    resize.observe(document.documentElement);
    const brand = document.querySelector('.communitylab-brand');
    const navigation = document.querySelector('[data-testid="stRadio"]');
    if (brand) resize.observe(brand);
    if (navigation) resize.observe(navigation);
    let observer;
    const showAll = () => root.querySelectorAll('.cl-pending').forEach(
        el => el.classList.remove('cl-pending'));
    const configure = () => {
        if (observer) observer.disconnect();
        showAll();
        if (media.matches || !('IntersectionObserver' in window)) return;
        observer = new IntersectionObserver(entries => entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.remove('cl-pending');
                observer.unobserve(entry.target);
            }
        }), {threshold: .12});
        root.querySelectorAll('.cl-reveal').forEach(el => {
            el.classList.add('cl-animated');
            if (el.getBoundingClientRect().top >= innerHeight) {
                el.classList.add('cl-pending');
                observer.observe(el);
            }
        });
    };
    configure();
    media.addEventListener('change', configure);
    const removal = new MutationObserver(() => {
        if (!root.isConnected) window.clInicioCleanup();
    });
    removal.observe(root.parentNode, {childList: true});
    window.clInicioCleanup = () => {
        if (observer) observer.disconnect();
        removal.disconnect();
        resize.disconnect();
        media.removeEventListener('change', configure);
        showAll();
        delete window.clInicioCleanup;
    };
})();
</script>
"""


def _html(contenido: str) -> None:
    st.html(f'<div class="cl-inicio">{contenido}</div>')


def render(*, ir_a: Callable[[str], None]) -> None:
    with st.container(key="inicio"):
        st.html(ESTILO)
        with st.container(key="inicio_portada"):
            _html("""
        <section class="hero" aria-label="Bienvenida">
          <div class="eyebrow">Escucha · Comprende · Crea</div>
          <h1>De lo que se dice.<br><em>A lo que importa.</em></h1>
          <p class="lead">Encuentra las historias de tu comunidad y conviértelas
          en contenido con sentido. Todo empieza con una pregunta.</p>
        </section>
            """)
            with st.container(key="inicio_hero_botones", horizontal=True):
                st.button("Conversar con el agente ↗", type="primary",
                          key="inicio_nav_agente", on_click=ir_a, args=("Agente",))
                st.button("Explorar plantillas", key="inicio_nav_plantillas",
                          on_click=ir_a, args=("Plantillas",))
            _html('<a class="scroll-cue" href="#inicio-recorrido" '
                  'aria-label="Descubre CommunityLab, baja al recorrido">↓</a>')
        _html("""
        <section class="section agent-scene" id="inicio-recorrido">
          <div class="split">
            <div>
              <div class="eyebrow cl-reveal">Así comienza</div>
              <h2 class="cl-reveal">Pregunta.<br>Encuentra una idea.</h2>
              <p class="lead cl-reveal">Un agente para explorar lo que tu comunidad
              está contando, sin perder de vista de dónde viene.</p>
            </div>
            <div class="panel chat" aria-label="Conversación ilustrativa">
              <div class="label">Conversación ilustrativa</div>
              <div class="question cl-reveal">Necesitamos presentar CommunityLab.
              ¿Por dónde empezamos?</div>
              <div class="answer cl-reveal" style="--delay:100ms"><p>Por esta conversación.
              Tú traes la pregunta; yo te ayudo a convertirla en una historia.</p></div>
              <div class="question cl-reveal" style="--delay:200ms">¿Y el titular?</div>
              <div class="answer cl-reveal" style="--delay:300ms"><p>De lo que se dice.
              <strong>A lo que importa.</strong></p></div>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="split">
            <div>
              <div class="eyebrow cl-reveal">01 / Comprender</div>
              <h2 class="cl-reveal">Menos ruido.<br>Más contexto.</h2>
              <p class="cl-reveal">Pregunta por los temas, sentimientos y experiencias
              de la comunidad. El agente consulta los datos disponibles y acompaña
              sus respuestas con fuentes.</p>
              <div class="pills cl-reveal"><span class="pill">Temas y frecuencias</span>
              <span class="pill">Sentimiento</span>
              <span class="pill">Historias de la comunidad</span></div>
            </div>
            <div class="panel cl-reveal">
              <div class="label">Un hallazgo / Datos de ejemplo</div>
              <h3>¿De qué estamos hablando?</h3>
              <div class="metric"><span>Aprendizaje</span><span>8 mensajes</span></div>
              <div class="track"><span style="width:80%"></span></div>
              <div class="metric"><span>Comunidad</span><span>6 mensajes</span></div>
              <div class="track green"><span style="width:60%"></span></div>
              <div class="metric"><span>Empleabilidad</span><span>4 mensajes</span></div>
              <div class="track"><span style="width:40%"></span></div>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="section-head">
            <div class="eyebrow cl-reveal">02 / Crear</div>
            <h2 class="cl-reveal">Tres formas de empezar.<br>Una comunidad detrás.</h2>
            <p class="cl-reveal">Tres ejemplos del catálogo de nueve plantillas.
            Contenido preparado para revisión, no publicaciones automáticas.</p>
          </div>
          <div class="cards">
            <article class="card cl-reveal"><span class="tag">LINKEDIN / HISTORIAS</span>
              <h3>Una experiencia<br>que merece contarse.</h3>
              <p>Un post profesional a partir de comentarios positivos,
              con una invitación a compartir experiencias.</p>
              <div class="sample">«Cada proyecto tiene una historia.
              Hoy escuchamos a quienes dieron su siguiente paso…»</div></article>
            <article class="card cl-reveal" style="--delay:100ms">
              <span class="tag">INSTAGRAM / COMUNIDAD</span>
              <h3>Más cerca de<br>quienes participan.</h3>
              <p>Un texto cercano para destacar voces de la comunidad.
              Tú aportas la imagen o el video.</p>
              <div class="sample">«Un logro, una pregunta, una mano que ayuda.
              ¿Qué te llevas de esta comunidad?»</div></article>
            <article class="card cl-reveal" style="--delay:200ms">
              <span class="tag">NEWSLETTER / SÍNTESIS</span>
              <h3>Lo importante,<br>en pocas líneas.</h3>
              <p>Una sección con titular, temas destacados y fuentes
              para tu siguiente boletín.</p>
              <div class="sample"><strong>Voces que nos hacen crecer</strong><br>
              Una mirada breve a los aprendizajes y experiencias compartidos.</div></article>
          </div>
        </section>
        """)
        st.button("Ver las nueve plantillas ↗", key="inicio_catalogo",
                  on_click=ir_a, args=("Plantillas",))
        _html("""
        <section class="section">
          <div class="split">
            <div class="files">
              <div class="file cl-reveal"><span class="ext">CSV</span>
              <div>Comentarios de un evento</div></div>
              <div class="file cl-reveal" style="--delay:100ms"><span class="ext">JSON</span>
              <div>Mensajes de tu comunidad</div></div>
              <div class="file cl-reveal" style="--delay:200ms"><span class="ext">TXT</span>
              <div>Notas y comentarios</div></div>
            </div>
            <div>
              <div class="eyebrow cl-reveal">03 / Ampliar</div>
              <h2 class="cl-reveal">Tus preguntas.<br>También tus archivos.</h2>
              <p class="cl-reveal">Añade JSON, CSV o TXT con el clip del chat.
              El agente puede combinarlos con la información disponible de la comunidad
              para responder en esa sesión.</p>
              <p class="cl-reveal">Los adjuntos no se publican en la base de la comunidad.
              Su contenido relevante se envía al servicio de IA al consultar.</p>
            </div>
          </div>
        </section>
        <section class="section">
          <div class="section-head">
            <div class="eyebrow cl-reveal">04 / Decidir</div>
            <h2 class="cl-reveal">La última palabra<br>siempre es tuya.</h2>
            <p class="cl-reveal">El agente propone. Tú revisas las fuentes, ajustas
            el contenido y confirmas la publicación en la plataforma de destino.</p>
          </div>
          <div class="steps">
            <div class="step cl-reveal"><span class="step-number">01</span>
              <h3>Revisa</h3><p>Consulta las fuentes y los avisos de verificación.
              Una respuesta de IA no equivale a una aprobación editorial.</p></div>
            <div class="step cl-reveal" style="--delay:100ms"><span class="step-number">02</span>
              <h3>Hazlo tuyo</h3><p>Elige el modelo y el estilo de redacción del chat.
              Copia el contenido y adáptalo en tu editor antes de compartir.</p></div>
            <div class="step cl-reveal" style="--delay:200ms"><span class="step-number">03</span>
              <h3>Comparte</h3><p>Copia o abre el destino compatible.
              No se conectan cuentas ni se publica automáticamente.</p></div>
          </div>
        </section>
        <section class="closing">
          <div class="eyebrow cl-reveal">De escuchar a construir</div>
          <h2 class="cl-reveal">La próxima buena idea<br>puede estar en tu comunidad.</h2>
          <p class="cl-reveal">Empieza con una pregunta. Explora con contexto.
          Comparte con criterio.</p>
        </section>
        """)
        with st.container(key="inicio_cierre_botones", horizontal=True):
            st.button("Abrir el agente ↗", type="primary",
                      key="inicio_abrir_agente", on_click=ir_a, args=("Agente",))
            st.button("Conocer el recorrido", key="inicio_ayuda",
                      on_click=ir_a, args=("Ayuda",))
        with st.container(key="inicio_footer"):
            marca, enlaces, contacto = st.columns([1.4, 1, 1])
            with marca:
                _html(
                    f'<div class="footer-brand">{tema.espiral()}CommunityLab</div>'
                )
            with enlaces:
                st.markdown("**Explora**")
                for pagina in ("Agente", "Análisis", "Plantillas", "Ayuda"):
                    st.button(pagina, key=f"inicio_footer_{pagina}", type="tertiary",
                              on_click=ir_a, args=(pagina,))
            with contacto:
                st.markdown("**Hablemos**")
                with st.expander("Contacto"):
                    st.write("Contacta al administrador de tu instalación de "
                             "CommunityLab para soporte y solicitudes sobre tus datos.")
                with st.expander("Sobre tus datos"):
                    st.write("Los archivos adjuntos se usan en tu sesión y no se "
                             "publican en la base de la comunidad. Al consultar, "
                             "su contenido relevante se envía al servicio de IA.")
            _html(
                '<div class="footer-bottom" role="contentinfo">'
                f"<span>© {datetime.now().year} CommunityLab. "
                "Todos los derechos reservados.</span>"
                "</div>"
            )
        st.html(ANIMACION, unsafe_allow_javascript=True)

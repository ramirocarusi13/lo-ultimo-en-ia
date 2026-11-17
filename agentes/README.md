# Redacción de agentes de @loultimoenia

Cada post nuevo lo arma y lo revisa un equipo de agentes, cada uno con un rol. Corren como
subagentes de la tarea programada de Claude (con la suscripción, sin API paga). El "jefe de
redacción" es la tarea programada: lanza a los agentes, junta sus informes, aplica los
cambios y decide.

| Agente | Cuándo | Qué hace | Modelo |
|---|---|---|---|
| `analista-tendencias` | después de `pick` | ordena las 5 candidatas: importancia, potencial de compartirse, si tiene video, equilibrio con los posts recientes | sonnet |
| `verificador` | después del borrador | cada dato del titular, slides, caption y guion contra las notas | opus |
| `editor-estilo` | después del borrador | reglas de `prompts/redaccion.md`, ortografía, largos, tono | sonnet |
| `revisor-legal` | después del borrador | rumores, acusaciones, derechos de fotos y videos, reglas de Instagram | sonnet |
| `guionista-reels` | después del borrador | gancho y ritmo del guion del Reel para que lo miren hasta el final | sonnet |
| `cazador-videos` | después del borrador | busca videos REALES de la noticia con licencia libre (YouTube CC del autor, Wikimedia Commons, NASA) y los baja para el Reel | sonnet |
| `productor` | después del armado | decide el formato: REEL (si la noticia se ve y hay video real), CARRUSEL o AMBOS | sonnet |
| `director-arte` | después del armado | los 4 slides: legibilidad, fotos correctas, terceros, recortes | sonnet |
| `editor-video` | después del armado | el Reel: clips, sincronía con la voz, textos, zonas seguras | sonnet |

Los 5 de "después del borrador" corren en paralelo, y los 3 de "después del armado" también.
Los Reels son solo con video real; sin video, la noticia sale como carrusel. El video sigue
a la voz: cuando nombra a alguien con clip propio (Trump, Elon Musk…) se lo ve a él; si no,
al protagonista. Nada de videos de relleno.
Cada agente devuelve un informe corto con VEREDICTO (OK / CAMBIOS / DESCARTAR), puntaje y
cambios concretos. Los informes se juntan en `posts/<id>/informe_agentes.md`, que se manda
al usuario junto con el post.

Videos: solo con licencia que permite reutilizarlos y citando al autor en el caption. Nunca
de cuentas de terceros (X/Twitter, TikTok, Instagram) ni de YouTube con licencia estándar.
Si el video oficial de la noticia tiene derechos, el caption puede decir dónde verlo.

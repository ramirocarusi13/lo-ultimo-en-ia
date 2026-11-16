# Redacción de agentes de @loultimoenia

Cada post nuevo lo revisa un equipo de agentes, cada uno con un rol. Corren como subagentes
de la tarea programada de Claude (con la suscripción, sin API paga). El "jefe de redacción"
es la tarea programada: lanza a los agentes, junta sus informes, aplica los cambios y decide.

| Agente | Cuándo | Qué analiza | Modelo |
|---|---|---|---|
| `analista-tendencias` | después de `pick` | las 5 candidatas: importancia, potencial de compartirse, equilibrio con los posts recientes | sonnet |
| `verificador` | después del borrador | cada dato del titular, slides, caption y guion del Reel contra las notas | opus |
| `editor-estilo` | después del borrador | reglas de `prompts/redaccion.md`, ortografía, largos, gancho, guion para el oído | sonnet |
| `revisor-legal` | después del borrador | rumores, acusaciones, licencias de fotos, reglas de Instagram, originalidad | sonnet |
| `director-arte` | después del armado | slides y cuadros del Reel: legibilidad, fotos correctas, terceros, recortes | sonnet |

Los 3 del borrador corren en paralelo. Cada agente devuelve un informe con el formato:

```
VEREDICTO: OK | CAMBIOS | DESCARTAR
PUNTAJE: 1-10
CAMBIOS:
- <campo>: "<texto actual>" -> "<texto propuesto>"  (motivo)
NOTAS: <1-3 líneas>
```

Los informes se juntan en `posts/<id>/informe_agentes.md`, que se manda al usuario junto
con el post para que vea qué se revisó.

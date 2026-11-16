Cómo publicar a mano un post ya armado en @loultimoenia desde el Chrome del usuario
(con la extensión Claude in Chrome). Usalo SOLO si el usuario lo pide explícitamente en la
conversación ("publicalo", "subilo"), nunca por tu cuenta.

1. list_connected_browsers y elegí el navegador donde Instagram tiene la sesión de
   loultimoenia (si hay varios, probá; el bueno muestra el perfil sin pedir login).
   tabs_context_mcp con createIfEmpty y navegá a https://www.instagram.com/.
   Si pide iniciar sesión, pedile al usuario que inicie sesión él (nunca escribas contraseñas).
2. Clic en "Nueva publicación / Crear" → "Publicación". Buscá el file-input del diálogo y subí
   con file_upload los 4 archivos posts\<id>\slide_1.jpg … slide_4.jpg (en ese orden).
3. Recorte: ícono de recorte abajo a la izquierda → "4:5". "Siguiente" dos veces.
4. Texto: clic en "Agrega una descripción…" y escribí el contenido de posts\<id>\caption.txt.
   Cerrá las sugerencias de hashtags haciendo clic en el nombre de la cuenta.
5. "Agregar etiqueta de IA": activala SOLO si alguna imagen es una foto REALISTA generada con
   IA. Con fotos reales de Wikimedia o ilustraciones 3D (no realistas), dejala apagada.
6. Si la pestaña no responde (captura en negro o "renderer frozen"), pedile al usuario que
   deje esa pestaña de Chrome seleccionada y visible.
7. "Compartir". Esperá "Se compartió tu publicación", abrí el perfil y verificá.
8. Después: si posts\pending.json es de este <id>, borralo y subí el cambio:
   git rm posts/pending.json; git commit -m "Publicado a mano <id>"; git push

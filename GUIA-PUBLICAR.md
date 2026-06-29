# 🎈 Cómo publicar tu Invitación Baby Shower (gratis)

Sigue estos 3 pasos. Al final tendrás un **link** para enviar a tus invitados,
tipo: `https://invitacion-baby-shower.onrender.com`

---

## PASO 1 · Subir el proyecto a GitHub

GitHub es donde se guarda el código para que Render lo pueda publicar.

1. Entra a **https://github.com** e inicia sesión (o crea una cuenta gratis).
2. Arriba a la derecha: botón **+** → **New repository**.
3. En *Repository name* escribe: `invitacion-baby-shower`
4. Déjalo en **Public**. **NO** marques "Add a README".
5. Clic en **Create repository**.
6. En la página que aparece, busca el enlace **"uploading an existing file"**.
7. **Arrastra TODA la carpeta** `Baby` (todos los archivos) a esa ventana.
   - Asegúrate de incluir las carpetas `static` y `templates`.
8. Abajo, clic en **Commit changes**.

✅ Listo: tu código ya está en GitHub.

---

## PASO 2 · Publicar en Render (gratis)

Render toma tu código y lo pone en internet, con base de datos incluida.

1. Entra a **https://render.com** → **Get Started** → inicia sesión **con GitHub**
   (botón "GitHub"). Autoriza el acceso.
2. Arriba: botón **New +** → elige **Blueprint**.
3. Selecciona el repositorio **invitacion-baby-shower** → **Connect**.
4. Render leerá el archivo `render.yaml` y mostrará lo que va a crear
   (la web + la base de datos). 
5. Te pedirá el valor de **HOST_KEY**: escribe tu **clave secreta de anfitriona**
   (la que usarás para agregar/eliminar regalos). Ej: `vanessa2026`.
6. Clic en **Apply**.
7. Espera ~3–5 minutos mientras se construye (verás "Live" en verde al terminar).

✅ Render te dará tu link arriba, algo como
`https://invitacion-baby-shower.onrender.com`

> Nota: en el plan gratis, la web "se duerme" si nadie entra por un rato.
> La primera visita después de dormir tarda ~30 segundos en despertar. Es normal.
> **Tus reservas NO se pierden** porque se guardan en la base de datos. 👍

---

## PASO 3 · Preparar y compartir

1. Abre tu link y toca **"⚙︎ Soy la anfitriona"** → escribe tu HOST_KEY.
2. Agrega/edita los regalos que quieras (y elimina los de ejemplo).
3. Copia el link y envíalo por **WhatsApp** a tus invitados. ¡Eso es todo! 💙

---

## ✏️ Cambiar nombre del bebé, fecha y lugar

En Render → tu servicio → pestaña **Environment** → edita estas variables y
guarda (la web se reinicia sola):

| Variable        | Ejemplo                              |
|-----------------|--------------------------------------|
| `EVENT_BABY`    | Bienvenido, Mateo                    |
| `EVENT_DATE`    | Sábado 15 de Agosto · 4:00 PM        |
| `EVENT_PLACE`   | Salón Las Nubes · Quito              |
| `EVENT_SUBTITLE`| Aparta tu regalo y evitemos repetidos|
| `HOST_KEY`      | tu clave secreta                     |

---

### ¿Prefieres que te ayude con el Paso 1?
Puedo instalarte la herramienta de GitHub y subir el código por ti
(solo tendrías que iniciar sesión una vez). Solo dime. 🙂

# HANDOFF: cómo continuar IsaWard (con cualquier cuenta de Claude)

Este archivo es el "traspaso". Quien lo lea (persona o Claude) debe poder seguir el proyecto
sin haber visto la conversación anterior. **Léelo completo y luego lee `ROADMAP.md`.**

## 1. Qué es IsaWard

Un procesador de texto tipo Word, gratuito, para PCs de pocos recursos, que se compila a `.exe`
y se publica en GitHub. Lo usan dos personas sin presupuesto para Office. El usuario habla español
y no es programador: los textos de la interfaz, los mensajes de error y las guías van **en español
sencillo**, y las instrucciones para él deben ser pasos cortos.

Requisitos pedidos: .exe compilable, interfaz bonita pero simple, funciones equivalentes a Word,
guía para los botones que solo tienen dibujo, abrir los formatos que abre Word, poder crear y guardar
archivos en el PC, y desarrollo **por segmentos** para poder cambiar de cuenta cuando se acaben los tokens.

## 2. Decisiones técnicas (y por qué)

- **Python + PySide6 (Qt 6).** `QTextDocument` ya trae tablas, listas, imágenes, deshacer, HTML, Markdown,
  ODT (escritura) e impresión/PDF. Tkinter es más liviano pero habría que escribir todo el texto enriquecido a mano.
  Costo: Qt 6 exige Windows 10/11 de 64 bits (no corre en Windows 7/8). Si resulta que la PC de la amiga
  tiene Windows 7, hay que replantear la tecnología (PyQt5/PySide2 o Tkinter).
- **HTML como formato puente** para `.docx`:
  `abrir: docx_to_html() → QTextDocument.setHtml()`  y  `guardar: QTextDocument.toHtml() → html_to_docx()`.
  Todo `isaward/formats/docx_io.py` es Python puro (sin Qt) y por eso tiene pruebas automáticas reales.
- **Iconos dibujados por código** (`icon_defs.py` son solo datos; `icons.py` los pinta con QPainter).
  Cero archivos de imagen que empaquetar. `tools/preview_icons.py` los renderiza con Pillow para revisarlos a ojo.
- **Catálogo único de herramientas** (`tools.py`): de ahí salen botones, tooltips y la Guía (F1). Para agregar
  una herramienta: icono en `icon_defs.py` + fila en `tools.py` + acción en `main_window.py`.
- **Ligero a propósito:** estilo plano (sin sombras ni animaciones), contador de palabras con retardo (300 ms),
  imágenes reducidas a 1600 px al insertarlas, PyInstaller en modo carpeta (abre más rápido que un solo archivo).
- **Las hojas son reales** (segmento 3): el `QTextDocument` del editor tiene `pageSize` finito y los márgenes de la hoja son los
  márgenes del marco raíz; así Qt reparte el texto en hojas (igual que al imprimir). `QTextEdit` vuelve a poner la hoja "sin
  fin" cuando cambia de tamaño, por eso `PageEditor.resizeEvent` la restituye. Encima del texto, `paintEvent` dibuja la
  franja gris entre hojas y el encabezado/pie (`pagedraw.py`, compartido con la impresión). El HTML para guardar se saca de un
  **clon** del documento (`clean_html`) porque, con márgenes por lado, Qt envolvería todo en una tabla. Si las hojas fallaran
  en algún equipo: `PAGINATE = False` en `config.py` vuelve a la hoja continua.
- **La configuración de la hoja (`PageSetup`) es lógica pura** (`pagesetup.py`) y viaja con el documento: docx, rtf, odt, pdf
  (lectura del tamaño) y copia de seguridad. Los lectores nuevos devuelven `(html, imágenes, PageSetup)` (`read_docx`, `read_rtf`,
  `read_odt`, `read_pdf`); `xxx_to_html` sigue existiendo y devuelve solo los dos primeros.
- **La guía se genera desde los datos** (`tools.py` + `howto.py`): botones, tooltips, menús y la ventana F1 salen de ahí.
- **Todos los lectores devuelven el mismo HTML** (`formats/htmlout.py`) y los escritores parten del mismo modelo
  (`parse_html` en `docx_io.py`). Un formato nuevo = un módulo en `formats/` con `xxx_to_html(path) -> (html, imágenes)`
  y, si se puede guardar, `html_to_xxx(html, imágenes, path)`. Sin Qt, con pruebas.
- **Se detecta el formato por el contenido** (`formats/sniff.py`), no por la extensión.
- **Copia de seguridad** (`recovery.py`): HTML + imágenes en la carpeta de datos del usuario; se borra al guardar o cerrar bien.
- **Hoja continua**, no paginada: `QTextEdit` no pagina en pantalla. El ancho de la hoja es el de una A4 a
  96 ppp (794 px) con márgenes de 96 px. La paginación visual es del segmento 3.

## 3. Mapa de archivos

```
run_isaward.py            lanzador (también lo usa PyInstaller)
run.bat / build.bat       ejecutar desde código / compilar el .exe
.github/workflows/        compila el .exe en GitHub y lo publica en Releases con etiquetas v*
isaward/
  app.py                  QApplication, tema, captura de errores (ventana + IsaWard-errores.log)
  main_window.py          menús, barras, abrir/guardar, recientes, autoguardado, recuperación, estado de botones
  editor.py               PageEditor(QTextEdit): todos los comandos de formato/insertar/tablas
  dialogs.py              Buscar y reemplazar, Insertar tabla, Guía de herramientas
  fileio.py               abrir (por contenido real) / guardar por extensión, imprimir, exportar PDF, UserMessage
  recent.py / recovery.py lista de recientes / copia automática (lógica pura, con pruebas)
  pagesetup.py            hoja: tamaño, orientación, márgenes, encabezado, pie, números (lógica pura, con pruebas)
  pagedraw.py             dibuja encabezado y pie (lo usan la pantalla y la impresión)
  howto.py                recetas «¿Cómo hago…?» de la guía (datos puros)
  datefmt.py / symbols.py fechas en español / lista de símbolos (datos puros, con pruebas)
  formats/                (todo Python puro, SIN Qt, con pruebas)
    htmlout.py            piezas comunes del HTML que lee Qt (esc, span, para, wrap, ListStack)
    docx_io.py            DOCX ⇄ HTML (+ .dotx/.docm) y el modelo `parse_html` que usan los escritores
    odt_io.py             ODT → HTML
    rtf_io.py             RTF ⇄ HTML (lector con tabla de colores/fuentes/listas/tablas; escritor desde el modelo)
    ole.py + doc_io.py    contenedor OLE2 mínimo + .doc de Word 97-2003 → HTML (solo texto)
    pdf_io.py             PDF → HTML (solo texto, con pypdf)
    sniff.py              detecta el formato real por los primeros bytes
  tools.py                catálogo de herramientas: nombre, ayuda corta, atajo, DÓNDE ESTÁ y MÁS INFORMACIÓN de cada una
  icon_defs.py / icons.py iconos como datos / su dibujo con Qt
  theme.py / config.py    colores y QSS / constantes (fuente por defecto, medidas de la hoja, autoguardado)
tests/                    pruebas sin Qt: python -m unittest discover tests   (74 pruebas)
tests/data/               muestra.* y hoja.* (docx/odt/rtf/doc/pdf) creados con LibreOffice (tools/make_fixtures.py)
tools/                    preview_icons.py (hoja de iconos y .ico), empaquetar.py (zip limpio), make_fixtures.py
```

## 4. Estado actual (ver detalle en ROADMAP.md)

Segmentos 1 a 3 escritos (el usuario ya probó los segmentos 1 y 2 en Windows y dijo que funcionan bien).
**Verificado de verdad:** todo `isaward/formats/`, `pagesetup.py`, `recent.py`, `recovery.py`, `datefmt.py`, `symbols.py` y
la coherencia de la guía (74 pruebas automáticas); los `.docx`/`.rtf` con hoja horizontal, márgenes, encabezado y "Página X de Y" que
escribe IsaWard se abrieron en LibreOffice y se vieron correctos, y se leen de vuelta idénticos; los `.docx` y `.rtf` que escribe IsaWard se abrieron y se vieron bien en LibreOffice;
los lectores de ODT/RTF/DOC/PDF se probaron con archivos reales que LibreOffice generó (y con RTF/ODT escritos a mano
en el estilo de Word); los iconos se revisaron renderizados con Pillow.
**NO verificado:** la ventana. En el entorno donde se escribió no existía PySide6 ni había internet, así que solo se
comprobó que el código compila y que se construye y ejecuta contra una maqueta de Qt (atrapa errores de nombres,
no de uso de la API real). **El primer paso de cualquier sesión nueva es la prueba manual (`PRUEBA_MANUAL.md`)
o, si tienes Qt disponible, arrancar la app y corregir lo que falle.** Tampoco se ha probado con un `.docx`/`.rtf`
hecho por Microsoft Word real (solo LibreOffice, python-docx y odfpy).

### Segmento 3 sin probar en Windows (lo más delicado del proyecto; probar primero esto)
- **Hojas en el editor** (`editor.py`: `_apply_geometry`, `_enforce_page_size`, `resizeEvent`, `_paint_page_chrome`):
  se asume que `QTextDocumentLayout` usa los márgenes superior/inferior del marco raíz como márgenes de CADA hoja cuando
  `pageSize` es finito (es lo que hace `QTextDocument.print`). Si se ven mal, probar `PAGINATE = False`.
- **Cambiar la hoja reinicia el historial de Deshacer** (`apply_page_layout` desactiva y reactiva el deshacer).
- **Imprimir/PDF** (`fileio.py`): sin encabezado/pie usa `doc.print_(printer)` (Qt escala la hoja del documento a la del papel);
  con encabezado/pie usa `_print_with_header_footer` (bucle propio por hojas). Probar ambos y en horizontal.
- **Ventanas nuevas** (`dialogs.py`): `PageSetupDialog` (se actualizan entre sí tamaño, orientación, medidas y márgenes con una
  bandera `_busy` para evitar rebotes), `HeaderFooterDialog`, `ParagraphDialog`, `SymbolDialog`, `DateDialog`, `GuideDialog`.
- Barra de 3 filas con nombres junto a los dibujos (`ToolButtonTextBesideIcon`); puede desbordar en ventanas angostas.

### Puntos donde es más probable que haya que ajustar (API de Qt usada sin poder probarla)
- `editor.py`: `toggle_list` / `change_indent` (listas anidadas), `insert_page_break` y
  `_drop_inherited_page_break`, `apply_paragraph_style` (nivel de título con `setHeadingLevel`),
  `html_and_images` (obtención de imágenes con `document.resource`).
- `main_window.py`: `_sync_state` (lectura de `fontFamilies()`, alineación y lista bajo el cursor), el menú
  "Abrir reciente" (`QSettings` con listas: un solo elemento vuelve como `str`, ya contemplado),
  `_autosave` / `_offer_recovery` (`QStandardPaths.AppDataLocation`).
- `fileio.py::print_document` (usa `QTextDocument.clone()` con margen 0 para imprimir y exportar PDF).
- `dialogs.py::FindReplaceDialog` (banderas `QTextDocument.FindFlag`).
- Qué HTML exacto entrega `QTextDocument.toHtml()` en la versión instalada de PySide6: `docx_io.parse_html` se probó con
  HTML escrito a mano con la forma conocida de Qt; si algo no se guarda bien, compara con el HTML real (`print(doc.toHtml())`).

### Límites conocidos
- **Zoom**: no existe. `QTextEdit` no escala bien texto con tamaño explícito, imágenes ni espacios (`zoomIn` solo cambia la fuente
  por defecto). «Vista previa de impresión» sí tiene zoom. Ver ROADMAP (ideas sueltas).
- **Encabezado/pie**: tres zonas (izquierda, centro, derecha) de una línea cada una, mismo texto en todas las hojas (menos «primera
  hoja distinta»). No hay encabezados distintos en pares/impares ni por secciones. Se dibujan sobre el margen, no se editan en la hoja.
- Las hojas en pantalla suponen 96 ppp; la separación entre hojas es una franja dibujada (el texto salta de hoja según Qt).
- **docx:** las listas numeradas de dos listas separadas continúan la numeración (estilos "List Number"); no se conservan
  formatos de viñeta/numeración (a, b, c · i, ii) ni el ancho de columnas; títulos con color negro explícito; sin
  encabezados/pies, notas al pie, comentarios, cuadros de texto, formas ni control de cambios; tablas anidadas se aplanan.
- **rtf (escritura):** las listas se escriben como texto con sangría francesa, no como listas reales.
- **doc:** solo texto. Las celdas con varios párrafos se separan y una celda vacía en la primera fila puede confundirse con
  el fin de fila (el formato binario necesita leer las propiedades de párrafo, ver ROADMAP).
- **pdf:** solo texto; los párrafos se reconstruyen con una heurística (líneas casi llenas y siguiente en minúscula);
  sin columnas, tablas ni imágenes; los escaneados no se pueden leer.
- Imágenes EMF/WMF no se leen. Imágenes pegadas desde el portapapeles pueden no llegar al .docx (nombres de recurso de Qt).
- El salto de página no se dibuja en pantalla (sí al imprimir/exportar y en Word).

### Lecciones del segmento 2 (para no repetir errores)
- Probar los lectores con **archivos reales de otro programa** y con el mismo documento en varios formatos
  (`SameContentInEveryFormat`) destapó dos errores del segmento 1 que las pruebas "de ida y vuelta" no veían.
- **Medir rendimiento** con un documento grande: un recorrido que consultaba estilos por cada trozo de texto tardaba
  208 s en 100 páginas (ahora 2,5 s). Hay una prueba de regresión; en PCs lentas esto importa mucho.
- Lo que escribe LibreOffice no es lo que escribe Word (por ejemplo separa listas anidadas): cubrir también el estilo de Word
  con fragmentos escritos a mano.

## 5. Reglas de trabajo por segmentos

1. Lee este archivo y `ROADMAP.md`. Corre `python -m unittest discover tests` (debe pasar todo).
2. Trabaja **solo el siguiente segmento pendiente**. No mezcles segmentos ni reescribas lo que ya funciona.
3. Todo código de lectura/escritura de formatos va en `isaward/formats/`, **sin importar Qt**, con pruebas en `tests/`.
   Así se puede verificar aunque no haya pantalla. Para comparar con un programa real, convierte con LibreOffice
   (`soffice --headless --convert-to pdf archivo.docx`) y mira el resultado. Los archivos de muestra de `tests/data/`
   se regeneran con `python tools/make_fixtures.py` (necesita LibreOffice).
4. Textos para el usuario: español, frases cortas, verbos activos, sin jerga ("No pude guardar…", no "Excepción de E/S").
5. Enums de Qt siempre con su nombre completo (`Qt.AlignmentFlag.AlignCenter`, no `Qt.AlignCenter`).
   Para valores numéricos que aceptan `int` (peso de fuente, tipo de interlineado) usa enteros.
6. Rendimiento: nada que recorra todo el documento en cada pulsación de tecla; sin animaciones.
7. Al terminar: marca el ROADMAP (✅ / 🟡), añade una entrada abajo en el **Registro de sesiones**, corre las pruebas
   y entrega el proyecto completo como `.zip` (`python tools/empaquetar.py`).
8. **LA GUÍA SIEMPRE AL DÍA (regla del usuario).** Toda función nueva o cambiada debe quedar explicada en la guía (F1) en la
   misma sesión: fila en `tools.py` con `help`, `where` y `more` (para qué sirve y cómo se usa, en español sencillo), icono en
   `icon_defs.py`, y una receta en `howto.py` si ayuda a una tarea común. Las pruebas (`tests/test_catalog.py`) fallan si falta.
   Si un menú, botón o ventana cambia de lugar o de nombre, actualizar `where` y las recetas. Mejorar la guía para que sea más
   intuitiva es parte del trabajo, no un extra.
9. **Que todo se entienda «con manzanitas»**: nombres de botones en español claro, tooltips con una frase útil, mensajes de error
   que digan qué hacer, ventanas con una explicación corta y un botón «Ayuda» que abra la guía en esa herramienta.
10. Si el proyecto no cabe en lo que te queda de sesión, **para en un punto limpio** (que todo compile y las pruebas
   pasen), actualiza el ROADMAP con lo que quedó a medias y entrega el zip. Mejor medio segmento sólido que uno entero roto.

## 5b. Si el usuario te manda el proyecto y pregunta «¿cómo se hace tal cosa?»

El usuario no conoce bien Word y no puede buscar en internet (es una app solo para él y su amiga). Cuando pregunte cómo hacer algo:
1. Busca la respuesta en `isaward/tools.py` (campos `where` y `more`) y en `isaward/howto.py` (recetas).
2. Respóndele con pasos cortos, usando los nombres EXACTOS de los botones y menús y diciendo en qué fila de la barra o menú están.
3. Si la guía no lo explica o la explicación es confusa, mira `main_window.py` para ver cómo se hace de verdad, respóndele y
   **agrega o mejora la receta/herramienta en la guía** (y entrégale el zip actualizado).
4. Si lo que pide no existe en el programa, dilo con claridad, di qué se puede hacer mientras tanto y anótalo en `ROADMAP.md`.

## 6. Cómo pasar el proyecto a otra cuenta de Claude

1. En la cuenta actual, pide el proyecto completo en `.zip` (o corre `python tools/empaquetar.py` en tu PC).
2. En la cuenta nueva, abre un chat con **ejecución de código / creación de archivos activada**, sube el `.zip`
   y pega este mensaje:

> Te paso el proyecto IsaWard (un procesador de texto tipo Word hecho con Python y PySide6, que se compila a .exe).
> Descomprime el zip, lee `HANDOFF.md` y `ROADMAP.md` completos antes de tocar nada, y corre
> `python -m unittest discover tests`. Después trabaja únicamente el siguiente segmento pendiente del ROADMAP,
> siguiendo las reglas de trabajo de HANDOFF.md. Si tengo errores de la prueba manual, te los pego aquí:
> arréglalos primero. Al terminar, actualiza ROADMAP.md y el Registro de sesiones, y entrégame el proyecto
> completo en un .zip. Háblame en español sencillo y dame pasos cortos.

3. Si hay errores al probar en Windows, pega el texto del error (o el contenido de `IsaWard-errores.log`) en ese mensaje.

## 7. Registro de sesiones

| # | Qué se hizo | Estado al cerrar |
|---|---|---|
| 1 | Segmento 1: estructura, conversión DOCX⇄HTML con pruebas, iconos, ventana completa, buscar/reemplazar, tablas, imágenes, archivos, PDF, compilación (.bat y GitHub Actions), documentación de traspaso. | Pruebas automáticas OK (12). Ventana sin ejecutar con Qt real: pendiente `PRUEBA_MANUAL.md`. |
| 2 | Segmento 2: lectores de ODT, RTF, DOC (texto) y PDF (texto); escritor RTF; plantillas .dotx/.docm; detección de formato por contenido; recientes; copia automática y recuperación; corrección de 2 errores del segmento 1 (resaltado al reabrir .docx y rendimiento de lectura). | Pruebas automáticas OK (39). Ventana sin ejecutar con Qt real: pendiente `PRUEBA_MANUAL.md` (pasos 1 a 30). |
| 3 | Segmento 3: hoja real (tamaño, orientación, márgenes) en editor y en docx/rtf/odt/pdf; encabezado, pie y números de página (campos reales en Word); hojas visibles, salto de página y hoja en blanco; impresión/PDF por hojas; ventanas Párrafo, Símbolo y Fecha; guía renovada (Más información, Dónde está, buscador, recetas, atajos) con pruebas que la mantienen completa; arreglo de rendimiento y de lectura en el segmento 2. No se hizo el zoom (explicado arriba). | Pruebas automáticas OK (74). Ventana sin ejecutar con Qt real: pendiente `PRUEBA_MANUAL.md` pasos 31 a 48. |

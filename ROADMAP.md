# Hoja de ruta de IsaWard

Se construye por **segmentos** pequeños y cerrados. Cada segmento termina con el proyecto funcionando
y con este archivo actualizado, así se puede retomar en cualquier momento (o con otra cuenta de Claude).

Leyenda: ✅ hecho · 🟡 hecho pero sin probar en Windows · ⬜ pendiente

## Segmento 1: base funcional ✅ (código) / 🟡 (ventana sin probar)
- ✅ Estructura del proyecto, `run.bat`, `build.bat`, GitHub Actions que compila el .exe
- ✅ Conversión DOCX ⇄ HTML con pruebas automáticas (`isaward/formats/docx_io.py`)
- ✅ Iconos dibujados por código + catálogo de herramientas + Guía de herramientas
- 🟡 Ventana: menús, dos barras de herramientas, hoja blanca sobre lienzo, barra de estado
- 🟡 Formato de texto y párrafo, listas con niveles, títulos, interlineado
- 🟡 Tablas (insertar, filas/columnas, combinar), imágenes, enlaces, línea, salto de página
- 🟡 Buscar y reemplazar, contador de palabras
- 🟡 Abrir/guardar: `.docx`, `.txt`, `.md`, `.html`; guardar `.odt`; exportar PDF; imprimir y vista previa
- 🟡 Arrastrar un archivo a la ventana para abrirlo; aviso de cambios sin guardar

## Segmento 2: abrir más formatos ✅ (código y pruebas) / 🟡 (ventana sin probar)
- ✅ Leer `.odt` (`formats/odt_io.py`): estilos con herencia, listas anidadas, tablas, imágenes, enlaces
- ✅ Leer y escribir `.rtf` (`formats/rtf_io.py`): Unicode, tablas con celdas combinadas, listas por tabla, imágenes PNG/JPEG, enlaces
- ✅ Leer `.doc` antiguo, **solo texto** (`formats/ole.py` + `formats/doc_io.py`, sin dependencias externas)
- ✅ Leer `.pdf`, **solo texto** (`formats/pdf_io.py`, con `pypdf`): rearma párrafos, viñetas y listas numeradas
- ✅ Abrir plantillas `.dotx` y archivos `.docm`/`.dotm`
- ✅ Detección del formato por el contenido (`formats/sniff.py`)
- ✅ Corregidos errores del segmento 1: el resaltado no se leía al reabrir un `.docx` de IsaWard; y leer `.docx` grandes
  era 80 veces más lento de lo debido (ahora hay una prueba de rendimiento)
- 🟡 Menú "Abrir reciente" (`recent.py`)
- 🟡 Copia automática cada 2 minutos y oferta de recuperación al arrancar (`recovery.py`)
- 🟡 Avisos al abrir `.doc`/`.pdf` (se abren solo como texto) y mensajes claros para archivos dañados o con contraseña

## Segmento 3: hojas, guía y ayuda ✅ (código y pruebas) / 🟡 (ventana sin probar)
- ✅ Configuración de la hoja (`pagesetup.py`): tamaño (A4, Carta, Oficio, Legal, A5, A3 o a medida), orientación, márgenes
- ✅ La hoja viaja en `.docx`, `.rtf` y `.odt` (lectura y escritura) y en la copia de seguridad; el PDF toma el tamaño de su primera página
- ✅ Encabezado, pie y números de página (con `{pagina}` y `{paginas}`), «primera hoja distinta» (portada). En `.docx` son campos reales de Word
- ✅ Ventana «Párrafo» (sangría de primera línea y francesa, espacios, interlineado), «Símbolo», «Fecha y hora»
- ✅ **Guía renovada**: «Más información» desplegable en cada herramienta, «Dónde está», buscador sin tildes, pestañas ¿Cómo hago…? (22 recetas) y Atajos. Pruebas que obligan a mantenerla completa
- 🟡 Hojas visibles en el editor (separación gris, «Página X de Y», encabezado/pie dibujados, hoja en blanco, salto de página visible)
- 🟡 Ventanas «Configurar página» (con dibujito), «Encabezado y pie», «Párrafo», «Símbolo», «Fecha»
- 🟡 Impresión y PDF por hojas, con encabezado, pie y números de página
- 🟡 Barra de herramientas de 3 filas (la tercera, con nombres junto a los dibujos)
- ⬜ **Zoom**: no se hizo. El componente de texto de Qt no escala de forma segura las letras con tamaño explícito, las imágenes y los espacios; en su lugar, «Vista previa de impresión» tiene zoom y varias hojas. Ver «Ideas sueltas»

## Segmento 4: lo que más piden en el colegio y la universidad ⬜
- ⬜ **Corrector ortográfico en español** (sin internet; subrayado rojo y menú con sugerencias)
- ⬜ **Tabla de contenido** automática (a partir de los Títulos) y panel de navegación por títulos
- ⬜ **Notas al pie** y referencias
- ⬜ Estilos (título, subtítulo, cita) que se puedan modificar
- ⬜ Copiar formato, «Ir a la página…», estadísticas del documento (palabras, hojas)
- ⬜ Imágenes: cambiar tamaño con el mouse y ajuste del texto alrededor
- ⬜ Tablas: bordes, sombreado y ancho de columnas
- ⬜ Numeración que se reinicia y otros tipos de viñeta (a, b, c / i, ii, iii)
- ⬜ Numeración de páginas en romanos y por secciones (índice y portada)

## Segmento 5: revisión ⬜
- ⬜ Contar palabras de la selección
- ⬜ (Estudiar) comentarios y control de cambios para trabajos en grupo
- ⬜ Columnas, bordes de página, encabezados distintos en hojas pares e impares

## Segmento 6: pulido y versión 1.0 ⬜
- ⬜ Modo oscuro
- ⬜ Instalador (Inno Setup) y asociar `.docx` con IsaWard
- ⬜ Medir y mejorar velocidad y memoria en una PC lenta real
- ⬜ Textos en inglés opcionales
- ⬜ Revisión de accesibilidad (teclado, contraste)

## Ideas sueltas (sin segmento todavía)
- **Zoom real** (Ctrl + rueda): hay que dibujar el documento escalado con un componente propio o con una vista gráfica; es un cambio grande y conviene probarlo con la ventana funcionando
- Columnas de texto (estilo periódico) y bordes de página
- Encabezado distinto en páginas pares e impares
- Leer el **formato** de los `.doc` antiguos (negrita, tamaños, tablas fieles): hay que leer las estructuras PAPX/CHPX
- Guardar listas reales (no como texto) en `.rtf`
- PDF: detectar títulos por tamaño de letra y columnas
- Leer `.dot`, `.wps` y `.xml` de Word 2003 si alguien los necesita
- Pegar imágenes desde el portapapeles y que se guarden bien en `.docx`
- Mantener el ancho de columnas de las tablas al abrir/guardar `.docx`
- Variantes de viñetas y formatos de numeración al guardar `.docx` desde el editor

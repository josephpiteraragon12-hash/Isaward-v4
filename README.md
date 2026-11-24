# IsaWard

Un procesador de texto sencillo, gratuito y **ligero**, pensado para PCs de pocos recursos.
Abre y guarda documentos de Word (`.docx`), tiene una interfaz clara y una **guía que explica
cada botón de dibujo**.

> Estado: **versión 0.3 (segmentos 1 a 3)**: edición completa, apertura de los formatos más comunes y **hojas reales** (tamaño, márgenes, encabezado, números de página). El plan completo está en [ROADMAP.md](ROADMAP.md).
>
> **¿No sabes cómo se hace algo? Pulsa F1.** La guía explica cada botón (con «Más información»), dice dónde está y trae recetas paso a paso.

## Qué puede hacer hoy

| | |
|---|---|
| **Escribir** | Fuente, tamaño, negrita, cursiva, subrayado, tachado, sub/superíndice, color, resaltado, borrar formato |
| **Párrafos** | Alineación (izquierda, centro, derecha, justificado), viñetas y numeración con niveles, sangría, interlineado, títulos 1 a 3, ventana **Párrafo** (sangría de primera línea y francesa para bibliografías, espacios antes y después) |
| **Insertar** | Tablas (agregar/quitar filas y columnas, combinar celdas), imágenes, enlaces, símbolos (°, ², π, €…), fecha y hora, línea horizontal |
| **Hoja y páginas** | Las hojas se ven separadas, con «Página 2 de 5» en la barra de estado. Salto de página, **hoja en blanco**, **tamaño de hoja** (A4, Carta, Oficio, Legal, A5, A3), vertical u horizontal, márgenes (con preajustes o a medida), **encabezado y pie de página** y **números de página** (con «no mostrar en la portada») |
| **Editar** | Deshacer/rehacer, cortar/copiar/pegar, buscar y reemplazar, contador de palabras |
| **Archivos** | Nuevo, abrir (también arrastrando el archivo a la ventana), archivos recientes, guardar, guardar como, exportar a PDF, imprimir y vista previa |
| **Seguridad** | Copia automática cada 2 minutos: si el programa se cierra mal, te ofrece **recuperar tu documento** al volver a abrirlo |
| **Ayuda** | **Guía (F1)** con tres pestañas: *Botones* (dibujo, nombre, atajo, dónde está y «Más información» de cada función), *¿Cómo hago…?* (recetas paso a paso para el colegio y la universidad) y *Atajos*. Tiene buscador |

### Formatos

IsaWard reconoce el formato por el **contenido** del archivo, no solo por su extensión (por ejemplo, un `.doc` que en realidad es RTF se abre bien).

| Formato | Abrir | Guardar |
|---|:-:|:-:|
| Word `.docx` (y plantillas `.dotx`, `.docm`) | ✅ | ✅ |
| OpenDocument `.odt` (LibreOffice) | ✅ | ✅ |
| Texto enriquecido `.rtf` | ✅ | ✅ |
| Texto `.txt` (y `.log`, `.csv`) | ✅ | ✅ |
| Markdown `.md` | ✅ | ✅ |
| Página web `.html` | ✅ | ✅ |
| Word antiguo `.doc` (97-2003) | ✅ solo el texto | — |
| PDF | ✅ solo el texto | ✅ (exportar) |

Se conserva (docx, odt, rtf), incluidos el tamaño de la hoja, la orientación, los márgenes, el encabezado y el pie con números de página: formato de texto, alineación, interlineado, sangrías, títulos, listas, tablas
(con celdas combinadas), imágenes, enlaces, líneas y saltos de página.
**Todavía no**: encabezados y pies de página, notas al pie, comentarios, control de cambios.
Notas: al guardar `.rtf` las listas se escriben como texto ("•", "1."); los `.pdf` y los `.doc` antiguos se abren
solo como texto (para conservar el formato de un `.doc`, ábrelo en Word o LibreOffice y guárdalo como `.docx`);
un PDF escaneado (una foto de la hoja) no tiene texto y no se puede leer.

## Requisitos

- Windows 10 u 11 de 64 bits (la librería gráfica, Qt 6, no funciona en Windows 7 u 8).
- Para usarlo desde el código: [Python 3.10 a 3.13](https://www.python.org/downloads/) (marca *Add Python to PATH*).

## Usarlo

**Opción A: bajar el programa ya compilado.** En la pestaña *Actions* de GitHub, entra a la última
ejecución de "Compilar IsaWard.exe" y descarga `IsaWard-windows.zip`. Descomprime y abre `IsaWard.exe`.
(Si publicas una etiqueta como `v0.1.0`, el zip aparece también en *Releases*.)

**Opción B: ejecutarlo desde el código.** Doble clic en `run.bat`. La primera vez instala lo necesario.

**Opción C: compilar tú mismo el .exe.** Doble clic en `build.bat`. El resultado queda en
`dist\IsaWard\IsaWard.exe` (copia la carpeta `IsaWard` completa). Con `build.bat onefile` sale un solo
archivo, pero tarda más en abrir en PCs lentas.

## Atajos de teclado

Siguen los de Google Docs y LibreOffice: `Ctrl+B` negrita, `Ctrl+I` cursiva, `Ctrl+U` subrayado,
`Ctrl+S` guardar, `Ctrl+F` buscar, `Ctrl+H` reemplazar, `Ctrl+K` enlace, `Ctrl+L/E/R/J` alinear,
`Ctrl+Enter` salto de página, `F1` guía. La lista completa está en la guía dentro del programa.

## Para quien quiera colaborar

- `HANDOFF.md`: cómo está armado el proyecto y cómo continuarlo (también con otra cuenta de Claude).
- `ROADMAP.md`: qué está hecho y qué sigue, por segmentos.
- `PRUEBA_MANUAL.md`: lista de comprobación para probar la ventana en Windows.
- `tests/data/`: documentos de muestra (docx, odt, rtf, doc, pdf) para probar la apertura de cada formato.
- Pruebas automáticas: `python -m unittest discover tests`
- Ver los iconos sin abrir la app: `python tools/preview_icons.py` (necesita Pillow)

Licencia MIT.

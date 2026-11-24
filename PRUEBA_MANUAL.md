# Prueba manual en Windows (la primera vez)

El código de la ventana se escribió **sin poder ejecutarlo** (el entorno de desarrollo no tenía Qt).
Esta lista sirve para descubrir rápido qué falla. Si algo falla, copia el mensaje de error
(también queda en `IsaWard-errores.log`, en tu carpeta de usuario) y pásaselo a Claude junto con el proyecto.

1. [ ] Abre el programa con `run.bat`. Se ve una hoja blanca centrada sobre fondo gris azulado.
2. [ ] Escribe un párrafo. El contador de palabras (abajo a la derecha) sube.
3. [ ] Selecciona texto y prueba Negrita, Cursiva, Subrayado, Tachado: el botón queda marcado.
4. [ ] Cambia fuente y tamaño desde los desplegables; los botones se actualizan al mover el cursor.
5. [ ] Color de fuente y Resaltado: elige uno de la lista y prueba "Más colores…".
6. [ ] Alineación: centrar, derecha, justificar. Interlineado 1,5.
7. [ ] Viñetas, luego Tab (baja un nivel), luego Shift+Tab (sube). Numeración también.
8. [ ] Estilo "Título 1" en un párrafo: se ve grande y en negrita.
9. [ ] Inserta una tabla 3×3, escribe en las celdas, usa Tab para avanzar; menú Tabla → agregar fila.
10. [ ] Inserta una imagen (foto JPG) y un enlace; Ctrl+clic en el enlace abre el navegador.
11. [ ] Línea horizontal y Salto de página (Ctrl+Enter).
12. [ ] Ctrl+F: busca una palabra, reemplaza una, reemplaza todo, y Ctrl+Z deshace de una vez.
13. [ ] Guardar como `.docx`. Ábrelo en Word, LibreOffice o Google Docs: debe verse igual que en IsaWard.
14. [ ] Cierra IsaWard y abre ese `.docx` otra vez: todo sigue ahí (tabla, imagen, listas, colores).
15. [ ] Abre un `.docx` hecho en Word con títulos, listas e imágenes.
16. [ ] Guardar como `.txt`, `.md`, `.html`, `.odt`; exportar a PDF; vista previa de impresión.
17. [ ] Arrastra un archivo a la ventana. Cierra con cambios sin guardar: pregunta si guardar.
18. [ ] F1 abre la guía: se ven todos los iconos con su explicación.
19. [ ] Con una PC lenta: ¿abre en pocos segundos? ¿escribir va fluido con 20 páginas?

## Segmento 2 (formatos nuevos y seguridad)

En la carpeta `tests\data\` hay un mismo documento guardado en cinco formatos (`muestra.docx`, `.odt`, `.rtf`, `.doc`, `.pdf`).

20. [ ] Abre `muestra.docx`: se ve un título, texto con negrita/rojo/resaltado, un enlace, listas, una tabla con una celda doble sombreada, una imagen y, tras un salto de página, "Segunda página".
21. [ ] Abre `muestra.odt` y `muestra.rtf`: deben verse casi igual que el `.docx` (puede cambiar un poco el espaciado).
22. [ ] Abre `muestra.doc`: aparece un aviso ("se abrió solo el texto"); el texto, el enlace y la tabla están, sin formato.
23. [ ] Abre `muestra.pdf`: aparece un aviso; el texto de las dos páginas está.
24. [ ] Prueba un `.rtf` o `.docx` hecho con Word de verdad (el que tengas a mano) y compara.
25. [ ] Guarda un documento con tabla, lista e imagen como `.rtf` y ábrelo con Word o WordPad.
26. [ ] Archivo → Abrir reciente: aparecen los últimos archivos; "Borrar la lista" los quita.
27. [ ] Intenta abrir un `.exe` o un `.zip`: debe decir que no es un documento (sin cerrarse el programa).
28. [ ] **Recuperación:** escribe algo en un documento nuevo, espera 2 minutos (o más), cierra IsaWard a la fuerza (Administrador de tareas → Finalizar tarea) y vuelve a abrirlo: debe ofrecerte recuperar el texto.
29. [ ] Cierra normalmente con cambios sin guardar y elige "No guardar": al reabrir NO debe ofrecer recuperar nada.
30. [ ] Abre un documento de 50 páginas o más (pega mucho texto): abrir y guardar no debe tardar más de unos segundos.

## Segmento 3 (hojas, guía y ayuda)

31. [ ] Al abrir el programa, la hoja en blanco se ve con su marco; abajo a la derecha dice «Página 1 de 1 · Hoja A4 vertical».
32. [ ] Escribe o pega texto hasta llenar más de una hoja: aparece una **franja gris** que separa las hojas y la barra de estado dice «Página 2 de 2».
33. [ ] Pulsa **Salto de página** (Ctrl+Enter) a mitad de texto: lo siguiente pasa a una hoja nueva, separada por la franja gris.
34. [ ] Pulsa **Hoja en blanco**: aparece una hoja vacía entre lo de antes y lo de después. Deshacer (Ctrl+Z) la quita.
35. [ ] **Configurar página**: cambia a Carta y a Horizontal; el dibujito se actualiza, la hoja cambia de forma al aceptar y la barra de estado lo dice.
36. [ ] Cambia los márgenes (prueba «Estrecho» y luego escribe números propios): el texto se acomoda al nuevo ancho.
37. [ ] **Encabezado y pie**: pon el nombre del colegio a la izquierda y «Página {pagina} de {paginas}» al centro del pie; aparecen en cada hoja.
38. [ ] **Números de página**: elige «Abajo, a la derecha» y «Página 1 de 5»; marca «No mostrar en la primera hoja»: la primera hoja queda limpia.
39. [ ] **Exportar a PDF** y ábrelo: tiene las mismas hojas, márgenes, encabezado, pie y números que viste en pantalla (también en horizontal).
40. [ ] **Vista previa de impresión**: se ven las hojas igual; prueba el zoom de esa ventana.
41. [ ] **Guardar como .docx** y abre ese archivo en Word o LibreOffice: mismo tamaño de hoja, orientación, márgenes, encabezado y «Página X de Y» (los números cambian solos).
42. [ ] Abre `tests\data\hoja.docx` (Carta horizontal, encabezado y pie): se ve con esa hoja y su portada sin encabezado. Abre también `hoja.odt` y `hoja.rtf`.
43. [ ] **Párrafo…** (¶): prueba «Primera línea» y «Francesa», y espacio antes/después; se ve el cambio al instante.
44. [ ] **Símbolo** (Ω): doble clic en varios (°, ², π, €); la ventana queda abierta. **Fecha y hora**: inserta la fecha de hoy.
45. [ ] **Guía (F1)**: en «Botones», toca «Más información» en varios; prueba «Abrir todo/Cerrar todo» y el buscador (escribe «pagina» sin tilde: aparece «Números de página»).
46. [ ] En la guía, pestaña **¿Cómo hago…?**: abre «Agregar una hoja nueva» y «Cambiar el tamaño de la hoja»; los pasos coinciden con lo que ves en pantalla.
47. [ ] En «Configurar página», el botón **Ayuda** abre la guía directamente en esa herramienta.
48. [ ] Si las hojas se ven rarísimas: abre `isaward\config.py`, cambia `PAGINATE = True` por `PAGINATE = False`, vuelve a abrir y avísame.

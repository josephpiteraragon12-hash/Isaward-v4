"""Catálogo de herramientas: nombre, explicación, dónde está y ayuda ampliada de cada una.

De aquí salen los botones, los textos de ayuda (tooltips) y la "Guía de herramientas" (F1).

REGLA DEL PROYECTO: cada función visible del programa (botón, menú, lista desplegable) debe tener su fila aquí,
con `where` (dónde encontrarla) y `more` (para qué sirve y cómo usarla). Las pruebas lo exigen.
Para añadir una herramienta nueva: icono en icon_defs.py, fila aquí, acción en main_window.py y,
si ayuda a una tarea común, una receta en howto.py.
"""
import unicodedata
from typing import NamedTuple

from .icon_defs import ICONS


class Tool(NamedTuple):
    id: str
    group: str
    label: str
    help: str                 # una frase: qué hace
    shortcut: str = ""
    where: str = ""           # dónde está en el programa
    more: str = ""            # explicación ampliada (se muestra al tocar "Más información")
    icon: str = ""            # nombre del icono si es distinto del id; sin icono propio se usa el genérico "menu"


def _t(id, group, label, help, shortcut="", where="", more="", icon=""):
    return Tool(id, group, label, help, shortcut, where, more, icon)


B1 = "Barra de arriba, fila 1"
B2 = "Barra de formato, fila 2"
B3 = "Barra de insertar y hoja, fila 3"

TOOLS = [
    # ------------------------------------------------------------------ Archivo
    _t("new", "Archivo", "Nuevo", "Crea un documento en blanco.", "Ctrl+N",
       f"{B1} (primer botón) · Menú Archivo → Nuevo",
       "Abre una hoja vacía. Si lo que tienes en pantalla tiene cambios sin guardar, primero te pregunta si quieres "
       "guardarlos, así que no pierdes nada por accidente.\n\nEl documento nuevo usa el tamaño de hoja que dejaste "
       "como predeterminado (A4 si nunca lo cambiaste). Puedes cambiarlo en Hoja → Configurar página."),
    _t("open", "Archivo", "Abrir", "Abre un documento de tu PC (Word, LibreOffice, RTF, PDF, texto…).", "Ctrl+O",
       f"{B1} (segundo botón) · Menú Archivo → Abrir",
       "Elige un archivo de tu computadora. IsaWard abre Word (.docx, y también .doc antiguo y plantillas), "
       "LibreOffice (.odt), RTF, PDF, texto (.txt), Markdown (.md) y páginas web (.html).\n\nTambién puedes "
       "arrastrar el archivo con el mouse y soltarlo sobre la ventana de IsaWard.\n\nOjo: los .doc antiguos y los PDF "
       "se abren solo como texto (sin formato). Para seguir trabajando con comodidad, guárdalos como .docx."),
    _t("recent", "Archivo", "Abrir reciente", "Lista de los últimos archivos que abriste o guardaste.", "",
       "Menú Archivo → Abrir reciente",
       "Muestra hasta 8 archivos que usaste hace poco; haz clic en uno para abrirlo sin buscarlo en carpetas. "
       "«Borrar la lista» la vacía (no borra tus archivos)."),
    _t("save", "Archivo", "Guardar", "Guarda los cambios en el archivo actual.", "Ctrl+S",
       f"{B1} (tercer botón) · Menú Archivo → Guardar",
       "Si el documento ya tiene nombre, lo guarda ahí mismo. Si es nuevo, te pide un nombre y una carpeta.\n\n"
       "Consejo: guarda seguido. Además, IsaWard hace una copia automática de seguridad cada 2 minutos y, si el "
       "programa se cierra mal, te ofrece recuperar tu trabajo al volver a abrirlo."),
    _t("save_as", "Archivo", "Guardar como", "Guarda una copia con otro nombre o en otro formato.", "Ctrl+Shift+S",
       "Menú Archivo → Guardar como",
       "Sirve para dos cosas: hacer una copia con otro nombre, o cambiar de formato.\n\n"
       "• Para mandarlo a alguien que usa Word: «Documento de Word (.docx)».\n• Para el celular o internet: PDF "
       "(botón «Exportar a PDF»).\n• «Texto sin formato (.txt)» borra negritas, tablas e imágenes: úsalo solo si "
       "lo necesitas.\n• También puedes guardar como .rtf, .odt (LibreOffice), .html y .md."),
    _t("pdf", "Archivo", "Exportar a PDF", "Crea un PDF para compartir o entregar.", "",
       f"{B1} (cuarto botón) · Menú Archivo → Exportar a PDF",
       "Crea un archivo PDF que se ve igual en cualquier computadora o celular, con las hojas, márgenes, "
       "encabezados y números de página que pusiste. Es lo ideal para entregar trabajos: nadie puede cambiarlo "
       "por accidente.\n\nTu documento original no cambia; el PDF es una copia aparte."),
    _t("preview", "Archivo", "Vista previa de impresión", "Muestra cómo saldrá el documento en papel.", "",
       "Menú Archivo → Vista previa de impresión",
       "Abre una ventana que muestra el documento hoja por hoja, tal como saldría impreso. Arriba tiene lupas para "
       "acercar y alejar, un botón para ver una o varias hojas a la vez y otro para ajustar al ancho.\n\nEs la "
       "mejor forma de revisar el trabajo completo antes de imprimirlo o entregarlo."),
    _t("print", "Archivo", "Imprimir", "Manda el documento a la impresora.", "Ctrl+P",
       f"{B1} (quinto botón) · Menú Archivo → Imprimir",
       "Elige la impresora, cuántas copias y qué hojas imprimir. Usa el tamaño de hoja que configuraste en "
       "Hoja → Configurar página. Si tu impresora usa otro tamaño de papel (por ejemplo, tienes A4 en el "
       "documento y Carta en la impresora), revisa esa opción en la ventana de impresión."),
    _t("quit", "Archivo", "Salir", "Cierra IsaWard.", "Ctrl+Q", "Menú Archivo → Salir",
       "Cierra el programa. Si hay cambios sin guardar, antes te pregunta qué hacer: Guardar, No guardar o Cancelar "
       "(volver al documento)."),

    # ------------------------------------------------------------------ Edición
    _t("undo", "Edición", "Deshacer", "Anula lo último que hiciste.", "Ctrl+Z",
       f"{B1} (flecha curva a la izquierda) · Menú Editar → Deshacer",
       "Si te equivocaste (borraste algo, cambiaste un color…), púlsalo y vuelve atrás. Puedes pulsarlo varias "
       "veces para retroceder paso a paso.\n\nNota: al cambiar el tamaño de la hoja o los márgenes, el historial de "
       "«Deshacer» se reinicia."),
    _t("redo", "Edición", "Rehacer", "Vuelve a hacer lo que acabas de deshacer.", "Ctrl+Y",
       f"{B1} (flecha curva a la derecha) · Menú Editar → Rehacer",
       "Es el contrario de Deshacer: si deshiciste de más, Rehacer te devuelve el cambio."),
    _t("cut", "Edición", "Cortar", "Quita lo seleccionado para pegarlo en otro lugar.", "Ctrl+X",
       f"{B1} (tijeras) · Menú Editar → Cortar",
       "Primero selecciona el texto (arrastra el mouse sobre él). Al cortar, desaparece de su sitio y queda "
       "guardado en el «portapapeles» hasta que lo pegues. Así se mueve algo de un lugar a otro."),
    _t("copy", "Edición", "Copiar", "Copia lo seleccionado sin quitarlo.", "Ctrl+C",
       f"{B1} (dos hojitas) · Menú Editar → Copiar",
       "Selecciona el texto y cópialo: se queda donde está y además queda guardado para pegarlo en otro lugar "
       "(incluso en otro programa)."),
    _t("paste", "Edición", "Pegar", "Pone aquí lo último que copiaste o cortaste.", "Ctrl+V",
       f"{B1} (tablita con papel) · Menú Editar → Pegar",
       "Pone en el cursor lo último que copiaste o cortaste. Si copiaste desde una página web, se pegan también "
       "los formatos; si no los quieres, usa «Borrar formato» después. Si arrastras un archivo de Word, PDF, etc. "
       "sobre la hoja, IsaWard lo abre."),
    _t("select_all", "Edición", "Seleccionar todo", "Selecciona todo el documento.", "Ctrl+A",
       "Menú Editar → Seleccionar todo",
       "Marca todo el texto de una vez. Útil para cambiar la fuente o el interlineado de todo el documento, o "
       "para copiarlo completo."),
    _t("find", "Edición", "Buscar y reemplazar", "Encuentra una palabra y, si quieres, la cambia por otra.", "Ctrl+F",
       f"{B1} (lupa) · Menú Editar → Buscar y reemplazar",
       "Escribe la palabra en «Buscar» y pulsa «Buscar siguiente»: te lleva a cada lugar donde aparece. Si quieres "
       "cambiarla, escribe la nueva en «Reemplazar con» y usa «Reemplazar» (de a una) o «Reemplazar todo».\n\n"
       "Opciones: «Distinguir mayúsculas» (Casa ≠ casa) y «Solo palabras completas» (para que «sol» no encuentre "
       "«solo»). «Reemplazar todo» se puede deshacer de una vez con Ctrl+Z."),
    _t("replace", "Edición", "Reemplazar", "Abre Buscar y reemplazar listo para cambiar palabras.", "Ctrl+H",
       "Menú Editar → Reemplazar…",
       "Es la misma ventana de «Buscar y reemplazar», pensada para cuando quieres cambiar una palabra por otra "
       "en todo el documento (por ejemplo, un nombre que escribiste mal muchas veces)."),

    # ------------------------------------------------------------------ Fuente
    _t("style", "Fuente", "Estilo del párrafo", "Convierte el párrafo en texto normal o en un título.", "",
       f"{B2} (primera lista desplegable)",
       "Elige «Normal» para texto común o «Título 1, 2 o 3» para encabezados: el Título 1 es el más grande y "
       "se usa para los capítulos; el 2 y el 3 para subtemas.\n\nUsar títulos de verdad (no solo letras grandes) "
       "ayuda a que el documento quede ordenado y Word lo reconozca como títulos al abrirlo."),
    _t("font", "Fuente", "Fuente (tipo de letra)", "Cambia el tipo de letra.", "",
       f"{B2} (segunda lista desplegable)",
       "Selecciona primero el texto y luego elige la fuente. Para trabajos escolares suelen pedirse Arial, "
       "Times New Roman o Calibri.\n\nSi no seleccionas nada, el cambio afecta a la palabra donde está el cursor "
       "y a lo que escribas después."),
    _t("size", "Fuente", "Tamaño de letra", "Cambia qué tan grande es la letra.", "",
       f"{B2} (tercera lista desplegable, la pequeña)",
       "Elige un número de la lista o escribe el que quieras (por ejemplo 12) y pulsa Intro. El tamaño normal "
       "de un trabajo es 11 o 12; los títulos suelen ir en 14 a 16."),
    _t("bold", "Fuente", "Negrita", "Pone el texto seleccionado más grueso.", "Ctrl+B",
       f"{B2} (la «B») · Menú Formato → Negrita",
       "Selecciona el texto y púlsalo. Si el botón está marcado (hundido), el texto ya está en negrita: púlsalo "
       "otra vez para quitarla. También funciona antes de escribir: actívalo, escribe, y desactívalo."),
    _t("italic", "Fuente", "Cursiva", "Inclina el texto seleccionado.", "Ctrl+I",
       f"{B2} (la «I») · Menú Formato → Cursiva",
       "Se usa para títulos de libros, palabras en otro idioma o para dar énfasis suave."),
    _t("underline", "Fuente", "Subrayado", "Subraya el texto seleccionado.", "Ctrl+U",
       f"{B2} (la «U») · Menú Formato → Subrayado",
       "Subraya el texto. Cuidado: en documentos, el subrayado suele confundirse con los enlaces; para destacar "
       "usa mejor negrita o cursiva."),
    _t("strike", "Fuente", "Tachado", "Traza una línea sobre el texto, como borrado.", "Ctrl+Shift+X",
       f"{B2} (la «S» tachada) · Menú Formato → Tachado",
       "Sirve para mostrar algo eliminado o descartado, por ejemplo en una lista de tareas ya hechas."),
    _t("sub", "Fuente", "Subíndice", "Baja y achica el texto, como en H₂O.", "Ctrl+=",
       f"{B2} (la «x» con un 2 abajo) · Menú Formato → Subíndice",
       "Selecciona el número o letra que debe ir abajo (el 2 de H2O) y púlsalo. Para volver al texto normal, "
       "púlsalo de nuevo. Muy usado en química y matemáticas."),
    _t("sup", "Fuente", "Superíndice", "Sube y achica el texto, como en m².", "Ctrl+Shift+=",
       f"{B2} (la «x» con un 2 arriba) · Menú Formato → Superíndice",
       "Selecciona lo que debe ir arriba (el 2 de m2, exponentes, notas como 1º) y púlsalo. Para volver al "
       "texto normal, púlsalo de nuevo."),
    _t("font_color", "Fuente", "Color de fuente", "Cambia el color de las letras.", "",
       f"{B2} (la «A» con barra roja)",
       "Selecciona el texto y toca el botón: se abre una lista con colores. «Más colores…» te deja elegir "
       "cualquier color; «Automático (negro)» devuelve el color normal."),
    _t("highlight", "Fuente", "Resaltado", "Pinta el fondo del texto, como con un marcador.", "",
       f"{B2} (la «A» sobre fondo amarillo)",
       "Como un marcador fluorescente: selecciona el texto, toca el botón y elige un color. «Sin resaltado» "
       "lo quita. Ideal para marcar lo importante al estudiar."),
    _t("clear_format", "Fuente", "Borrar formato", "Quita negrita, color, tamaño y demás del texto seleccionado.",
       "Ctrl+\\", f"{B2} (la «A» con una cruz roja)",
       "Devuelve el texto seleccionado a la fuente y el tamaño normales y quita negrita, cursiva, subrayado, "
       "colores y resaltado. Muy útil después de pegar texto de una página web con formatos raros."),

    # ------------------------------------------------------------------ Párrafo
    _t("align_left", "Párrafo", "Alinear a la izquierda", "Pega el texto al margen izquierdo.", "Ctrl+L",
       f"{B2} (rayitas pegadas a la izquierda) · Menú Formato",
       "Es la forma normal de escribir: las líneas empiezan todas en el margen izquierdo y terminan desiguales a "
       "la derecha."),
    _t("align_center", "Párrafo", "Centrar", "Centra el texto en la hoja.", "Ctrl+E",
       f"{B2} (rayitas al centro) · Menú Formato",
       "Pone el texto en el medio de la hoja. Se usa para títulos y portadas."),
    _t("align_right", "Párrafo", "Alinear a la derecha", "Pega el texto al margen derecho.", "Ctrl+R",
       f"{B2} (rayitas pegadas a la derecha) · Menú Formato",
       "Se usa para fechas, firmas y cosas que van en la esquina derecha."),
    _t("align_justify", "Párrafo", "Justificar", "Reparte el texto para que ambos márgenes queden parejos.", "Ctrl+J",
       f"{B2} (rayitas parejas por ambos lados) · Menú Formato",
       "Estira cada línea para que llegue justo al margen derecho, como en los libros y periódicos. Muchos "
       "trabajos escolares piden «texto justificado»."),
    _t("bullets", "Párrafo", "Viñetas", "Convierte los párrafos en una lista con puntos.", "Ctrl+Shift+8",
       f"{B2} (puntos con rayitas) · Menú Formato → Viñetas",
       "Selecciona uno o varios párrafos y púlsalo: cada párrafo pasa a ser un punto de la lista. Pulsa Intro "
       "para el siguiente punto; pulsa Intro dos veces seguidas para terminar la lista.\n\nTab baja un nivel "
       "(sub-lista) y Mayús+Tab lo sube."),
    _t("numbering", "Párrafo", "Numeración", "Convierte los párrafos en una lista numerada.", "Ctrl+Shift+7",
       f"{B2} (números con rayitas) · Menú Formato → Numeración",
       "Igual que las viñetas pero con números (1, 2, 3…), ideal para pasos o instrucciones. Si agregas o quitas "
       "un punto en medio, los números se ajustan solos."),
    _t("indent_less", "Párrafo", "Reducir sangría", "Acerca el párrafo (o el nivel de la lista) al margen.", "Ctrl+[",
       f"{B2} (flecha hacia la izquierda) · Menú Formato",
       "Mueve el párrafo hacia el margen izquierdo un paso. En una lista, la sube un nivel."),
    _t("indent_more", "Párrafo", "Aumentar sangría", "Aleja el párrafo (o baja un nivel en la lista).", "Ctrl+]",
       f"{B2} (flecha hacia la derecha) · Menú Formato",
       "Mueve el párrafo hacia la derecha un paso (útil para citas largas). En una lista, crea una sub-lista."),
    _t("line_spacing", "Párrafo", "Interlineado", "Cambia el espacio entre las líneas de un párrafo.", "",
       f"{B2} (flechas arriba y abajo con rayitas) · Menú Formato → Interlineado",
       "Elige Sencillo (1,0), 1,15, 1,5 o Doble (2,0). Los trabajos escolares suelen pedir 1,5 o doble. "
       "Selecciona todo el documento (Ctrl+A) para cambiarlo en todos los párrafos.\n\nPara más control "
       "(espacio antes y después, sangría de primera línea) usa el botón «Párrafo…»."),
    _t("paragraph", "Párrafo", "Párrafo…", "Sangrías, espacios y interlineado con medidas exactas.", "",
       f"{B2} (el símbolo ¶) · Menú Formato → Párrafo…",
       "Abre una ventana para ajustar el párrafo con precisión, en centímetros:\n\n"
       "• Sangría izquierda: separa todo el párrafo del margen.\n"
       "• Especial → Primera línea: solo la primera línea entra hacia la derecha (muy usado en trabajos escritos).\n"
       "• Especial → Francesa: la primera línea queda pegada y las demás entran (así se hace la bibliografía en "
       "normas como APA).\n• Espacio antes y después del párrafo, en puntos.\n• Interlineado.\n\n"
       "Se aplica al párrafo donde está el cursor o a todos los que tengas seleccionados."),

    # ------------------------------------------------------------------ Insertar
    _t("table", "Insertar", "Tabla", "Inserta una tabla con las filas y columnas que elijas.", "",
       f"{B3} (rejilla) · Menú Insertar → Tabla",
       "Te pregunta cuántas filas y columnas quieres y crea la tabla donde está el cursor. Escribe en cada "
       "celda; con Tab pasas a la siguiente (y al final de la última se crea una fila nueva).\n\nPara agregar o "
       "quitar filas y columnas, o unir celdas, usa el menú «Tabla» (aparece activo cuando el cursor está "
       "dentro de una tabla)."),
    _t("image", "Insertar", "Imagen", "Inserta una foto o dibujo desde tu PC.", "",
       f"{B3} (cuadro con montaña) · Menú Insertar → Imagen",
       "Elige un archivo PNG, JPG, GIF o BMP. Si la foto es más ancha que la hoja, se ajusta sola para que "
       "quepa. IsaWard también reduce las fotos gigantes para que el documento no pese demasiado."),
    _t("link", "Insertar", "Enlace", "Convierte el texto seleccionado en un enlace a una página web.", "Ctrl+K",
       f"{B3} (dos eslabones) · Menú Insertar → Enlace",
       "Selecciona el texto que será el enlace (o no selecciones nada para escribir la dirección completa), pulsa el "
       "botón y escribe la dirección, como https://www.ejemplo.com.\n\nPara abrir un enlace desde el "
       "documento, mantén pulsada la tecla Ctrl y haz clic sobre él."),
    _t("symbol", "Insertar", "Símbolo", "Inserta caracteres especiales: °, ², π, ≤, €, ©…", "",
       f"{B3} (la letra Ω) · Menú Insertar → Símbolo…",
       "Abre una tabla con símbolos agrupados (matemáticas, letras griegas, monedas, flechas, signos "
       "de puntuación…). Haz doble clic en uno para ponerlo en el documento, o selecciónalo y pulsa «Insertar». "
       "La ventana queda abierta para que pongas varios seguidos."),
    _t("date", "Insertar", "Fecha y hora", "Escribe la fecha de hoy (o la hora) en el documento.", "",
       f"{B3} (calendario) · Menú Insertar → Fecha y hora",
       "Muestra la fecha de hoy en varios formatos (por ejemplo «21 de noviembre de 2026» o «21/11/2026») y la "
       "hora. Elige uno y se escribe donde está el cursor. Se escribe como texto normal: no se actualiza solo "
       "al día siguiente."),
    _t("hr", "Insertar", "Línea horizontal", "Dibuja una línea de lado a lado para separar partes.", "",
       f"{B3} (línea con puntitos) · Menú Insertar → Línea horizontal",
       "Pone una línea que cruza toda la hoja, útil para separar secciones o poner una firma."),

    # ------------------------------------------------------------------ Hoja y páginas
    _t("page_break", "Hoja y páginas", "Salto de página", "Lo que sigue empieza en una hoja nueva.", "Ctrl+Enter",
       f"{B3} (hoja con línea punteada) · Menú Hoja → Salto de página · Menú Insertar",
       "Termina la hoja actual: todo lo que escribas después del cursor pasa al comienzo de una hoja nueva. "
       "Se ve como una separación gris entre las hojas.\n\nÚsalo, por ejemplo, para que cada capítulo "
       "empiece en su propia hoja, o para separar la portada del texto.\n\nPara quitarlo, coloca el cursor al "
       "inicio del texto de la hoja nueva y pulsa la tecla Retroceso (←) hasta que se junten."),
    _t("new_page", "Hoja y páginas", "Hoja en blanco", "Agrega una hoja completamente en blanco en el cursor.", "",
       f"{B3} (dos hojas con un +) · Menú Hoja → Hoja en blanco · Menú Insertar",
       "Inserta una hoja vacía justo donde está el cursor: lo que está antes se queda en su hoja, luego viene "
       "una hoja en blanco, y lo que sigue continúa en la hoja siguiente.\n\nSi lo que quieres es solo empezar "
       "a escribir en una hoja nueva, usa «Salto de página».\n\nPara agregar una hoja en blanco al final del "
       "documento, pon el cursor al final (Ctrl+Fin) y pulsa este botón."),
    _t("page_setup", "Hoja y páginas", "Configurar página", "Tamaño de la hoja, orientación y márgenes.", "",
       f"{B3} (hoja con recuadro) · Menú Hoja → Configurar página…",
       "Aquí cambias las dimensiones del documento:\n\n"
       "• Tamaño: A4, Carta (Letter), Oficio, Legal, A5 o A3.\n"
       "• Orientación: Vertical (hoja alta) u Horizontal (hoja ancha).\n"
       "• Márgenes: Normal, Estrecho, Moderado, Ancho, o los que escribas tú en centímetros (arriba, abajo, "
       "izquierda, derecha).\n"
       "• «Usar como predeterminado»: los documentos nuevos nacerán con esta hoja.\n\n"
       "Los cambios se ven de inmediato y se guardan dentro del archivo (en .docx, .rtf y .odt), así que Word "
       "los respeta. Si tu trabajo pide una norma específica, escribe sus medidas en «Personalizado»."),
    _t("header_footer", "Hoja y páginas", "Encabezado y pie de página", "Texto fijo arriba y abajo de cada hoja.", "",
       f"{B3} (hoja con franjas arriba y abajo) · Menú Hoja → Encabezado y pie de página…",
       "El encabezado va en el borde de arriba de cada hoja y el pie en el de abajo. Cada uno tiene tres "
       "espacios: izquierda, centro y derecha. Por ejemplo, el nombre del colegio a la izquierda y el título del "
       "trabajo a la derecha.\n\nEn los cuadros puedes escribir {pagina} (se cambia por el número de cada hoja) y "
       "{paginas} (el total de hojas). Marca «No mostrar en la primera hoja» si tu portada va sin encabezado.\n\n"
       "Se ve en pantalla en cada hoja, sale en el PDF y en la impresión, y se guarda en .docx para que Word lo "
       "muestre igual."),
    _t("page_number", "Hoja y páginas", "Números de página", "Numera las hojas automáticamente.", "",
       f"{B3} (hoja con un 1 abajo) · Menú Hoja → Números de página…",
       "Elige dónde van los números (abajo al centro, abajo a la derecha, arriba…) y cómo se escriben: «1», "
       "«Página 1», «Página 1 de 5» o «- 1 -». Marca «No mostrar en la primera hoja» para que la portada no "
       "lleve número.\n\nEs la misma ventana de «Encabezado y pie de página»; se abre en la parte de números."),

    # ------------------------------------------------------------------ Tabla
    _t("table_row_add", "Tabla", "Agregar fila (debajo)", "Agrega una fila debajo de la actual.", "",
       "Menú Tabla → Agregar fila debajo (primero haz clic dentro de la tabla)",
       "Pon el cursor en una celda de la tabla y úsalo: aparece una fila nueva justo debajo. También se crea una "
       "fila al pulsar Tab en la última celda de la tabla."),
    _t("table_col_add", "Tabla", "Agregar columna (a la derecha)", "Agrega una columna a la derecha de la actual.", "",
       "Menú Tabla → Agregar columna a la derecha (primero haz clic dentro de la tabla)",
       "Pon el cursor en una celda y úsalo: aparece una columna nueva a la derecha de la actual."),
    _t("table_row_above", "Tabla", "Agregar fila arriba", "Agrega una fila encima de la actual.", "",
       "Menú Tabla → Agregar fila arriba", "Igual que «Agregar fila», pero la fila nueva queda encima de la celda "
       "donde está el cursor."),
    _t("table_col_left", "Tabla", "Agregar columna a la izquierda", "Agrega una columna a la izquierda de la actual.", "",
       "Menú Tabla → Agregar columna a la izquierda", "Igual que «Agregar columna», pero queda a la izquierda."),
    _t("table_row_del", "Tabla", "Eliminar fila", "Quita la fila donde está el cursor.", "",
       "Menú Tabla → Eliminar fila", "Borra toda la fila (con lo que tenga escrito). Si es la única fila, se "
       "elimina la tabla completa. Si te equivocas, Ctrl+Z."),
    _t("table_col_del", "Tabla", "Eliminar columna", "Quita la columna donde está el cursor.", "",
       "Menú Tabla → Eliminar columna", "Borra toda la columna. Si es la única, se elimina la tabla completa."),
    _t("table_merge", "Tabla", "Combinar celdas", "Une varias celdas seleccionadas en una sola.", "",
       "Menú Tabla → Combinar celdas seleccionadas",
       "Selecciona varias celdas arrastrando el mouse de una a otra (que formen un rectángulo) y úsalo: se "
       "convierten en una celda grande. Muy útil para títulos que ocupan todo el ancho de la tabla."),
    _t("table_del", "Tabla", "Eliminar tabla", "Borra la tabla completa.", "",
       "Menú Tabla → Eliminar tabla", "Quita la tabla entera con todo su contenido. Se puede deshacer con Ctrl+Z."),

    # ------------------------------------------------------------------ Ayuda
    _t("help", "Ayuda", "Guía de herramientas", "Explica para qué sirve cada botón.", "F1",
       f"{B1} (el «?» al final) · Menú Ayuda → Guía de herramientas",
       "Es esta ventana. Tiene tres pestañas: «Botones» (todo lo que hace el programa, con su dibujo y dónde "
       "encontrarlo), «¿Cómo hago…?» (pasos para tareas comunes) y «Atajos» (teclas rápidas).\n\nEn "
       "«Botones», toca «Más información» para leer una explicación completa de cada uno. La caja de búsqueda "
       "filtra: escribe, por ejemplo, «página» o «tabla»."),
    _t("about", "Ayuda", "Acerca de IsaWard", "Muestra la versión del programa.", "",
       "Menú Ayuda → Acerca de IsaWard", "Dice qué versión estás usando. Si le escribes a quien te ayuda con el "
       "programa, menciona este número."),
]

TOOL_BY_ID = {t.id: t for t in TOOLS}

# El editor de texto ya atiende estos atajos por sí mismo; solo los mostramos.
NATIVE_SHORTCUTS = {"undo", "redo", "cut", "copy", "paste", "select_all"}

GROUP_ORDER = ["Archivo", "Edición", "Fuente", "Párrafo", "Insertar", "Hoja y páginas", "Tabla", "Ayuda"]

# Atajos y gestos que no son botones; se muestran en la pestaña "Atajos" de la guía.
EXTRA_SHORTCUTS = [
    ("Tab", "En una lista: baja un nivel. En una tabla: pasa a la celda siguiente (y crea una fila al final)."),
    ("Mayús+Tab", "En una lista: sube un nivel. En una tabla: vuelve a la celda anterior."),
    ("Ctrl + clic en un enlace", "Abre el enlace en tu navegador."),
    ("Intro dos veces (en una lista)", "Termina la lista y vuelve a escribir normal."),
    ("Ctrl+Inicio / Ctrl+Fin", "Salta al principio / al final del documento."),
    ("Ctrl+flechas", "Mueve el cursor de palabra en palabra."),
    ("Mayús+flechas", "Selecciona mientras mueves el cursor."),
    ("Doble clic / triple clic", "Selecciona una palabra / un párrafo completo."),
]


def icon_of(tool: Tool) -> str:
    """Nombre del icono de una herramienta (si no tiene uno propio, el genérico de menú)."""
    for name in (tool.icon, tool.id):
        if name and name in ICONS:
            return name
    return "menu"


def search_key(text: str) -> str:
    """Texto en minúsculas y sin tildes, para que «pagina» encuentre «página»."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def matches(query: str, text: str) -> bool:
    """¿Aparecen todas las palabras de la búsqueda en el texto? (sin importar tildes ni mayúsculas)"""
    haystack = search_key(text)
    return all(word in haystack for word in search_key(query).split())


def shortcut_text(shortcut: str) -> str:
    """Atajo en español para mostrarlo al usuario."""
    return shortcut.replace("Shift", "Mayús").replace("Enter", "Intro")

# Lector Libre

Lector de texto en voz alta **gratis** para Windows, al estilo Speechify / NaturalReader.

- **Leer selección o desde la posición del cursor (`Ctrl + Alt + R`)**: si tenés texto seleccionado lo lee; si no, lee desde donde esté el cursor hasta el final usando UI Automation. `Ctrl + Alt + P` pausa y reanuda.
- **Leer esta página con 1 clic (`Ctrl + Alt + W`)**: extrae de forma inteligente el contenido, etiquetas, preguntas y respuestas de páginas web y formularios (ej. Acts 29), saltando menús, navegación y pies de página.
- **OCR de pantalla (`Ctrl + Alt + O`)**: seleccioná cualquier zona de la pantalla para leer texto en imágenes o documentos escaneados con el OCR nativo de Windows.
- **Tres motores de voz (locales sin internet y online)**:
  - **Kokoro-82M (offline)**: español e inglés con detección automática de idioma por oración.
  - **Piper (offline)**: voces adicionales de español latinoamericano (Argentina, México) e inglés.
  - **Edge TTS (online, gratis)**: voces neurales adicionales.
- **Velocidad de 0.5× a 4× manteniendo el tono natural (WSOLA)**: cambiá la velocidad o la voz en vivo sin reiniciar la oración que está sonando.
- **Botón flotante compacto y Mini reproductor expandido**: alterná entre una micro-píldora flotante arrastrable y la barra completa de controles.
- **Ventana de estudio moderna**: abrí TXT, PDF (filtrando encabezados, pies y números de página repetidos), Word (`.docx`), libros **ePub (`.epub`)** o páginas web; incluye índice lateral de capítulos, **resaltado oración + palabra por palabra**, doble clic para saltar de oración y barra inferior con deslizador interactivo y tiempo restante.
- **Marcadores y Audiolibros**: guarda marcadores automáticos y manuales para retomar documentos largos donde quedaste, exporta a MP3/WAV o genera un **audiolibro completo separado por capítulos** (`.mp3`/`.wav` + `.m3u`).
- **Diccionario de pronunciación**: personalizá cómo se leen siglas o nombres (ej. `Acts 29` → `Hechos veintinueve`).

## Instalar
Descargá `LectorLibre-Setup.exe` desde [Releases](https://github.com/faculuz/Lector-Libre/releases/latest) y abrilo. Si Windows avisa que protegió tu PC: **Más información → Ejecutar de todas formas**.

## Desarrollo
Código Python + PySide6. Cada tag `v*` compila en GitHub Actions (PyInstaller + Inno Setup) y publica el instalador; la app busca actualizaciones en las Releases.

## Licencia
Distribuido bajo la Licencia Apache 2.0. Ver `LICENSE` y `NOTICE` para más detalles.

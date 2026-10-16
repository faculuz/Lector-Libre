# Lector Libre

Lector de texto en voz alta **gratis** para Windows, al estilo Speechify / NaturalReader.

- **Seleccioná texto en cualquier programa y apretá `Ctrl + Alt + R`** para escucharlo. `Ctrl + Alt + P` pausa y reanuda (los dos atajos se cambian en Configuración y se aplican al instante).
- Voces naturales **sin internet** (Kokoro-82M): español (Dora, Alex, Santa) e inglés (Heart, Bella, Nicole, Michael, Fenrir, Emma, George). Detecta el idioma de cada oración, así un texto mezclado en español e inglés se lee bien.
- Voz online opcional y gratuita (Edge) desde Configuración.
- Mini reproductor flotante: anterior / pausa / siguiente / detener, velocidad de 0.5x a 3x y elección de voz.
- Ventana de lectura: pegá texto o abrí TXT, PDF, Word o una página web; resalta la oración que se está leyendo.
- Exporta a MP3 o WAV, guarda historial de lecturas y se actualiza solo.

## Instalar
Descargá `LectorLibre-Setup.exe` desde [Releases](https://github.com/faculuz/Lector-Libre/releases/latest) y abrilo. Si Windows avisa que protegió tu PC: **Más información → Ejecutar de todas formas**. La primera vez descarga la voz (~340 MB, una sola vez).

## Desarrollo
Código Python + PySide6. Cada tag `v*` compila en GitHub Actions (PyInstaller + Inno Setup) y publica el instalador; la app busca actualizaciones en las Releases.

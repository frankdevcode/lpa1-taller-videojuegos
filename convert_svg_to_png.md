# Conversión de SVG a PNG

Para que Phaser utilice correctamente los recursos gráficos, es necesario convertir los archivos SVG a PNG. A continuación se presentan algunas opciones para realizar esta conversión:

## Opción 1: Usando Inkscape (aplicación de escritorio)

1. Descarga e instala [Inkscape](https://inkscape.org/es/)
2. Abre el archivo SVG con Inkscape
3. Ve a "Archivo" > "Exportar PNG"
4. Configura las dimensiones y la resolución adecuadas
5. Exporta el archivo PNG en la misma ubicación que el SVG

## Opción 2: Usando herramientas en línea

1. Utiliza alguna de estas herramientas en línea:
   - [SVG to PNG Converter](https://svgtopng.com/)
   - [Convertio](https://convertio.co/svg-png/)
   - [EZGIF](https://ezgif.com/svg-to-png)
2. Sube tus archivos SVG
3. Descarga los PNG resultantes
4. Colócalos en la misma ubicación que los SVG

## Opción 3: Usando herramientas de línea de comandos

Si tienes Node.js instalado, puedes usar la herramienta `svg2png`:

```bash
npm install -g svg2png
svg2png input.svg -o output.png
```

## Importante para sprites

Para imágenes que son sprite sheets (como personajes y enemigos), asegúrate de:

1. Exportar con las dimensiones correctas (manteniendo cada frame de 64x64 píxeles)
2. Verificar que los frames estén perfectamente alineados
3. Mantener la transparencia del fondo

## Notas para Phaser

En Phaser, después de convertir los archivos, actualiza las rutas en los archivos JavaScript para que apunten a los archivos PNG en lugar de SVG:

```javascript
// Cambiar esto:
this.load.image('background-forest', '/assets/images/backgrounds/forest.svg');

// Por esto:
this.load.image('background-forest', '/assets/images/backgrounds/forest.png');
``` 
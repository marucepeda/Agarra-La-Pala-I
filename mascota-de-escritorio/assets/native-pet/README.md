# La Pala — assets para mascota nativa

Esta carpeta separa los assets de distribución de los sprites fuente de la aplicación de escritorio.

## Estado actual

`provisional/la-pala-v2-idle-refined.png` cumple el formato técnico Pets v2: PNG RGBA transparente, 1536×2288 píxeles, cuadrícula de 8×11 y 73 celdas requeridas.

Es una **hoja provisional**, no una publicación final de arte. La fila `idle` fue corregida con parpadeo de cuerpo completo. Persisten placeholders visuales en direcciones de mirada y en algunos estados de actividad; no deben presentarse como animaciones genuinas.

## Contenido apto para revisión local

- `provisional/la-pala-v2-idle-refined.png`: atlas v2 estructuralmente válido.
- `provisional/contact-sheet-refined.png`: contacto para revisión humana.
- `provisional/idle-animation-preview.gif`: vista del ciclo de reposo refinado.
- `provisional/*validation*.json`: evidencia de validación estructural y local.
- `provisional/frame-provenance.json`: trazabilidad de cada cuadro y sus límites.

## Antes de publicar o activar

1. Reemplazar todos los placeholders por poses genuinas aprobadas.
2. Revisar el sheet visualmente, incluidos los 16 sentidos de mirada.
3. Ejecutar los validadores técnico y semántico sobre los bytes finales.
4. Revisar el `git diff --cached` para que no incluya configuraciones, diagnósticos, datos personales ni trabajo temporal.
5. Pedir aprobación explícita antes de compartir o hacer `push`.

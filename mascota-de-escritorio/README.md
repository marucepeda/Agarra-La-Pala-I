# Mascota de escritorio para Windows

Una mascota pixel-art para el escritorio de Windows, desarrollada con Python y PySide6.

## Funcionalidades

- Ventana sin bordes, con fondo transparente y siempre visible.
- Movimiento de la ventana mediante arrastre.
- Control desde el menú contextual y la bandeja del sistema.
- Ajuste de tamaño y persistencia de la configuración local.
- Modo de interacción para permitir clics a través de la mascota.
- Animaciones de reposo, caminar, saludar, sentarse, dormir y escribir.

La animación de reposo conserva el movimiento sutil original y el parpadeo generado a partir del sprite maestro.

## Requisitos

- Windows 10 u 11.
- Python 3.10 o posterior.

## Instalación

Abrí PowerShell en la carpeta del proyecto y ejecutá:

```powershell
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
```

## Ejecución

```powershell
py -3 main.py
```

La mascota aparecerá en el escritorio. Usá el botón izquierdo para arrastrarla y el botón derecho para abrir su menú.

La aplicación puede crear `settings.json` para guardar preferencias locales. Ese archivo no forma parte del repositorio.

## Estructura

- `main.py`: aplicación principal.
- `mascota_master.png`: sprite maestro del reposo.
- `sprites_revision_v2/`: sprites utilizados por las animaciones.
- `assets/native-pet/`: assets de revisión para una futura mascota nativa. El sheet v2 actual está validado técnicamente, pero se marca como **provisional** mientras existan poses o direcciones pendientes de arte genuino.
- `requirements.txt`: dependencias de Python.

## Tecnologías

- Python
- PySide6 / Qt
- Pillow

## Estado

Proyecto personal en desarrollo.

"""Mascota de escritorio para Windows (Fase 1).

El diseño separa la ventana de la fuente de fotogramas para poder sumar
animaciones PNG sin modificar la lógica de arrastre, configuración o menús.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image
from PySide6.QtCore import QPoint, QRect, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QCursor, QIcon, QImage, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QWidget,
)


APP_DIR = Path(__file__).resolve().parent
MASTER_SPRITE_PATH = APP_DIR / "mascota_master.png"
SPRITES_DIR = APP_DIR / "sprites_revision_v2"
SPRITE_CANVAS_SIZE = (25, 51)
SETTINGS_PATH = APP_DIR / "settings.json"
# El sprite maestro es pixel art de baja resolución. Se amplía una vez, con
# vecino más cercano, antes de aplicar la escala que elige la persona usuaria.
SPRITE_MAGNIFICATION = 8
DEFAULT_SCALE = 0.70
MIN_SCALE = 0.40
MAX_SCALE = 1.40


@dataclass
class Settings:
    """Preferencias persistentes; se guardan junto a la aplicación."""

    scale: float = DEFAULT_SCALE
    x: int | None = None
    y: int | None = None
    movement_enabled: bool = True
    interaction_enabled: bool = True

    @classmethod
    def load(cls) -> "Settings":
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            x = raw.get("x")
            y = raw.get("y")
            return cls(
                scale=float(raw.get("scale", DEFAULT_SCALE)),
                x=None if x is None else int(x),
                y=None if y is None else int(y),
                movement_enabled=bool(raw.get("movement_enabled", True)),
                # Conserva settings.json de la versión anterior: el movimiento
                # habilitado equivale a una mascota interactiva inicialmente.
                interaction_enabled=bool(
                    raw.get("interaction_enabled", raw.get("movement_enabled", True))
                ),
            )
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self) -> None:
        SETTINGS_PATH.write_text(
            json.dumps(
                {
                    "scale": self.scale,
                    "x": self.x,
                    "y": self.y,
                    "movement_enabled": self.movement_enabled,
                    "interaction_enabled": self.interaction_enabled,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


class AnimationController:
    """Punto de extensión para futuras animaciones por fotogramas PNG.

    Cuando haya PNGs nuevos, registrar cada secuencia con ``register`` y llamar
    ``play``. Un QTimer reutilizable cambiará los pixmaps sin crear ventanas.
    La secuencia inicial combina el reposo y el parpadeo del sprite maestro.
    """

    def __init__(self, on_frame_changed) -> None:
        self._on_frame_changed = on_frame_changed
        self._animations: dict[str, tuple[Sequence[QPixmap], int]] = {}
        self._frames: Sequence[QPixmap] = ()
        self._index = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._next_frame)

    def register(self, name: str, frames: Sequence[QPixmap], interval_ms: int) -> None:
        if not frames:
            raise ValueError("Una animación necesita al menos un fotograma.")
        self._animations[name] = (frames, interval_ms)

    def play(self, name: str) -> None:
        frames, interval_ms = self._animations[name]
        self._timer.stop()
        self._frames = frames
        self._index = 0
        self._on_frame_changed(self._frames[0])
        if len(frames) > 1:
            self._timer.start(interval_ms)

    def _next_frame(self) -> None:
        self._index = (self._index + 1) % len(self._frames)
        self._on_frame_changed(self._frames[self._index])


def _magnified_sprite(image: QImage) -> QPixmap:
    """Convierte el sprite maestro en pixel art visible sin suavizarlo."""
    enlarged = image.scaled(
        image.width() * SPRITE_MAGNIFICATION,
        image.height() * SPRITE_MAGNIFICATION,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    return QPixmap.fromImage(enlarged)


def _load_animation_frame(filename: str) -> QPixmap:
    """Carga el PNG sin reducir sus píxeles y lo centra en un lienzo común."""
    path = SPRITES_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el fotograma: {path}")

    with Image.open(path) as opened:
        sprite = opened.convert("RGBA")

    # El lienzo admite el mayor sprite de la versión 2 (81 x 111).
    # No se reduce la figura: así se preservan ojos y detalles pequeños.
    canvas_width, canvas_height = 81, 111
    if sprite.width > canvas_width or sprite.height > canvas_height:
        raise RuntimeError(
            f"{filename} mide {sprite.size}; supera el lienzo "
            f"de {(canvas_width, canvas_height)}."
        )

    canvas = Image.new(
        "RGBA", (canvas_width, canvas_height), (0, 0, 0, 0)
    )
    x = (canvas_width - sprite.width) // 2
    y = canvas_height - sprite.height
    canvas.alpha_composite(sprite, (x, y))

    image = QImage(
        canvas.tobytes(),
        canvas_width,
        canvas_height,
        canvas_width * 4,
        QImage.Format.Format_RGBA8888,
    ).copy()

    # Ampliación entera por vecino más cercano; sin suavizado ni reducción.
    enlarged = image.scaled(
        canvas_width * 4,
        canvas_height * 4,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    return QPixmap.fromImage(enlarged)


def _idle_frame(source: QPixmap, vertical_offset: int, blinking: bool = False) -> QPixmap:
    """Crea un fotograma de reposo: leve balanceo y, opcionalmente, ojos cerrados."""
    frame = QPixmap(source.size())
    frame.fill(Qt.GlobalColor.transparent)
    painter = QPainter(frame)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    painter.drawPixmap(0, vertical_offset, source)

    if blinking:
        # Los ojos del sprite maestro ocupan una línea de tres píxeles. Se
        # dibujan párpados horizontales en lugar de modificar el PNG aprobado.
        pixel = SPRITE_MAGNIFICATION
        painter.fillRect(QRect(9 * pixel, (12 + vertical_offset) * pixel, 8 * pixel, pixel), Qt.GlobalColor.white)
        painter.fillRect(QRect(9 * pixel, (13 + vertical_offset) * pixel, 3 * pixel, pixel), Qt.GlobalColor.black)
        painter.fillRect(QRect(14 * pixel, (13 + vertical_offset) * pixel, 3 * pixel, pixel), Qt.GlobalColor.black)
    painter.end()
    return frame


def create_idle_blink_frames(source: QPixmap) -> list[QPixmap]:
    """Devuelve un ciclo pausado de respiración con un parpadeo breve."""
    # Doce posiciones de reposo (~1,4 s) y dos de párpado cerrado (240 ms).
    resting_offsets = (0, 0, -1, -1, 0, 0, 1, 1, 0, 0, -1, 0)
    frames = [_idle_frame(source, offset) for offset in resting_offsets]
    frames.extend((_idle_frame(source, 0, blinking=True), _idle_frame(source, 0, blinking=True)))
    return frames


class PetWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()
        self._drag_offset: QPoint | None = None
        self._source_pixmap = self._load_image()
        self._current_pixmap = self._source_pixmap

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._apply_interaction_mode(self.settings.interaction_enabled, restore_visibility=False)

        self.animations = AnimationController(self._set_frame)

        # Reposo original: movimiento sutil y parpadeo sobre el sprite maestro.
        self.animations.register(
            "idle", create_idle_blink_frames(self._source_pixmap), 120
        )
        # El blink independiente se mantiene provisionalmente como antes.
        blink = _load_animation_frame("blink.png")
        self.animations.register("blink", [blink], 120)
        self.animations.register(
            "walk",
            [_load_animation_frame("walk_1.png"), _load_animation_frame("walk_2.png")],
            180,
        )
        self.animations.register("wave", [_load_animation_frame("wave.png")], 500)
        self.animations.register("sit", [_load_animation_frame("sit.png")], 500)
        self.animations.register("sleep", [_load_animation_frame("sleep.png")], 500)
        self.animations.register(
            "typing",
            [_load_animation_frame("typing_1.png"), _load_animation_frame("typing_2.png")],
            180,
        )
        self.animations.play("idle")
        self._create_tray_icon()
        self._apply_size()
        self._restore_position()

    def _load_image(self) -> QPixmap:
        if not MASTER_SPRITE_PATH.is_file():
            raise FileNotFoundError(f"No se encontró el sprite maestro aprobado: {MASTER_SPRITE_PATH}")
        reader = QImageReader(str(MASTER_SPRITE_PATH))
        reader.setAutoTransform(False)
        image = reader.read()
        if image.isNull():
            raise RuntimeError(f"No se pudo abrir mascota_master.png: {reader.errorString()}")
        if not image.hasAlphaChannel():
            raise RuntimeError("El sprite maestro debe incluir transparencia.")
        return _magnified_sprite(image)

    def _set_frame(self, pixmap: QPixmap) -> None:
        self._current_pixmap = pixmap
        self._apply_size()

    def _apply_size(self) -> None:
        scale = max(MIN_SCALE, min(MAX_SCALE, self.settings.scale))
        self.settings.scale = scale
        width = max(1, round(self._current_pixmap.width() * scale))
        height = max(1, round(self._current_pixmap.height() * scale))
        self.resize(width, height)
        self.update()

    def _restore_position(self) -> None:
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        available = screen.availableGeometry()
        x = self.settings.x if self.settings.x is not None else available.left() + 40
        y = self.settings.y if self.settings.y is not None else available.top() + 40
        self.move(self._clamped_position(QPoint(x, y)))

    def _clamped_position(self, position: QPoint) -> QPoint:
        """Mantiene al menos una parte de la mascota dentro de su monitor."""
        screen = QApplication.screenAt(position + QPoint(self.width() // 2, self.height() // 2))
        screen = screen or QApplication.primaryScreen()
        area = screen.availableGeometry()
        visible_margin = 32
        min_x = area.left() - self.width() + visible_margin
        max_x = area.right() - visible_margin
        min_y = area.top() - self.height() + visible_margin
        max_y = area.bottom() - visible_margin
        return QPoint(max(min_x, min(position.x(), max_x)), max(min_y, min(position.y(), max_y)))

    def paintEvent(self, event) -> None:  # noqa: N802 - nombre impuesto por Qt
        from PySide6.QtGui import QPainter

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(self.rect(), self._current_pixmap)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.settings.interaction_enabled:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(self._clamped_position(event.globalPosition().toPoint() - self._drag_offset))
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self._save_position()
            event.accept()

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        animation_menu = menu.addMenu("Animación")
        for label, animation_name in (
            ("Reposo", "idle"), ("Parpadeo", "blink"),
            ("Caminar", "walk"), ("Saludar", "wave"),
            ("Sentarse", "sit"), ("Dormir", "sleep"),
            ("Escribir", "typing"),
        ):
            action = animation_menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, name=animation_name: self.animations.play(name)
            )
        menu.addSeparator()
        size_menu = menu.addMenu("Tamaño")
        for label, scale in (("Pequeña", 0.50), ("Mediana", 0.70), ("Grande", 0.95), ("Extra grande", 1.20)):
            action = size_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(abs(self.settings.scale - scale) < 0.01)
            action.triggered.connect(lambda checked=False, value=scale: self._set_scale(value))

        menu.addSeparator()
        interaction = menu.addAction("Modo interacción (arrastrar y menú)")
        interaction.setCheckable(True)
        interaction.setChecked(self.settings.interaction_enabled)
        interaction.toggled.connect(self._set_interaction_enabled)
        menu.addAction("Ocultar mascota", self.hide)
        menu.addSeparator()
        menu.addAction("Salir", QApplication.quit)
        menu.exec(global_pos)

    def _create_tray_icon(self) -> None:
        self.tray = QSystemTrayIcon(QIcon(self._source_pixmap), self)
        tray_menu = QMenu(self)
        animation_menu = tray_menu.addMenu("Animación")
        for label, animation_name in (
            ("Reposo", "idle"), ("Parpadeo", "blink"),
            ("Caminar", "walk"), ("Saludar", "wave"),
            ("Sentarse", "sit"), ("Dormir", "sleep"),
            ("Escribir", "typing"),
        ):
            action = animation_menu.addAction(label)
            action.triggered.connect(
                lambda checked=False, name=animation_name: self.animations.play(name)
            )
        self.visibility_action = tray_menu.addAction("Ocultar mascota", self._toggle_visibility)
        self.interaction_action = tray_menu.addAction("Modo interacción (arrastrar y menú)")
        self.interaction_action.setCheckable(True)
        self.interaction_action.setChecked(self.settings.interaction_enabled)
        self.interaction_action.toggled.connect(self._set_interaction_enabled)
        tray_menu.addAction("Salir", QApplication.quit)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_visibility()

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
            self.visibility_action.setText("Mostrar mascota")
        else:
            self.show()
            self.visibility_action.setText("Ocultar mascota")

    def _set_scale(self, scale: float) -> None:
        self.settings.scale = scale
        self._apply_size()
        self._save_position()

    def _set_interaction_enabled(self, enabled: bool) -> None:
        self._apply_interaction_mode(enabled)
        self.settings.interaction_enabled = enabled
        self.settings.movement_enabled = enabled  # Compatibilidad con la configuración anterior.
        # El menú de la bandeja debe reflejar cambios hechos desde el menú de
        # la mascota; de lo contrario no podría restaurar click-through.
        blocker = QSignalBlocker(self.interaction_action)
        self.interaction_action.setChecked(enabled)
        del blocker
        self.settings.save()

    def _apply_interaction_mode(self, enabled: bool, restore_visibility: bool = True) -> None:
        """Activa o desactiva el click-through nativo de Windows mediante Qt."""
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, not enabled)
        if restore_visibility and was_visible:
            # Qt reaplica las flags de una ventana nativa al mostrarla de nuevo.
            self.show()

    def _save_position(self) -> None:
        self.settings.x = self.x()
        self.settings.y = self.y()
        self.settings.save()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_position()
        self.tray.hide()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    try:
        pet = PetWindow()
    except (OSError, RuntimeError) as error:
        QMessageBox.critical(None, "Mascota de escritorio", str(error))
        return 1
    pet.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

"""
Загрузчик картинок на Pillow: масштабирование, эффекты (hover / pressed / disabled),
кэш. Если файла нет — возвращает None, а интерфейс рисует запасной вариант.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageEnhance, ImageTk

from app.utils import log

Size2 = tuple[int, int]


class Assets:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self._pil: dict[tuple, Optional[Image.Image]] = {}
        self._tk: dict[tuple, Optional[ImageTk.PhotoImage]] = {}

    # ------------------------------------------------------------------
    # Низкий уровень
    # ------------------------------------------------------------------
    def _load(self, name: str, trim: bool = False) -> Optional[Image.Image]:
        key = (name, trim)
        if key not in self._pil:
            try:
                img = Image.open(self.dir / name).convert("RGBA")
                if trim:  # срезаем прозрачные поля
                    bbox = img.getchannel("A").getbbox()
                    if bbox:
                        img = img.crop(bbox)
                self._pil[key] = img
            except Exception as e:
                log.warning(f"Asset '{name}': {e}")
                self._pil[key] = None
        return self._pil[key]

    @staticmethod
    def _effect(img: Image.Image, effect: Optional[str]) -> Image.Image:
        """Меняет яркость/насыщенность, не трогая альфа-канал."""
        if not effect:
            return img
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        if effect == "hover":
            rgb = ImageEnhance.Brightness(rgb).enhance(1.18)
        elif effect == "pressed":
            rgb = ImageEnhance.Brightness(rgb).enhance(0.78)
        elif effect == "disabled":
            rgb = ImageEnhance.Color(rgb).enhance(0.15)
            rgb = ImageEnhance.Brightness(rgb).enhance(0.6)
        return Image.merge("RGBA", (*rgb.split(), a))

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------
    def photo(self, name: str, *, size: Size2 | None = None,
              width: int | None = None, height: int | None = None,
              trim: bool = False, effect: str | None = None
              ) -> Optional[ImageTk.PhotoImage]:
        """Картинка для tkinter. size — точный размер; width/height — с сохранением пропорций."""
        key = (name, size, width, height, trim, effect)
        if key in self._tk:
            return self._tk[key]

        img = self._load(name, trim)
        result = None
        if img is not None:
            if size:
                target = size
            elif width:
                target = (width, max(1, round(img.height * width / img.width)))
            elif height:
                target = (max(1, round(img.width * height / img.height)), height)
            else:
                target = img.size
            if target != img.size:
                img = img.resize(target, Image.LANCZOS)
            result = ImageTk.PhotoImage(self._effect(img, effect))
        self._tk[key] = result
        return result

    def size_of(self, name: str, *, width: int | None = None,
                trim: bool = False) -> Size2:
        """Размер картинки после масштабирования по ширине (для раскладки)."""
        img = self._load(name, trim)
        if img is None:
            return (width or 100, 40)
        if width:
            return (width, max(1, round(img.height * width / img.width)))
        return img.size

    def button_states(self, normal: str, *, pressed: str | None = None,
                      size: Size2 | None = None, width: int | None = None,
                      trim: bool = False) -> dict:
        """
        Набор состояний кнопки: normal / hover / pressed / active / disabled.
        Если картинки для pressed нет — затемняем normal.
        Пустой словарь = файла нет (кнопка нарисуется запасным цветом).
        """
        kw = dict(size=size, width=width, trim=trim)
        base = self.photo(normal, **kw)
        if base is None:
            return {}
        press = (self.photo(pressed, **kw) if pressed else None) \
            or self.photo(normal, effect="pressed", **kw)
        return {
            "normal":   base,
            "hover":    self.photo(normal, effect="hover", **kw),
            "pressed":  press,
            "active":   press,
            "disabled": self.photo(normal, effect="disabled", **kw),
        }

    def cover(self, name: str, size: Size2, *,
              fade_bottom: float = 0.0) -> Optional[ImageTk.PhotoImage]:
        """
        Фон «cover»: заполняет область целиком, лишнее обрезается по центру.
        fade_bottom (0..1) — затемнение низа, чтобы текст читался поверх сцены.
        """
        img = self._load(name)
        if img is None:
            return None
        tw, th = size
        scale = max(tw / img.width, th / img.height)
        nw, nh = max(tw, round(img.width * scale)), max(th, round(img.height * scale))
        out = img.convert("RGB").resize((nw, nh), Image.LANCZOS)
        left, top = (nw - tw) // 2, (nh - th) // 2
        out = out.crop((left, top, left + tw, top + th))

        if fade_bottom > 0:
            band = int(th * 0.45)
            mask = Image.new("L", (tw, th), 0)
            px = mask.load()
            for y in range(th - band, th):
                v = int(255 * fade_bottom * (y - (th - band)) / band)
                for x in range(tw):
                    px[x, y] = v
            out.paste(Image.new("RGB", (tw, th), (0, 0, 0)), (0, 0), mask)
        return ImageTk.PhotoImage(out)

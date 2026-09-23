"""Главная: фон-сцена, новости, кнопка PLAY NOW и статус сервера."""
import tkinter as tk

from ui.pages.base import BasePage
from ui.theme import C, F
from ui.widgets import ImageButton
from app.utils import get_stat
import threading
# ---- Заглушки: замените реальными данными ---------------------------------
NEWS = [
    ("МЕГА-КРАНЫ",           "Представлены новые огромные краны для ваших построек."),
    ("НОВЫЙ ЛОКОМОТИВ",      "Обновление локомотивов теперь доступно всем игрокам."),
    ("АВТОМАТИЧЕСКАЯ ФЕРМА", "Добавлена автоматическая ферма из мода mobs."),
    ("ТОЧНАЯ МЕХАНИКА",      "Новые точные инструменты для вашей фабрики."),
]
SERVER_STATS = [
    ("Игроки:", "-"),
    ("Пинг:",   "-"),
    ("Статус:", "-"),
]
# ---------------------------------------------------------------------------

MARGIN = 20
PLAY_WIDTH = 250


class HomePage(BasePage):
    key = "home"
    title = "Главная"

    def build(self) -> None:
        self._bg_photo = None
        self._resize_job = None

        self.canvas = tk.Canvas(self, bg="#1a1108", highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg_item = self.canvas.create_image(0, 0, anchor="nw")

        # self._build_news()
        self._build_play()
        self._build_stats()

        self.canvas.bind("<Configure>", self._on_resize)

    # ------------------------------------------------------------------
    def _build_news(self) -> None:
        news = tk.Frame(self, bg=C.SIDEBAR, bd=1, relief="solid")
        news.place(x=MARGIN, y=MARGIN, width=280, height=352)
        news.pack_propagate(False)

        tk.Label(news, text="НОВОСТИ СЕРВЕРА", font=F.H2,
                 bg=C.SIDEBAR, fg=C.ACCENT).pack(pady=(12, 8))
        tk.Frame(news, bg=C.ACCENT, height=1).pack(fill="x", padx=15)

        box = tk.Frame(news, bg=C.SIDEBAR)
        box.pack(fill="both", expand=True, padx=10, pady=8)
        for title, desc in NEWS:
            item = tk.Frame(box, bg=C.PANEL_ALT, padx=8, pady=6)
            item.pack(fill="x", pady=3)
            tk.Label(item, text=title, font=F.SMALL_B, bg=C.PANEL_ALT, fg="white",
                     wraplength=230, justify="left").pack(anchor="w")
            tk.Label(item, text=desc, font=F.TINY, bg=C.PANEL_ALT, fg="#aaa",
                     wraplength=230, justify="left").pack(anchor="w", pady=(2, 0))

    def _build_play(self) -> None:
        """PLAY NOW и подпись рисуются прямо на фоне — прозрачность PNG сохраняется."""
        assets = self.ctx.assets
        self._play_size = assets.size_of("play.png", width=PLAY_WIDTH, trim=True)
        states = assets.button_states("play.png", width=PLAY_WIDTH, trim=True)

        self.play_btn = ImageButton(self.canvas, 0, 0, states, size=self._play_size,
                                    command=self.ctx.controller.play)

        self._ver_shadow = self.canvas.create_text(0, 0, text="", font=F.SMALL_B, fill="black")
        self._ver_text = self.canvas.create_text(0, 0, text="", font=F.SMALL_B, fill=C.TEXT)

    def _build_stats(self) -> None:
        self.stats = tk.Frame(
            self,
            bg=C.PANEL,
            bd=1,
            relief="solid",
            padx=15,
            pady=10
        )

        tk.Label(
            self.stats,
            text="СТАТУС СЕРВЕРА",
            font=F.SMALL_B,
            bg=C.PANEL,
            fg=C.ACCENT
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            pady=(0, 6)
        )

        tk.Frame(
            self.stats,
            bg=C.BORDER,
            height=1
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 6)
        )

        self._stat_labels = {}

        # Создаём Label один раз
        for i, (key, value) in enumerate([
            ("Игроки:", "-"),
            ("Пинг:", "-"),
            ("Статус:", "-"),
        ]):
            tk.Label(
                self.stats,
                text=key,
                bg=C.PANEL,
                fg="#888",
                font=F.SMALL
            ).grid(
                row=i + 2,
                column=0,
                sticky="w",
                pady=1
            )

            value_label = tk.Label(
                self.stats,
                text=value,
                bg=C.PANEL,
                fg="white",
                font=F.SMALL
            )
            value_label.grid(
                row=i + 2,
                column=1,
                sticky="e",
                padx=(15, 0),
                pady=1
            )

            self._stat_labels[key] = value_label

        self._stats_job = None
        self._stats_thread = None

        self._update_stats()

    def _update_stats(self) -> None:
        # Не запускаем новый запрос, если предыдущий ещё выполняется
        if self._stats_thread is None or not self._stats_thread.is_alive():
            self._stats_thread = threading.Thread(
                target=self._get_stats_thread,
                daemon=True
            )
            self._stats_thread.start()

        # Следующее обновление через 3 секунды
        self._stats_job = self.after(3000, self._update_stats)


    def _get_stats_thread(self) -> None:
        try:
            stats = get_stat()

        except Exception:
            stats = [
                ("Игроки:", "-"),
                ("Пинг:", "-"),
                ("Статус:", "Недоступен"),
            ]

        # В Tkinter нельзя менять виджеты из другого потока.
        # Поэтому возвращаемся в главный поток.
        self.after(0, lambda: self._apply_stats(stats))


    def _apply_stats(self, stats) -> None:
        for key, value in stats:
            label = self._stat_labels.get(key)

            if label is not None:
                label.config(text=value)
    # ------------------------------------------------------------------
    # Раскладка / фон
    # ------------------------------------------------------------------
    def _on_resize(self, event) -> None:
        if event.width < 10 or event.height < 10:
            return
        self._layout(event.width, event.height)
        # фон пересобираем с задержкой, чтобы не тормозить при перетаскивании размера
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(
            80, lambda: self._draw_background(event.width, event.height))

    def _draw_background(self, w: int, h: int) -> None:
        self._resize_job = None
        photo = self.ctx.assets.cover("background.png", (w, h), fade_bottom=0.6)
        if photo is not None:
            self._bg_photo = photo  # держим ссылку, иначе tkinter «съест» картинку
            self.canvas.itemconfigure(self._bg_item, image=photo)

    def _layout(self, w: int, h: int) -> None:
        pw, ph = self._play_size
        cx = MARGIN + pw // 2
        self.play_btn.move(cx, h - MARGIN - 26 - ph // 2)

        ty = h - MARGIN - 8
        for item, dy in ((self._ver_shadow, 1), (self._ver_text, 0)):
            self.canvas.coords(item, cx + dy, ty + dy)
        self.stats.place(x=MARGIN + pw + 20, y=h - MARGIN, anchor="sw")

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        # версия Minecraft могла поменяться после обновления сборки
        text = self.ctx.controller.version_label()
        self.canvas.itemconfigure(self._ver_text, text=text)
        self.canvas.itemconfigure(self._ver_shadow, text=text)

    def on_busy(self, busy: bool) -> None:
        self.play_btn.set_enabled(not busy)

import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path

from app.utils import log


class HomePage(tk.Frame):
    """
    Главная страница лаунчера.

    Раскладка:
      ┌────────────────────────────────────────────┐
      │ ┌─── новости ──┐                            │
      │ │              │                            │
      │ │              │       [фон]                │
      │ │              │                            │
      │ └──────────────┘                            │
      │                                             │
      │ [PLAY]  [статистика]                        │
      └────────────────────────────────────────────┘
    """

    BG        = "#2b2b2b"
    ACCENT    = "#8B5A2B"
    ACCENT_HOV= "#A56A35"
    TEXT      = "#e0e0e0"
    TEXT_DIM  = "#888888"
    PANEL_BG  = "#1f1f1f"
    NEWS_BG   = "#1a1a1a"
    GREEN     = "#4CAF50"
    GREEN_HOV = "#45a049"

    def __init__(self, master, assets: Path, cfg: dict, on_play):
        super().__init__(master, bg=self.BG)
        self.assets = Path(assets)
        self.cfg = cfg
        self.on_play = on_play

        self._photos = {}

        self.header_font = tkfont.Font(family="Arial", size=13, weight="bold")
        self.small_font  = tkfont.Font(family="Arial", size=9)
        self.normal_font = tkfont.Font(family="Arial", size=10)

        self._build()

    # ------------------------------------------------------------------
    # Сборка страницы
    # ------------------------------------------------------------------
    def _build(self):
        # --- Фон ---
        self._build_background()

        # --- Верхний блок: новости слева ---
        self._build_news()

        # --- Нижний блок: PLAY + статистика ---
        self._build_bottom()

        # --- Статус + прогресс (внизу поверх фона) ---
        self._build_status()

    # ------------------------------------------------------------------
    # Фон
    # ------------------------------------------------------------------
    def _build_background(self):
        self.bg_canvas = tk.Canvas(self, bg="#1a1108", highlightthickness=0, bd=0)
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        try:
            bg = tk.PhotoImage(file=str(self.assets / "background.png"))
            self._photos["background"] = bg
            self.bg_canvas.create_image(0, 0, anchor="nw", image=bg, tags=("bg",))
            # масштабирование при изменении размера
            self.bg_canvas.bind("<Configure>", self._rescale_bg)
        except Exception as e:
            log.warning(f"Background: {e}")
            self.bg_canvas.create_text(
                400, 300,
                text="[Фон: assets/background.png]",
                fill="#666", font=("Arial", 20),
            )

    def _rescale_bg(self, event):
        """Простое масштабирование картинки под размер окна (без PIL)."""
        if "background" not in self._photos:
            return
        # В чистом tkinter нормальное масштабирование невозможно без PIL,
        # поэтому просто центрируем картинку.
        cw = event.width
        ch = event.height
        self.bg_canvas.coords("bg", cw // 2, ch // 2)
        self.bg_canvas.itemconfig("bg", anchor="center")

    # ------------------------------------------------------------------
    # Новости (слева сверху)
    # ------------------------------------------------------------------
    def _build_news(self):
        news = tk.Frame(self, bg=self.NEWS_BG, bd=1, relief="solid")
        news.place(relx=0.02, rely=0.04, anchor="nw", width=280, height=320)
        news.pack_propagate(False)

        # Заголовок
        tk.Label(
            news, text="НОВОСТИ СЕРВЕРА",
            font=self.header_font,
            bg=self.NEWS_BG, fg=self.ACCENT,
        ).pack(pady=(12, 8))

        tk.Frame(news, bg=self.ACCENT, height=1).pack(fill="x", padx=15)

        # Список
        items_container = tk.Frame(news, bg=self.NEWS_BG)
        items_container.pack(fill="both", expand=True, padx=10, pady=8)

        for title, desc in [
            ("МЕГА-КРАНЫ",          "Представлены новые огромные краны для ваших построек."),
            ("НОВЫЙ ЛОКОМОТИВ",     "Обновление локомотивов теперь доступно всем игрокам."),
            ("АВТОМАТИЧЕСКАЯ ФЕРМА", "Добавлена автоматическая ферма из мода mobs."),
            ("ТОЧНАЯ МЕХАНИКА",     "Новые точные инструменты для вашей фабрики."),
        ]:
            item = tk.Frame(items_container, bg="#252525", padx=8, pady=6)
            item.pack(fill="x", pady=3)

            tk.Label(
                item, text=title,
                font=("Arial", 9, "bold"),
                bg="#252525", fg="white",
                wraplength=230, justify="left",
            ).pack(anchor="w")
            tk.Label(
                item, text=desc,
                font=("Arial", 8),
                bg="#252525", fg="#aaa",
                wraplength=230, justify="left",
            ).pack(anchor="w", pady=(2, 0))

    # ------------------------------------------------------------------
    # Нижний блок: PLAY + статистика
    # ------------------------------------------------------------------
    def _build_bottom(self):
        bottom = tk.Frame(self, bg=self.BG)
        # слева внизу
        bottom.place(relx=0.02, rely=0.97, anchor="sw")

        # --- PLAY ---
        play_frame = tk.Frame(bottom, bg=self.BG)
        play_frame.pack(side="left", anchor="s")

        self.play_btn = tk.Button(
            play_frame, text="PLAY",
            font=("Arial", 28, "bold"),
            bg=self.GREEN, fg="white",
            bd=0, padx=55, pady=12,
            activebackground=self.GREEN_HOV,
            activeforeground="white",
            cursor="hand2",
            command=self.on_play,
        )
        self.play_btn.pack()

        tk.Label(
            play_frame,
            text=f"NeoForge | MC {self.cfg.get('minecraft_version', '?')}",
            bg=self.BG, fg=self.TEXT_DIM, font=self.small_font,
        ).pack(pady=(3, 0))

        # --- Статистика (справа от PLAY) ---
        stats = tk.Frame(bottom, bg=self.PANEL_BG, bd=1,
                         relief="solid", padx=15, pady=10)
        stats.pack(side="left", anchor="s", padx=(20, 0))

        tk.Label(
            stats, text="СТАТУС СЕРВЕРА",
            font=("Arial", 9, "bold"),
            bg=self.PANEL_BG, fg=self.ACCENT,
        ).grid(row=0, column=0, columnspan=2, pady=(0, 6))

        tk.Frame(stats, bg="#3a3a3a", height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6),
        )

        for i, (k, v) in enumerate([
            ("Игроки:", "1,245 / 2,000"),
            ("Пинг:",   "23мс (Отличный)"),
            ("Статус:", "Онлайн"),
        ]):
            tk.Label(
                stats, text=k,
                bg=self.PANEL_BG, fg="#888", font=self.small_font,
            ).grid(row=i + 2, column=0, sticky="w", pady=1)
            tk.Label(
                stats, text=v,
                bg=self.PANEL_BG, fg="white", font=self.small_font,
            ).grid(row=i + 2, column=1, sticky="e", padx=(15, 0), pady=1)

    # ------------------------------------------------------------------
    # Статус + прогресс (поверх фона, по центру снизу)
    # ------------------------------------------------------------------
    def _build_status(self):
        wrapper = tk.Frame(self, bg=self.NEWS_BG)
        wrapper.place(relx=0.5, rely=0.97, anchor="s", relwidth=0.4)

        self._status_label = tk.Label(
            wrapper,
            text="Статус: —",
            bg=self.NEWS_BG, fg="#e7d3a7",
            font=("Arial", 9, "bold"),
            anchor="w", padx=8, pady=3,
        )
        self._status_label.pack(fill="x")

        self._pb_canvas = tk.Canvas(
            wrapper, height=10,
            bg="#241509", highlightthickness=0, bd=0,
        )
        self._pb_canvas.pack(fill="x")

        self._pb_bg = self._pb_canvas.create_rectangle(
            0, 0, 2000, 10, fill="#241509", outline="#7a5a3a",
        )
        self._pb = self._pb_canvas.create_rectangle(
            0, 0, 0, 10, fill="#c58b3a", outline="",
        )
        self._pb_canvas.bind("<Configure>", lambda e: self._redraw_progress())

        self._pb_value = 0

    # ==================================================================
    #                    Публичные методы
    # ==================================================================
    def set_status(self, text: str, color: str = "#e7d3a7"):
        self._status_label.config(text=f"Статус: {text}", fg=color)

    def update_progress(self, pct: int, text: str = ""):
        pct = max(0, min(100, pct))
        self._pb_value = pct
        self._redraw_progress()
        # статус показывает текст
        if text:
            self._status_label.config(text=f"Статус: {text}")

    def _redraw_progress(self):
        w = self._pb_canvas.winfo_width()
        if w <= 1:
            w = 2000
        new_x = w * self._pb_value / 100
        self._pb_canvas.coords(self._pb, 0, 0, new_x, 10)
        self._pb_canvas.coords(self._pb_bg, 0, 0, w, 10)

    def set_play_enabled(self, enabled: bool):
        if enabled:
            self.play_btn.config(state="normal", bg=self.GREEN)
        else:
            self.play_btn.config(state="disabled", bg="#666")
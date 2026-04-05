"""
common.py — общий протокол и стиль для сервера и клиента.
"""

import socket
import time
import tkinter as tk
from tkinter import scrolledtext

# ──────────────────────────────────────────────────────────────
# Протокол: 4-байтовый заголовок длины + UTF-8 тело
# ──────────────────────────────────────────────────────────────

HEADER   = 4
ENCODING = "utf-8"


def send_msg(sock: socket.socket, text: str) -> None:
    """Отправить текстовое сообщение."""
    data   = text.encode(ENCODING)
    length = len(data).to_bytes(HEADER, "big")
    sock.sendall(length + data)


def recv_msg(sock: socket.socket) -> str | None:
    """Получить одно сообщение. None — соединение разорвано."""
    raw_len = _recv_exactly(sock, HEADER)
    if raw_len is None:
        return None
    msg_len  = int.from_bytes(raw_len, "big")
    raw_data = _recv_exactly(sock, msg_len)
    if raw_data is None:
        return None
    return raw_data.decode(ENCODING)


def _recv_exactly(sock: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except OSError:
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


def port_is_free(port: int) -> bool:
    """True если порт свободен."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False


# ──────────────────────────────────────────────────────────────
# Цвета и шрифты
# ──────────────────────────────────────────────────────────────

DARK_BG    = "#0d0f14"
PANEL_BG   = "#13161e"
ACCENT     = "#00e5c8"
ACCENT2    = "#7c5cfc"
TEXT_COLOR = "#e8eaf0"
MUTED      = "#555a6e"
ENTRY_BG   = "#1a1e2a"

FONT_MAIN  = ("Consolas", 11)
FONT_TITLE = ("Consolas", 16, "bold")
FONT_NICK  = ("Consolas", 10, "bold")
FONT_SMALL = ("Consolas", 9)


def style_btn(btn: tk.Button, accent: bool = True) -> None:
    bg = ACCENT if accent else ACCENT2
    btn.config(
        bg=bg, fg="#000000", relief="flat", bd=0,
        font=("Consolas", 11, "bold"),
        cursor="hand2", padx=16, pady=8,
        activebackground=bg, activeforeground="#000000",
    )


def labeled_entry(parent, label: str, var: tk.StringVar,
                  width: int = 22) -> None:
    """Строка «Метка + Entry» внутри parent-фрейма."""
    f = tk.Frame(parent, bg=DARK_BG)
    f.pack(fill=tk.X, padx=24, pady=5)
    tk.Label(
        f, text=label, bg=DARK_BG, fg=MUTED,
        font=FONT_SMALL, width=13, anchor="w",
    ).pack(side=tk.LEFT)
    tk.Entry(
        f, textvariable=var, bg=ENTRY_BG, fg=TEXT_COLOR,
        insertbackground=ACCENT, font=FONT_MAIN,
        relief="flat", bd=0, width=width,
    ).pack(side=tk.LEFT, padx=(8, 0), ipady=4)


# ──────────────────────────────────────────────────────────────
# Виджет ленты сообщений + поле ввода
# ──────────────────────────────────────────────────────────────

class ChatFrame(tk.Frame):
    def __init__(self, master, on_send_callback, **kw):
        super().__init__(master, bg=DARK_BG, **kw)
        self.on_send = on_send_callback
        self._build()

    def _build(self):
        self.msg_area = scrolledtext.ScrolledText(
            self, bg=DARK_BG, fg=TEXT_COLOR,
            font=FONT_MAIN, wrap=tk.WORD,
            state=tk.DISABLED, relief="flat", bd=0,
            padx=10, pady=10,
        )
        self.msg_area.pack(fill=tk.BOTH, expand=True)

        self.msg_area.tag_config("nick_self",  foreground=ACCENT,  font=FONT_NICK)
        self.msg_area.tag_config("nick_other", foreground=ACCENT2, font=FONT_NICK)
        self.msg_area.tag_config("nick_sys",   foreground=MUTED,   font=FONT_NICK)
        self.msg_area.tag_config("msg_self",   foreground=TEXT_COLOR)
        self.msg_area.tag_config("msg_other",  foreground=TEXT_COLOR)
        self.msg_area.tag_config("msg_sys",    foreground=MUTED, font=FONT_SMALL)
        self.msg_area.tag_config("ts",         foreground=MUTED, font=FONT_SMALL)

        bar = tk.Frame(self, bg=PANEL_BG)
        bar.pack(fill=tk.X, pady=(1, 0))

        self.entry = tk.Entry(
            bar, bg=ENTRY_BG, fg=TEXT_COLOR,
            insertbackground=ACCENT, font=FONT_MAIN,
            relief="flat", bd=0,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True,
                        padx=(12, 6), pady=10)
        self.entry.bind("<Return>", self._send)

        btn = tk.Button(bar, text="ОТПРАВИТЬ", command=self._send)
        style_btn(btn)
        btn.pack(side=tk.RIGHT, padx=(0, 12), pady=10)

    def _send(self, _event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.on_send(text)

    def append(self, who: str, text: str, kind: str = "other") -> None:
        ts = time.strftime("%H:%M:%S")
        self.msg_area.config(state=tk.NORMAL)
        self.msg_area.insert(tk.END, who,          f"nick_{kind}")
        self.msg_area.insert(tk.END, f"  {ts}\n",  "ts")
        self.msg_area.insert(tk.END, f"  {text}\n\n", f"msg_{kind}")
        self.msg_area.config(state=tk.DISABLED)
        self.msg_area.see(tk.END)

    def sys_msg(self, text: str) -> None:
        self.append("◈ система", text, "sys")

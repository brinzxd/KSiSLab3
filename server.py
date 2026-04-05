"""
server.py — запуск сервера чата.

Использование:
    python server.py
"""

import socket
import threading
import queue
import tkinter as tk
from tkinter import messagebox

from common import (
    send_msg, recv_msg, port_is_free,
    DARK_BG, PANEL_BG, ACCENT, MUTED, FONT_SMALL, FONT_TITLE,
    ChatFrame, style_btn, labeled_entry,
)


# ──────────────────────────────────────────────────────────────
# Главное окно сервера (чат + статус)
# ──────────────────────────────────────────────────────────────

class ServerChatWindow(tk.Tk):
    def __init__(self, host: str, port: int, nickname: str):
        super().__init__()
        self.title(f"Socket Chat — СЕРВЕР  [{host}:{port}]")
        self.configure(bg=DARK_BG)
        self.geometry("820x620")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.nickname  = nickname
        self.host      = host
        self.port      = port
        self.clients: dict[socket.socket, str] = {}   # sock → nick
        self.lock      = threading.Lock()
        self.running   = True
        self.q: queue.Queue = queue.Queue()

        self._build_ui()
        self._start_server()
        self._poll()

    # ── UI ──────────────────────────────────────────────────

    def _build_ui(self):
        # шапка
        header = tk.Frame(self, bg=PANEL_BG, height=52)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="◈ СЕРВЕР", bg=PANEL_BG, fg=ACCENT,
            font=("Consolas", 13, "bold"),
        ).pack(side=tk.LEFT, padx=14, pady=12)

        self.status_lbl = tk.Label(
            header, text="запуск…", bg=PANEL_BG, fg=MUTED, font=FONT_SMALL,
        )
        self.status_lbl.pack(side=tk.LEFT, padx=6)

        self.clients_lbl = tk.Label(
            header, text="0 клиентов", bg=PANEL_BG, fg=MUTED, font=FONT_SMALL,
        )
        self.clients_lbl.pack(side=tk.RIGHT, padx=14)

        # виджет чата
        self.chat = ChatFrame(self, self._send_message)
        self.chat.pack(fill=tk.BOTH, expand=True)

    # ── сетевая часть ───────────────────────────────────────

    def _start_server(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen()
        self.q.put(("sys", f"Сервер запущен  {self.host}:{self.port}"))
        self.q.put(("status", f"слушаю {self.host}:{self.port}"))
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                self.server_sock.settimeout(1.0)
                conn, addr = self.server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            # первое сообщение от клиента — его никнейм
            nick_msg = recv_msg(conn)
            nick = nick_msg.strip() if nick_msg else str(addr)

            with self.lock:
                self.clients[conn] = nick

            self.q.put(("sys",            f"✦ {nick} ({addr[0]}) подключился"))
            self.q.put(("update_clients", None))

            threading.Thread(
                target=self._client_loop,
                args=(conn, nick),
                daemon=True,
            ).start()

    def _client_loop(self, conn: socket.socket, nick: str):
        while self.running:
            msg = recv_msg(conn)
            if msg is None:
                break
            # показать в своём чате и разослать остальным
            self.q.put(("msg", nick, msg))
            self._broadcast(f"{nick}§{msg}", exclude=conn)

        with self.lock:
            self.clients.pop(conn, None)
        conn.close()
        self.q.put(("sys",            f"✦ {nick} отключился"))
        self.q.put(("update_clients", None))

    def _broadcast(self, payload: str, exclude=None):
        with self.lock:
            dead = []
            for c in self.clients:
                if c is exclude:
                    continue
                try:
                    send_msg(c, payload)
                except OSError:
                    dead.append(c)
            for c in dead:
                self.clients.pop(c, None)

    def _send_message(self, text: str):
        self.chat.append(self.nickname, text, "self")
        self._broadcast(f"{self.nickname}§{text}")

    # ── poll (очередь → UI) ─────────────────────────────────

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                kind = item[0]
                if kind == "sys":
                    self.chat.sys_msg(item[1])
                elif kind == "msg":
                    _, nick, text = item
                    self.chat.append(nick, text, "other")
                elif kind == "status":
                    self.status_lbl.config(text=item[1], fg=ACCENT)
                elif kind == "update_clients":
                    with self.lock:
                        n = len(self.clients)
                    self.clients_lbl.config(text=f"{n} клиент(ов)")
        except Exception:
            pass
        if self.running:
            self.after(50, self._poll)

    def _on_close(self):
        self.running = False
        try:
            self.server_sock.close()
        except OSError:
            pass
        self.destroy()


# ──────────────────────────────────────────────────────────────
# Окно настроек перед запуском
# ──────────────────────────────────────────────────────────────

class ServerSetupWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Socket Chat — Сервер")
        self.resizable(False, False)
        self.configure(bg=DARK_BG)
        self._build()

    def _build(self):
        tk.Label(
            self, text="ЗАПУСК СЕРВЕРА", bg=DARK_BG, fg=ACCENT,
            font=FONT_TITLE,
        ).pack(pady=(30, 4))
        tk.Label(
            self, text="TCP · Socket API", bg=DARK_BG, fg=MUTED, font=FONT_SMALL,
        ).pack(pady=(0, 20))

        self.nick_var = tk.StringVar(value="Сервер")
        self.host_var = tk.StringVar(value="0.0.0.0")
        self.port_var = tk.StringVar(value="9000")

        labeled_entry(self, "Никнейм:",  self.nick_var)
        labeled_entry(self, "Bind IP:",  self.host_var)
        labeled_entry(self, "Порт:",     self.port_var)

        btn = tk.Button(self, text="▶  ЗАПУСТИТЬ СЕРВЕР", command=self._launch)
        style_btn(btn)
        btn.pack(pady=(20, 30), padx=32, fill=tk.X)

    def _launch(self):
        try:
            port = int(self.port_var.get())
            assert 1 <= port <= 65535
        except (ValueError, AssertionError):
            messagebox.showerror("Ошибка", "Порт должен быть числом 1–65535")
            return

        if not port_is_free(port):
            messagebox.showerror(
                "Порт занят",
                f"Порт {port} уже используется.\nВыберите другой.",
            )
            return

        host = self.host_var.get().strip() or "0.0.0.0"
        nick = self.nick_var.get().strip() or "Сервер"

        self.destroy()
        ServerChatWindow(host, port, nick).mainloop()


# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ServerSetupWindow().mainloop()

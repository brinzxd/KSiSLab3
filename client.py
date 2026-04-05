"""
client.py — запуск клиента чата.
"""

import socket
import threading
import queue
import tkinter as tk
from tkinter import messagebox

from common import (
    send_msg, recv_msg,
    DARK_BG, PANEL_BG, ACCENT, ACCENT2, MUTED, FONT_SMALL, FONT_TITLE,
    ChatFrame, style_btn, labeled_entry,
)


class ClientChatWindow(tk.Tk):
    def __init__(self, host: str, port: int, nickname: str, bind_ip: str = ""):  # ← ИЗМЕНЕНО: добавлен bind_ip
        super().__init__()
        self.title(f"Socket Chat — КЛИЕНТ [{host}:{port}]")
        self.configure(bg=DARK_BG)
        self.geometry("820x620")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.nickname = nickname
        self.host = host
        self.port = port
        self.bind_ip = bind_ip  # ← НОВОЕ
        self.running = True
        self.sock: socket.socket | None = None
        self.q: queue.Queue = queue.Queue()

        self._build_ui()
        threading.Thread(target=self._connect, daemon=True).start()
        self._poll()

    def _build_ui(self):
        header = tk.Frame(self, bg=PANEL_BG, height=52)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="◈ КЛИЕНТ", bg=PANEL_BG, fg=ACCENT2,
            font=("Consolas", 13, "bold"),
        ).pack(side=tk.LEFT, padx=14, pady=12)

        self.status_lbl = tk.Label(
            header, text="подключение…", bg=PANEL_BG, fg=MUTED, font=FONT_SMALL,
        )
        self.status_lbl.pack(side=tk.LEFT, padx=6)

        self.chat = ChatFrame(self, self._send_message)
        self.chat.pack(fill=tk.BOTH, expand=True)

    def _connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.bind_ip:                        # ← НОВОЕ
                self.sock.bind((self.bind_ip, 0))   # ← НОВОЕ: 0 = автовыбор порта
            self.sock.connect((self.host, self.port))
            send_msg(self.sock, self.nickname)
            self.q.put(("status", f"подключён к {self.host}:{self.port}"))
            self.q.put(("sys", f"Добро пожаловать, {self.nickname}!"))
            self._recv_loop()
        except OSError as e:
            self.q.put(("error", str(e)))

    def _recv_loop(self):
        while self.running:
            msg = recv_msg(self.sock)
            if msg is None:
                if self.running:
                    self.q.put(("sys", "Соединение с сервером разорвано."))
                    self.q.put(("status_err", "отключён"))
                break
            if "§" in msg:
                nick, text = msg.split("§", 1)
                self.q.put(("msg", nick, text))
            else:
                self.q.put(("sys", msg))

    def _send_message(self, text: str):
        if self.sock is None:
            return
        try:
            send_msg(self.sock, text)
            self.chat.append(self.nickname, text, "self")
        except OSError as e:
            self.chat.sys_msg(f"Ошибка отправки: {e}")

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
                elif kind == "status_err":
                    self.status_lbl.config(text=item[1], fg="#ff4466")
                elif kind == "error":
                    self.status_lbl.config(text="ошибка подключения", fg="#ff4466")
                    self.chat.sys_msg(f"Не удалось подключиться: {item[1]}")
        except Exception:
            pass
        if self.running:
            self.after(50, self._poll)

    def _on_close(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.destroy()


class ClientSetupWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Socket Chat — Клиент")
        self.resizable(False, False)
        self.configure(bg=DARK_BG)
        self._build()

    def _build(self):
        tk.Label(
            self, text="ПОДКЛЮЧЕНИЕ", bg=DARK_BG, fg=ACCENT2,
            font=FONT_TITLE,
        ).pack(pady=(30, 4))
        tk.Label(
            self, text="TCP · Socket API", bg=DARK_BG, fg=MUTED, font=FONT_SMALL,
        ).pack(pady=(0, 20))

        self.nick_var = tk.StringVar(value="Пользователь")
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="9000")
        self.bind_var = tk.StringVar(value="")  # ← НОВОЕ

        labeled_entry(self, "Никнейм:", self.nick_var)
        labeled_entry(self, "IP сервера:", self.host_var)
        labeled_entry(self, "Порт:", self.port_var)
        labeled_entry(self, "Bind IP (opt):", self.bind_var)  # ← НОВОЕ

        btn = tk.Button(self, text="▶ ПОДКЛЮЧИТЬСЯ", command=self._launch)
        style_btn(btn, accent=False)
        btn.pack(pady=(20, 30), padx=32, fill=tk.X)

    def _launch(self):
        try:
            port = int(self.port_var.get())
            assert 1 <= port <= 65535
        except (ValueError, AssertionError):
            messagebox.showerror("Ошибка", "Порт должен быть числом 1–65535")
            return

        host = self.host_var.get().strip() or "127.0.0.1"
        nick = self.nick_var.get().strip() or "Аноним"
        bind_ip = self.bind_var.get().strip()  # ← НОВОЕ

        self.destroy()
        ClientChatWindow(host, port, nick, bind_ip).mainloop()  # ← ИЗМЕНЕНО


if __name__ == "__main__":
    ClientSetupWindow().mainloop()
#!/usr/bin/env python3
"""
LoanTrack — Pemantau Pinjaman Kereta
A local desktop app to track car loan applications: applicant name, IC,
car model, bank, loan amount, status and status history.

Data is stored locally in SQLite (data/loantrack.db).
No internet connection is required.
"""

from __future__ import annotations

import csv
import ctypes
import os
import queue
import re
import sqlite3
import sys
import threading
import uuid
import webbrowser
from collections import Counter
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import firebase_sync as fb

APP_NAME = "LoanTrack"
APP_VERSION = "1.1.1"
WINDOW_TITLE = "LoanTrack — Pemantau Pinjaman Kereta"

STATUSES = ["Baru", "Dalam Proses", "Hantar Bank", "Diluluskan", "Ditolak", "Selesai"]
PROCESS_STATUSES = {"Baru", "Dalam Proses", "Hantar Bank"}
APPROVED_STATUSES = {"Diluluskan", "Selesai"}
REJECTED_STATUSES = {"Ditolak"}

BANKS = [
    "Maybank",
    "CIMB Bank",
    "Public Bank",
    "RHB Bank",
    "Hong Leong Bank",
    "AmBank",
    "Bank Islam",
    "Bank Rakyat",
    "BSN",
    "Affin Bank",
    "Alliance Bank",
    "MBSB Bank",
    "Bank Muamalat",
    "Agrobank",
    "OCBC Bank",
    "UOB Malaysia",
    "HSBC Malaysia",
    "Standard Chartered",
    "AEON Bank",
    "GXBank",
    "Boost Bank",
]

# ---------------------------------------------------------------- palette ----
INK = "#0F172A"
INK_SOFT = "#334155"
MUTED = "#64748B"
MUTED_LIGHT = "#94A3B8"
BG = "#F4F6FA"
CARD = "#FFFFFF"
BORDER = "#E8ECF3"
BORDER_STRONG = "#D8DFEA"
SOFT_FILL = "#F4F6FB"
ROW_HOVER = "#F8FAFD"

PRIMARY = "#1D4ED8"
PRIMARY_DARK = "#173FB0"
PRIMARY_SOFT = "#EDF3FF"
DANGER = "#BE123C"
DANGER_SOFT = "#FFF1F3"
SUCCESS = "#059669"

SIDEBAR = "#0B1424"
SIDEBAR_HOVER = "#111E31"
SIDEBAR_ACTIVE = "#17253C"
SIDEBAR_LINE = "#1B2A40"
SIDEBAR_TEXT = "#93A3BA"
SIDEBAR_TEXT_ACTIVE = "#F8FAFC"
SIDEBAR_COUNT_BG = "#1A2941"
SIDEBAR_COUNT_FG = "#AFC1DB"

FOOTER_BG = "#FBFCFE"

STATUS_STYLES = {
    "Baru": ("#475569", "#EEF2F7"),
    "Dalam Proses": ("#B45309", "#FEF3C7"),
    "Hantar Bank": ("#4338CA", "#E0E7FF"),
    "Diluluskan": ("#047857", "#D1FAE5"),
    "Ditolak": ("#BE123C", "#FFE4E6"),
    "Selesai": ("#0369A1", "#E0F2FE"),
}
STATUS_DOTS = {
    "Baru": "#9AA9BC",
    "Dalam Proses": "#FBBF24",
    "Hantar Bank": "#818CF8",
    "Diluluskan": "#34D399",
    "Ditolak": "#FB7185",
    "Selesai": "#38BDF8",
}
UNKNOWN_STATUS_STYLE = ("#475569", "#EEF2F7")

AVATAR_PALETTE = [
    ("#DBEAFE", "#1D4ED8"),
    ("#D1FAE5", "#047857"),
    ("#FEF3C7", "#B45309"),
    ("#FCE7F3", "#BE185D"),
    ("#E0E7FF", "#4338CA"),
    ("#CFFAFE", "#0E7490"),
    ("#F3E8FF", "#7E22CE"),
]

MONTHS_SHORT = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun",
                "Jul", "Ogo", "Sep", "Okt", "Nov", "Dis"]
MONTHS_LONG = ["Januari", "Februari", "Mac", "April", "Mei", "Jun",
               "Julai", "Ogos", "September", "Oktober", "November", "Disember"]
DAYS_LONG = ["Isnin", "Selasa", "Rabu", "Khamis", "Jumaat", "Sabtu", "Ahad"]

# table columns: (index, weight, minimum width in base px)
TABLE_COLS = [
    (0, 5, 198),   # applicant
    (1, 3, 146),   # IC
    (2, 3, 142),   # bank
    (3, 2, 96),    # amount
    (4, 2, 98),    # date
    (5, 2, 100),   # status
]
ACTION_COL = 6
ACTION_WIDTH = 28

SCALE = 1.0
F: dict[str, tkfont.Font] = {}


def s(value: float) -> int:
    """Scale a base-96-DPI pixel value."""
    return max(1, int(round(value * SCALE)))


def setup_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def init_fonts(root: tk.Tk) -> None:
    F.clear()
    families = set(tkfont.families(root))
    semi_family = "Segoe UI Semibold" if "Segoe UI Semibold" in families else "Segoe UI"
    semi_weight = "normal" if semi_family == "Segoe UI Semibold" else "bold"

    def mk(key: str, size: int, semibold: bool = False, family: str = "Segoe UI") -> None:
        F[key] = tkfont.Font(
            root=root,
            family=semi_family if semibold else family,
            size=-s(size),
            weight=semi_weight if semibold else "normal",
        )

    mk("micro", 9)
    mk("tiny", 10)
    mk("small", 10)
    mk("label", 11)
    mk("body", 12)
    mk("body_lg", 13)
    mk("body_bold", 13, semibold=True)
    mk("btn", 12, semibold=True)
    mk("btn_sm", 11, semibold=True)
    mk("card_title", 15, semibold=True)
    mk("h1", 26, semibold=True)
    mk("stat", 27, semibold=True)
    mk("stat_label", 10, semibold=True)
    mk("pill", 9, semibold=True)
    mk("pill_md", 10, semibold=True)
    mk("nav", 12)
    mk("nav_active", 12, semibold=True)
    mk("avatar", 12, semibold=True)
    mk("avatar_lg", 20, semibold=True)
    mk("logo", 15, semibold=True)
    mk("brand", 16, semibold=True)
    mk("thead", 10, semibold=True)
    mk("dialog_title", 19, semibold=True)
    mk("field_label", 11)
    mk("toast", 11, semibold=True)
    mk("error", 10)
    mk("chev", 20)


def setup_ttk(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        "Field.TCombobox",
        fieldbackground=CARD,
        background=CARD,
        foreground=INK,
        arrowcolor=MUTED,
        borderwidth=0,
        relief="flat",
        padding=(s(6), s(6)),
        arrowsize=s(12),
    )
    style.map(
        "Field.TCombobox",
        fieldbackground=[("readonly", CARD), ("disabled", SOFT_FILL)],
        foreground=[("readonly", INK)],
        background=[("readonly", CARD), ("active", CARD)],
        bordercolor=[("focus", CARD), ("!focus", CARD)],
        lightcolor=[("focus", CARD), ("!focus", CARD)],
        darkcolor=[("focus", CARD), ("!focus", CARD)],
        selectbackground=[("readonly", CARD)],
        selectforeground=[("readonly", INK)],
        arrowcolor=[("active", PRIMARY), ("!active", MUTED)],
    )

    root.option_add("*TCombobox*Listbox.background", CARD)
    root.option_add("*TCombobox*Listbox.foreground", INK)
    root.option_add("*TCombobox*Listbox.selectBackground", PRIMARY)
    root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
    root.option_add("*TCombobox*Listbox.font", F["body"])


# --------------------------------------------------------------- helpers ----
def rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle using a smoothed polygon."""
    r = max(1, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=32, **kwargs)


def draw_icon(canvas: tk.Canvas, kind: str, color: str, soft: str, size: int) -> None:
    """Small line icon inside a rounded pastel tile."""
    canvas.delete("all")
    rounded_rect(canvas, 0, 0, size - 1, size - 1, size * 0.27, fill=soft, outline=soft)
    w = max(1, int(size * 0.055))
    cx = cy = size / 2
    r = size * 0.23
    if kind == "doc":
        x1, y1 = cx - r * 0.8, cy - r
        x2, y2 = cx + r * 0.8, cy + r
        canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=w)
        for fy in (0.35, 0.6, 0.85):
            yy = y1 + (y2 - y1) * fy
            canvas.create_line(x1 + (x2 - x1) * 0.2, yy,
                               x1 + (x2 - x1) * 0.8, yy,
                               fill=color, width=max(1, w - 1),
                               capstyle="round")
    elif kind == "clock":
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=w)
        canvas.create_line(cx, cy, cx, cy - r * 0.58, fill=color, width=w, capstyle="round")
        canvas.create_line(cx, cy, cx + r * 0.5, cy + r * 0.25, fill=color, width=w, capstyle="round")
    elif kind == "check":
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=w)
        canvas.create_line(cx - r * 0.52, cy + r * 0.02,
                           cx - r * 0.1, cy + r * 0.45,
                           cx + r * 0.58, cy - r * 0.42,
                           fill=color, width=w + 1, capstyle="round", joinstyle="round")
    elif kind == "x":
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=w)
        d = r * 0.42
        canvas.create_line(cx - d, cy - d, cx + d, cy + d, fill=color, width=w, capstyle="round")
        canvas.create_line(cx - d, cy + d, cx + d, cy - d, fill=color, width=w, capstyle="round")


def draw_empty_icon(canvas: tk.Canvas, kind: str) -> None:
    canvas.delete("all")
    w = int(canvas["width"])
    h = int(canvas["height"])
    canvas.create_oval(2, 2, w - 2, h - 2, fill=PRIMARY_SOFT, outline="")
    cx, cy = w / 2, h / 2
    if kind == "doc":
        bw, bh = w * 0.30, h * 0.36
        canvas.create_rectangle(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2,
                                outline=PRIMARY, width=max(1, s(2)))
        for fy in (-0.12, 0.12, 0.36):
            canvas.create_line(cx - bw * 0.30, cy + bh * fy,
                               cx + bw * 0.30, cy + bh * fy,
                               fill=PRIMARY, width=max(1, s(2)), capstyle="round")
    else:
        r = w * 0.17
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           outline=PRIMARY, width=max(1, s(2)))
        canvas.create_line(cx + r * 0.7, cy + r * 0.7, cx + r * 1.5, cy + r * 1.5,
                           fill=PRIMARY, width=max(1, s(2)), capstyle="round")


def fmt_money(value) -> str:
    if value is None:
        return "—"
    try:
        return f"RM {float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def fmt_money_input(value) -> str:
    if value is None:
        return ""
    try:
        txt = f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return ""
    return txt.rstrip("0").rstrip(".") if "." in txt else txt


def fmt_compact(value) -> str:
    value = float(value or 0)
    if value >= 1_000_000:
        txt = f"{value / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"RM {txt}j"
    if value >= 1_000:
        if value >= 10_000:
            txt = f"{value / 1_000:.0f}"
        else:
            txt = f"{value / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"RM {txt}k"
    return f"RM {value:,.0f}"


def fmt_date(iso: str, short: bool = True) -> str:
    if not iso:
        return "—"
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    months = MONTHS_SHORT if short else MONTHS_LONG
    return f"{d.day} {months[d.month - 1]} {d.year}"


def fmt_datetime(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    return f"{dt.day} {MONTHS_SHORT[dt.month - 1]} {dt.year} · {dt:%H:%M}"


def relative_days(iso: str) -> str:
    if not iso:
        return ""
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return ""
    days = (date.today() - d).days
    if days <= 0:
        return "Hari ini"
    if days == 1:
        return "Semalam"
    return f"{days} hari lalu"


def format_ic(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12:
        return f"{digits[:6]}-{digits[6:8]}-{digits[8:]}"
    return value or ""


def parse_date(value: str) -> date:
    raw = (value or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("format tarikh tidak sah")


def parse_amount(value: str):
    raw = (value or "").strip().lower().replace("rm", "").replace(",", "").replace(" ", "")
    if not raw:
        return None
    amount = float(raw)
    if amount < 0:
        raise ValueError("jumlah tidak boleh negatif")
    return round(amount, 2)


def clip(value, length: int) -> str:
    text = str(value if value is not None else "")
    if len(text) <= length:
        return text
    return text[: max(1, length - 1)].rstrip() + "…"


def initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today_label() -> str:
    d = date.today()
    return f"{DAYS_LONG[d.weekday()]}, {d.day} {MONTHS_LONG[d.month - 1]} {d.year}"


def is_descendant(widget, ancestor) -> bool:
    node = widget
    while node is not None:
        if node is ancestor:
            return True
        node = getattr(node, "master", None)
    return False


def work_area(widget) -> tuple[int, int, int, int]:
    """Desktop work area (excludes the Windows taskbar) for window placement."""
    if sys.platform == "win32":
        try:
            from ctypes import wintypes
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(
                0x0030, 0, ctypes.byref(rect), 0
            ):
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                if width > 0 and height > 0:
                    return rect.left, rect.top, width, height
        except Exception:
            pass
    return 0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight()


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# ------------------------------------------------------------------- db -----
SCHEMA = """
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ic TEXT NOT NULL,
    car TEXT NOT NULL,
    bank TEXT NOT NULL,
    amount REAL,
    applied_date TEXT,
    status TEXT NOT NULL DEFAULT 'Baru',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    cloud_id TEXT,
    synced_at TEXT
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    note TEXT DEFAULT '',
    changed_at TEXT NOT NULL,
    FOREIGN KEY(loan_id) REFERENCES loans(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(status);
CREATE INDEX IF NOT EXISTS idx_loans_date ON loans(applied_date);
CREATE INDEX IF NOT EXISTS idx_history_loan ON history(loan_id);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS tombstones (
    cloud_id TEXT PRIMARY KEY,
    deleted_at TEXT NOT NULL,
    synced INTEGER NOT NULL DEFAULT 0
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 8000")
        self.conn.executescript(SCHEMA)
        self._migrate_cloud_columns()
        self.conn.commit()

    def _migrate_cloud_columns(self):
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(loans)")}
        with self.conn:
            if "cloud_id" not in columns:
                self.conn.execute("ALTER TABLE loans ADD COLUMN cloud_id TEXT")
            if "synced_at" not in columns:
                self.conn.execute("ALTER TABLE loans ADD COLUMN synced_at TEXT")
            missing = self.conn.execute(
                "SELECT id FROM loans WHERE cloud_id IS NULL OR cloud_id = ''"
            ).fetchall()
            for row in missing:
                self.conn.execute(
                    "UPDATE loans SET cloud_id = ? WHERE id = ?",
                    (uuid.uuid4().hex, row[0]),
                )
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_loans_cloud ON loans(cloud_id)"
            )

    def list_loans(self):
        return self.conn.execute(
            "SELECT * FROM loans "
            "ORDER BY COALESCE(applied_date, substr(created_at, 1, 10)) DESC, id DESC"
        ).fetchall()

    def get_loan(self, loan_id: int):
        return self.conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()

    def create_loan(self, data: dict) -> int:
        stamp = now_iso()
        cloud_id = uuid.uuid4().hex
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO loans (name, ic, car, bank, amount, applied_date, status, "
                "notes, created_at, updated_at, cloud_id, synced_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (
                    data["name"], data["ic"], data["car"], data["bank"],
                    data["amount"], data["applied_date"], data["status"],
                    data["notes"], stamp, stamp, cloud_id,
                ),
            )
            loan_id = cur.lastrowid
            self.conn.execute(
                "INSERT INTO history (loan_id, from_status, to_status, note, changed_at) "
                "VALUES (?, NULL, ?, ?, ?)",
                (loan_id, data["status"], "Rekod dicipta", stamp),
            )
        return int(loan_id)

    def update_loan(self, loan_id: int, data: dict) -> bool:
        current = self.get_loan(loan_id)
        if current is None:
            return False
        status_changed = current["status"] != data["status"]
        stamp = now_iso()
        with self.conn:
            self.conn.execute(
                "UPDATE loans SET name = ?, ic = ?, car = ?, bank = ?, amount = ?, "
                "applied_date = ?, status = ?, notes = ?, updated_at = ?, "
                "synced_at = NULL WHERE id = ?",
                (
                    data["name"], data["ic"], data["car"], data["bank"],
                    data["amount"], data["applied_date"], data["status"],
                    data["notes"], stamp, loan_id,
                ),
            )
            if status_changed:
                self.conn.execute(
                    "INSERT INTO history (loan_id, from_status, to_status, note, changed_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (loan_id, current["status"], data["status"], "Status dikemas kini", stamp),
                )
        return status_changed

    def delete_loan(self, loan_id: int) -> None:
        current = self.get_loan(loan_id)
        with self.conn:
            if current is not None and current["cloud_id"]:
                self.conn.execute(
                    "INSERT OR REPLACE INTO tombstones (cloud_id, deleted_at, synced) "
                    "VALUES (?, ?, 0)",
                    (current["cloud_id"], now_iso()),
                )
            self.conn.execute("DELETE FROM loans WHERE id = ?", (loan_id,))

    def history_for(self, loan_id: int):
        return self.conn.execute(
            "SELECT * FROM history WHERE loan_id = ? ORDER BY id DESC", (loan_id,)
        ).fetchall()

    def history_ascending(self, loan_id: int):
        return self.conn.execute(
            "SELECT * FROM history WHERE loan_id = ? ORDER BY changed_at ASC, id ASC",
            (loan_id,),
        ).fetchall()

    # -- settings ---------------------------------------------------------
    def get_setting(self, key: str, default=None):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row is not None else default

    def set_setting(self, key: str, value) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )

    def delete_setting(self, key: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM settings WHERE key = ?", (key,))

    # -- cloud sync -------------------------------------------------------
    def get_loan_by_cloud(self, cloud_id: str):
        return self.conn.execute(
            "SELECT * FROM loans WHERE cloud_id = ?", (cloud_id,)
        ).fetchone()

    def _insert_history(self, loan_id: int, history) -> None:
        for entry in history:
            self.conn.execute(
                "INSERT INTO history (loan_id, from_status, to_status, note, changed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    loan_id, entry.get("from_status"), entry["to_status"],
                    entry.get("note") or "", entry["changed_at"],
                ),
            )

    def merge_remote_loan(self, remote: dict, history: list) -> str:
        """Merge one Firestore record into the local DB (last-write-wins).

        Returns 'inserted', 'updated', 'kept_local' or 'same'.
        """
        existing = self.get_loan_by_cloud(remote["cloud_id"])
        with self.conn:
            if existing is not None:
                if remote["updated_at"] > existing["updated_at"]:
                    self.conn.execute(
                        "UPDATE loans SET name = ?, ic = ?, car = ?, bank = ?, amount = ?, "
                        "applied_date = ?, status = ?, notes = ?, created_at = ?, "
                        "updated_at = ?, synced_at = ? WHERE id = ?",
                        (
                            remote["name"], remote["ic"], remote["car"], remote["bank"],
                            remote["amount"], remote["applied_date"], remote["status"],
                            remote["notes"], remote["created_at"], remote["updated_at"],
                            remote["updated_at"], existing["id"],
                        ),
                    )
                    self.conn.execute(
                        "DELETE FROM history WHERE loan_id = ?", (existing["id"],)
                    )
                    self._insert_history(existing["id"], history)
                    return "updated"
                if remote["updated_at"] == existing["updated_at"]:
                    if existing["synced_at"] is None:
                        # Same second, but local has changes that were never pushed.
                        # Keep them dirty so the push below cannot lose an edit.
                        return "kept_local"
                    return "same"
                # Local copy is newer: make sure it gets pushed on this sync.
                if existing["synced_at"] is not None:
                    self.conn.execute(
                        "UPDATE loans SET synced_at = NULL WHERE id = ?",
                        (existing["id"],),
                    )
                return "kept_local"
            cur = self.conn.execute(
                "INSERT INTO loans (name, ic, car, bank, amount, applied_date, status, "
                "notes, created_at, updated_at, cloud_id, synced_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    remote["name"], remote["ic"], remote["car"], remote["bank"],
                    remote["amount"], remote["applied_date"], remote["status"],
                    remote["notes"], remote["created_at"], remote["updated_at"],
                    remote["cloud_id"], remote["updated_at"],
                ),
            )
            self._insert_history(int(cur.lastrowid), history)
            return "inserted"

    def loans_pending_push(self):
        return self.conn.execute(
            "SELECT * FROM loans WHERE synced_at IS NULL ORDER BY id ASC"
        ).fetchall()

    def mark_loan_synced(self, cloud_id: str, updated_at: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE loans SET synced_at = ? "
                "WHERE cloud_id = ? AND updated_at = ? AND synced_at IS NULL",
                (updated_at, cloud_id, updated_at),
            )

    def pending_tombstones(self):
        return self.conn.execute(
            "SELECT cloud_id, deleted_at FROM tombstones WHERE synced = 0"
        ).fetchall()

    def record_cloud_tombstone(self, cloud_id: str, deleted_at: str) -> bool:
        """Apply a deletion that happened on another client (e.g. the web app)."""
        removed = False
        with self.conn:
            row = self.get_loan_by_cloud(cloud_id)
            if row is not None:
                self.conn.execute("DELETE FROM loans WHERE id = ?", (row["id"],))
                removed = True
            self.conn.execute(
                "INSERT INTO tombstones (cloud_id, deleted_at, synced) "
                "VALUES (?, ?, 1) "
                "ON CONFLICT(cloud_id) DO UPDATE SET "
                "deleted_at = excluded.deleted_at, synced = 1",
                (cloud_id, deleted_at or now_iso()),
            )
        return removed

    def mark_tombstones_synced(self, cloud_ids) -> None:
        cloud_ids = list(cloud_ids)
        if not cloud_ids:
            return
        placeholders = ",".join("?" for _ in cloud_ids)
        with self.conn:
            self.conn.execute(
                f"UPDATE tombstones SET synced = 1 WHERE cloud_id IN ({placeholders})",
                tuple(cloud_ids),
            )

    def tombstone_ids(self) -> set[str]:
        return {
            row[0] for row in
            self.conn.execute("SELECT cloud_id FROM tombstones").fetchall()
        }

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


def make_backup(db_path: Path, backup_dir: Path) -> None:
    """Keep one SQLite backup per day, retaining the last 14 daily copies."""
    if not db_path.exists():
        return
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        dest = backup_dir / f"loantrack_{date.today().isoformat()}.db"
        if not dest.exists():
            src = sqlite3.connect(str(db_path))
            dst = sqlite3.connect(str(dest))
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
        copies = sorted(backup_dir.glob("loantrack_*.db"))
        for old in copies[:-14]:
            try:
                old.unlink()
            except OSError:
                pass
    except Exception:
        # A failed backup must never prevent the app from opening.
        pass


# -------------------------------------------------------------- cloud sync --
class CloudSyncEngine:
    """One full pull → merge → push cycle against Firestore."""

    def __init__(self, db_path: Path, project_id: str, api_key: str,
                 uid: str, refresh_token: str):
        self.db_path = Path(db_path)
        self.project_id = project_id
        self.api_key = api_key
        self.uid = uid
        self.refresh_token = refresh_token

    def run(self) -> dict:
        auth = fb.FirebaseAuth(self.api_key)
        session = auth.refresh(self.refresh_token)
        client = fb.FirestoreClient(self.project_id, session["id_token"])
        db = Database(self.db_path)
        inserted = updated = same = kept_local = malformed = 0
        removed_remote = 0
        try:
            docs = client.list_loans(self.uid)
            cloud_tombstones = fb.doc_ids(client.list_tombstones(self.uid))
            for cloud_id in cloud_tombstones:
                if db.record_cloud_tombstone(cloud_id, ""):
                    removed_remote += 1
            tombstones = db.tombstone_ids()
            for doc in docs:
                name = doc.get("name", "")
                doc_id = name.rsplit("/", 1)[-1] if name else ""
                try:
                    remote, history = fb.fields_to_loan(doc.get("fields", {}), doc_id)
                except Exception:
                    malformed += 1
                    continue
                if remote["cloud_id"] in tombstones:
                    continue
                outcome = db.merge_remote_loan(remote, history)
                if outcome == "inserted":
                    inserted += 1
                elif outcome == "updated":
                    updated += 1
                elif outcome == "kept_local":
                    kept_local += 1
                else:
                    same += 1

            pending = db.loans_pending_push()
            writes = []
            for loan in pending:
                writes.append(client.make_update(
                    self.uid, loan, db.history_ascending(loan["id"])
                ))
            tomb_rows = db.pending_tombstones()
            for row in tomb_rows:
                writes.append(client.make_tombstone(
                    self.uid, row["cloud_id"], row["deleted_at"]
                ))
                writes.append(client.make_delete(self.uid, row["cloud_id"]))
            client.commit(writes)
            for loan in pending:
                db.mark_loan_synced(loan["cloud_id"], loan["updated_at"])
            db.mark_tombstones_synced([row["cloud_id"] for row in tomb_rows])

            stamp = now_iso()
            db.set_setting("cloud_last_sync", stamp)
            return {
                "inserted": inserted,
                "updated": updated,
                "same": same,
                "kept_local": kept_local,
                "malformed": malformed,
                "removed": removed_remote,
                "pushed": len(pending),
                "deleted": len(tomb_rows),
                "uid": session.get("uid") or self.uid,
                "refresh_token": session.get("refresh_token") or self.refresh_token,
                "last_sync": stamp,
            }
        finally:
            db.close()


class CloudManager:
    """Owns Firebase configuration, authentication and background syncing."""

    def __init__(self, app, db: Database):
        self.app = app
        self.db = db
        self.project_id = db.get_setting("cloud_project", "") or ""
        self.api_key = db.get_setting("cloud_api_key", "") or ""
        self.uid = db.get_setting("cloud_uid", "") or ""
        self.email = db.get_setting("cloud_email", "") or ""
        self.refresh_token = db.get_setting("cloud_refresh_token", "") or ""
        self.last_sync = db.get_setting("cloud_last_sync", "") or ""
        self._syncing = False
        self._pending_sync = False
        self._after_id = None
        self._auth_running = False
        self._auth_error = ""
        self._last_error = ""
        self._last_result = None
        self._session_generation = 0
        self._disposed = False
        self._ui_queue: queue.Queue = queue.Queue()
        self._poll_id = None
        try:
            self.app.after(120, self._drain_ui_queue)
        except tk.TclError:
            pass

    # -- state ------------------------------------------------------------
    @property
    def configured(self) -> bool:
        return bool(self.project_id and self.api_key)

    @property
    def signed_in(self) -> bool:
        return bool(self.uid and self.refresh_token)

    @property
    def auth_running(self) -> bool:
        return self._auth_running

    @property
    def syncing(self) -> bool:
        return self._syncing

    @property
    def auth_error(self) -> str:
        return self._auth_error

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def last_result(self):
        return self._last_result

    def state(self) -> dict:
        if not self.configured:
            return {"key": "not_configured", "label": "Tidak disediakan",
                    "color": "#7B8CA3",
                    "detail": "Sambungkan Firebase untuk sandaran awan & sync."}
        if not self.signed_in:
            return {"key": "signed_out", "label": "Belum log masuk",
                    "color": "#FBBF24",
                    "detail": "Log masuk untuk mula sync ke Firestore."}
        if self._syncing:
            return {"key": "syncing", "label": "Menyegerak…",
                    "color": "#60A5FA",
                    "detail": "Sedang menghantar dan menerima data."}
        if self._last_error:
            return {"key": "error", "label": "Ralat sync",
                    "color": "#F87171", "detail": self._last_error}
        if self._auth_running:
            return {"key": "auth", "label": "Menyambung…",
                    "color": "#60A5FA",
                    "detail": "Mengesahkan akaun dengan Firebase."}
        if self.last_sync:
            return {"key": "synced", "label": "Disegerakkan",
                    "color": "#34D399",
                    "detail": f"Terakhir: {fmt_datetime(self.last_sync)}"}
        return {"key": "ready", "label": "Sedia untuk sync",
                "color": "#60A5FA",
                "detail": "Tekan Sync Sekarang untuk mula."}

    def notify(self) -> None:
        if self._disposed or getattr(self.app, "_closing", False):
            return
        self._ui_queue.put(self.app.on_cloud_change)

    def _post(self, callback) -> None:
        if self._disposed or getattr(self.app, "_closing", False):
            return
        # Workers must never call Tk directly. The main thread drains this queue.
        self._ui_queue.put(callback)

    def _drain_ui_queue(self) -> None:
        self._poll_id = None
        if self._disposed or getattr(self.app, "_closing", False):
            return
        while True:
            try:
                callback = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                pass
        try:
            self._poll_id = self.app.after(120, self._drain_ui_queue)
        except tk.TclError:
            self._poll_id = None

    # -- configuration ----------------------------------------------------
    def save_config(self, project_id: str, api_key: str) -> tuple[bool, str]:
        if self._syncing:
            return False, "Sila tunggu sync selesai sebelum menukar konfigurasi."
        project_id = (project_id or "").strip()
        api_key = (api_key or "").strip()
        if not project_id:
            return False, "Sila masukkan Project ID Firebase."
        if not api_key:
            return False, "Sila masukkan Web API key Firebase."
        if len(api_key) < 15:
            return False, "Web API key kelihatan tidak sah."
        if not re.fullmatch(r"[A-Za-z0-9._-]+", project_id):
            return False, "Project ID mengandungi aksara yang tidak sah."
        project_changed = project_id != self.project_id
        if self._after_id is not None:
            try:
                self.app.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self.project_id = project_id
        self.api_key = api_key
        self.db.set_setting("cloud_project", project_id)
        self.db.set_setting("cloud_api_key", api_key)
        self._last_error = ""
        self._auth_error = ""
        if project_changed:
            self._session_generation += 1
            self._clear_session_settings()
        self.notify()
        return True, "Konfigurasi Firebase disimpan."

    def _clear_session_settings(self) -> None:
        self.uid = ""
        self.email = ""
        self.refresh_token = ""
        self.last_sync = ""
        self._syncing = False
        self._pending_sync = False
        self._auth_running = False
        for key in ("cloud_uid", "cloud_email", "cloud_refresh_token",
                    "cloud_last_sync"):
            self.db.delete_setting(key)

    def sign_out(self) -> None:
        if self._after_id is not None:
            try:
                self.app.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self._session_generation += 1
        self._clear_session_settings()
        self._last_error = ""
        self._auth_error = ""
        self.notify()

    # -- authentication ---------------------------------------------------
    def sign_in_async(self, email: str, password: str, create: bool = False,
                      on_done=None) -> None:
        if not self.configured:
            if on_done:
                on_done("Konfigurasi Firebase belum disimpan.")
            return
        if self._auth_running:
            return
        email = (email or "").strip()
        password = password or ""
        if not email or "@" not in email:
            self._auth_error = "Sila masukkan alamat email yang sah."
            self.notify()
            if on_done:
                on_done(self._auth_error)
            return
        if len(password) < 6:
            self._auth_error = "Kata laluan mesti sekurang-kurangnya 6 aksara."
            self.notify()
            if on_done:
                on_done(self._auth_error)
            return
        self._auth_running = True
        self._auth_error = ""
        self.notify()
        generation = self._session_generation
        api_key = self.api_key

        def worker():
            try:
                auth = fb.FirebaseAuth(api_key)
                session = auth.sign_up(email, password) if create else auth.sign_in(
                    email, password
                )
            except fb.CloudError as exc:
                self._post(lambda msg=exc.message, g=generation:
                           self._finish_auth(None, msg, on_done, g))
            except Exception as exc:
                self._post(lambda msg=f"Ralat tidak dijangka: {exc}", g=generation:
                           self._finish_auth(None, msg, on_done, g))
            else:
                self._post(lambda s=session, g=generation:
                           self._finish_auth(s, None, on_done, g))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_auth(self, session, error, on_done, generation) -> None:
        if generation != self._session_generation:
            return
        self._auth_running = False
        if error:
            self._auth_error = error
            self.notify()
            if on_done:
                on_done(error)
            return
        self.uid = session.get("uid", "")
        self.email = session.get("email") or self.email
        self.refresh_token = session.get("refresh_token", "")
        self._auth_error = ""
        self._last_error = ""
        self.db.set_setting("cloud_uid", self.uid)
        self.db.set_setting("cloud_email", self.email)
        self.db.set_setting("cloud_refresh_token", self.refresh_token)
        self.notify()
        try:
            self.app.toast("Awan disambungkan. Menyegerak data…")
        except Exception:
            pass
        if on_done:
            on_done(None)
        self.sync_async(manual=False)

    # -- sync -------------------------------------------------------------
    def start_auto_sync(self) -> None:
        if self.configured and self.signed_in:
            self.schedule_sync(1600)

    def schedule_sync(self, delay_ms: int = 1200) -> None:
        if not self.configured or not self.signed_in or self._disposed:
            return
        if self._syncing:
            self._pending_sync = True
            return
        if self._after_id is not None:
            try:
                self.app.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self._after_id = self.app.after(delay_ms, self._scheduled_sync)

    def _scheduled_sync(self) -> None:
        self._after_id = None
        self.sync_async(manual=False)

    def sync_async(self, manual: bool = False, on_done=None) -> None:
        if not self.configured:
            if manual:
                messagebox.showinfo(
                    "Awan belum disediakan",
                    "Sambungkan projek Firebase terlebih dahulu.",
                    parent=self.app,
                )
            return
        if not self.signed_in:
            if manual:
                messagebox.showinfo(
                    "Belum log masuk",
                    "Sila log masuk ke akaun Firebase terlebih dahulu.",
                    parent=self.app,
                )
            return
        if self._syncing:
            self._pending_sync = True
            return
        if self._after_id is not None:
            try:
                self.app.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        self._syncing = True
        self._last_error = ""
        self.notify()
        generation = self._session_generation
        project_id, api_key = self.project_id, self.api_key
        uid, refresh_token = self.uid, self.refresh_token
        db_path = self.db.path

        def worker():
            try:
                result = CloudSyncEngine(
                    db_path, project_id, api_key, uid, refresh_token
                ).run()
            except fb.CloudError as exc:
                self._post(lambda e=exc, g=generation:
                           self._finish_sync(None, e, manual, on_done, g))
            except Exception as exc:
                err = fb.CloudError(f"Ralat sync: {exc}", code="unexpected")
                self._post(lambda e=err, g=generation:
                           self._finish_sync(None, e, manual, on_done, g))
            else:
                self._post(lambda r=result, g=generation:
                           self._finish_sync(r, None, manual, on_done, g))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_sync(self, result, error, manual, on_done, generation) -> None:
        if generation != self._session_generation:
            return
        self._syncing = False
        if error:
            self._last_error = error.message
            self._pending_sync = False
            if error.code == "auth_expired":
                self._clear_session_settings()
                self._auth_error = "Sesi tamat. Sila log masuk semula."
            self.notify()
            if on_done:
                on_done(error.message)
            if manual:
                try:
                    self.app.toast("Sync gagal. Buka Awan & Sync untuk butiran.")
                except Exception:
                    pass
            return
        self._last_result = result
        if result.get("uid"):
            self.uid = result["uid"]
            self.db.set_setting("cloud_uid", self.uid)
        if result.get("refresh_token"):
            self.refresh_token = result["refresh_token"]
            self.db.set_setting("cloud_refresh_token", self.refresh_token)
        self.last_sync = result.get("last_sync", "")
        self.db.set_setting("cloud_last_sync", self.last_sync)
        self._last_error = ""
        self.notify()
        try:
            self.app.on_cloud_sync_finished(result, manual)
        except Exception:
            pass
        if on_done:
            on_done(None)
        if self._pending_sync:
            self._pending_sync = False
            self.schedule_sync(500)

    def dispose(self) -> None:
        self._disposed = True
        for attr in ("_after_id", "_poll_id"):
            after_id = getattr(self, attr, None)
            if after_id is not None:
                try:
                    self.app.after_cancel(after_id)
                except tk.TclError:
                    pass
                setattr(self, attr, None)


# --------------------------------------------------------------- widgets ----
class RoundButton(tk.Canvas):
    STYLES = {
        "primary": dict(fill=PRIMARY, fg="#FFFFFF", border=PRIMARY,
                        hover_fill=PRIMARY_DARK, hover_border=PRIMARY_DARK),
        "ghost": dict(fill=CARD, fg=INK_SOFT, border=BORDER_STRONG,
                      hover_fill="#F6F8FC", hover_border="#C7D1E0"),
        "soft": dict(fill=PRIMARY_SOFT, fg=PRIMARY, border=PRIMARY_SOFT,
                     hover_fill="#E2EBFF", hover_border="#D7E2FE"),
        "danger": dict(fill=CARD, fg=DANGER, border="#F0C9D0",
                       hover_fill=DANGER_SOFT, hover_border="#E5AEB9"),
    }

    def __init__(self, master, text, command=None, kind="primary", bg=CARD,
                 height=38, font=None, padx=16):
        self.kind = kind
        self.text = text
        self.command = command
        self.font = font or F["btn"]
        self.height = s(height)
        self.width = self.font.measure(text) + s(padx) * 2
        super().__init__(master, width=self.width, height=self.height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2", takefocus=0)
        self._hover = False
        self._pressed = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self) -> None:
        style = self.STYLES[self.kind]
        fill = style["hover_fill"] if self._hover else style["fill"]
        border = style["hover_border"] if self._hover else style["border"]
        if self._pressed:
            fill = style["hover_fill"]
        self.delete("all")
        rounded_rect(self, 0.5, 0.5, self.width - 0.5, self.height - 0.5,
                     s(9), fill=fill, outline=border)
        self.create_text(self.width / 2, self.height / 2 + 0.5, text=self.text,
                         font=self.font, fill=style["fg"])

    def _on_enter(self, _event=None):
        self._hover = True
        self._draw()

    def _on_leave(self, _event=None):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event=None):
        self._pressed = True
        self._draw()

    def _on_release(self, event=None):
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        if not was_pressed:
            return
        if event is not None:
            under = self.winfo_containing(event.x_root, event.y_root)
            if under is not self:
                return
        if self.command:
            self.command()


class StatusPill(tk.Canvas):
    def __init__(self, master, status: str, bg=CARD, font=None, height=22,
                 fixed_width=None):
        fg, fill = STATUS_STYLES.get(status, UNKNOWN_STATUS_STYLE)
        self.font = font or F["pill_md"]
        self.height = s(height)
        text_w = self.font.measure(status)
        pill_w = text_w + s(20)
        width = max(pill_w, s(fixed_width)) if fixed_width else pill_w
        super().__init__(master, width=width, height=self.height, bg=bg,
                         highlightthickness=0, bd=0)
        rounded_rect(self, 0, 0, pill_w, self.height, self.height / 2,
                     fill=fill, outline=fill)
        self.create_text(pill_w / 2, self.height / 2 + 0.5, text=status,
                         font=self.font, fill=fg)

    def set_bg(self, bg: str) -> None:
        self.configure(bg=bg)


class ScrollFrame(tk.Frame):
    def __init__(self, master, bg=CARD):
        super().__init__(master, bg=bg)
        self.bg = bg
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.configure(yscrollincrement=s(20))
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.bar = tk.Canvas(self, width=s(9), bg=bg, highlightthickness=0, bd=0,
                             cursor="hand2")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self._bar_visible = False
        self._bar_hover = False
        self._bar_first = 0.0
        self._bar_last = 1.0
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bar.bind("<Configure>", lambda _e: self._draw_bar())
        self.bar.bind("<Enter>", lambda _e: self._set_bar_hover(True))
        self.bar.bind("<Leave>", lambda _e: self._set_bar_hover(False))
        self.bar.bind("<ButtonPress-1>", self._bar_jump)
        self.bar.bind("<B1-Motion>", self._bar_jump)

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._sync_bar()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)
        self._sync_bar()

    def _on_scroll(self, first, last):
        try:
            self._bar_first = float(first)
            self._bar_last = float(last)
        except ValueError:
            return
        self._sync_bar()

    def _sync_bar(self):
        first, last = self.canvas.yview()
        self._bar_first, self._bar_last = first, last
        needed = not (first <= 0.0 and last >= 1.0)
        if needed and not self._bar_visible:
            self.bar.place(relx=1.0, rely=0, x=0, anchor="ne",
                           relheight=1.0, width=s(9))
            self.bar.tk.call("raise", self.bar._w)
            self._bar_visible = True
            self.after_idle(self._draw_bar)
        elif not needed and self._bar_visible:
            self.bar.place_forget()
            self._bar_visible = False
        self._draw_bar()

    def _draw_bar(self):
        bar = self.bar
        bar.delete("all")
        if not self._bar_visible:
            return
        width = bar.winfo_width()
        height = bar.winfo_height()
        if width <= 1 or height <= 1:
            return
        pad = s(6)
        track_h = max(1, height - 2 * pad)
        thumb_h = max(s(30), track_h * (self._bar_last - self._bar_first))
        top = pad + track_h * self._bar_first
        top = min(top, height - pad - thumb_h)
        top = max(pad, top)
        color = "#A8B7C9" if self._bar_hover else "#CBD5E1"
        x1 = s(2)
        x2 = width - s(2)
        rounded_rect(bar, x1, top, x2, top + thumb_h, (x2 - x1) / 2,
                     fill=color, outline=color)

    def _set_bar_hover(self, hover: bool):
        self._bar_hover = hover
        self._draw_bar()

    def _bar_jump(self, event):
        width = self.bar.winfo_width()
        height = self.bar.winfo_height()
        if width <= 1 or height <= 1:
            return
        pad = s(6)
        track_h = max(1, height - 2 * pad)
        thumb_frac = max(0.0, min(1.0, self._bar_last - self._bar_first))
        fraction = (event.y - pad) / track_h - thumb_frac / 2
        self.canvas.yview_moveto(max(0.0, min(1.0, fraction)))

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)

    def pointer_inside(self) -> bool:
        try:
            widget = self.winfo_containing(*self.winfo_pointerxy())
        except tk.TclError:
            return False
        return widget is not None and is_descendant(widget, self)

    def wheel(self, event):
        delta = event.delta
        if delta == 0:
            return
        steps = 2 if abs(delta) >= 120 else 1
        direction = -1 if delta > 0 else 1
        self.canvas.yview_scroll(direction * steps, "units")


class SearchBox(tk.Frame):
    def __init__(self, master, textvariable: tk.StringVar, placeholder: str,
                 on_change, width=280):
        super().__init__(master, bg=SOFT_FILL, width=s(width), height=s(36),
                         highlightthickness=s(1), highlightbackground="#ECF0F6",
                         highlightcolor=PRIMARY)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.var = textvariable
        self.on_change = on_change
        self._focused = False

        self.icon = tk.Canvas(self, width=s(27), height=s(34), bg=SOFT_FILL,
                              highlightthickness=0, bd=0)
        self.icon.pack(side="left", padx=(s(4), 0))
        self._draw_icon()

        self.entry = tk.Entry(self, textvariable=textvariable, font=F["body"],
                              bg=SOFT_FILL, fg=INK, relief="flat", bd=0,
                              insertbackground=INK, width=1)
        self.entry.pack(side="left", fill="both", expand=True,
                        padx=(0, s(24)), pady=(s(7), s(5)))

        self.placeholder = tk.Label(self, text=placeholder, font=F["body"],
                                    bg=SOFT_FILL, fg=MUTED_LIGHT, cursor="xterm")
        self.placeholder.place(x=s(31), rely=0.5, anchor="w")
        self.placeholder.bind("<Button-1>", lambda _e: self.entry.focus_set())

        self.clear_btn = tk.Label(self, text="✕", font=F["small"],
                                  bg=SOFT_FILL, fg=MUTED_LIGHT, cursor="hand2")
        self.clear_btn.bind("<Button-1>", lambda _e: self._clear())
        self.clear_btn.bind("<Enter>", lambda _e: self.clear_btn.configure(fg=INK_SOFT))
        self.clear_btn.bind("<Leave>", lambda _e: self.clear_btn.configure(fg=MUTED_LIGHT))

        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<Escape>", lambda _e: self._clear())
        textvariable.trace_add("write", self._sync)
        self._sync()

    def _draw_icon(self):
        c = self.icon
        c.delete("all")
        width = max(1, s(2))
        c.create_oval(s(7), s(9), s(16), s(18), outline=MUTED_LIGHT, width=width)
        c.create_line(s(15), s(17), s(20), s(22), fill=MUTED_LIGHT,
                       width=width + 1, capstyle="round")

    def _focus_in(self, _event=None):
        self._focused = True
        self.configure(highlightbackground=PRIMARY, highlightcolor=PRIMARY)
        self._sync()

    def _focus_out(self, _event=None):
        self._focused = False
        self.configure(highlightbackground="#ECF0F6", highlightcolor=PRIMARY)
        self._sync()

    def _sync(self, *_args):
        text = self.var.get()
        if text and not self._focused:
            self.placeholder.place_forget()
        elif not text and not self._focused:
            self.placeholder.place(x=s(31), rely=0.5, anchor="w")
        else:
            self.placeholder.place_forget()
        if text:
            self.clear_btn.place(relx=1.0, rely=0.5, x=-s(9), anchor="e")
        else:
            self.clear_btn.place_forget()
        if self.on_change:
            self.on_change()

    def _clear(self):
        self.var.set("")
        self.entry.focus_set()

    def focus(self):
        self.entry.focus_set()
        self.entry.icursor("end")


class NavItem(tk.Frame):
    def __init__(self, master, label, command, count=0, dot=None, active=False,
                 font=None, show_dot=True):
        super().__init__(master, bg=SIDEBAR, height=s(38), cursor="hand2")
        self.pack_propagate(False)
        self.command = command
        self.active = active
        self.show_dot = show_dot
        self._hover = False

        self.indicator = tk.Frame(self, width=s(3), bg=ACCENT_NAV if active else SIDEBAR)
        self.indicator.pack(side="left", fill="y")

        self.body = tk.Frame(self, bg=SIDEBAR_ACTIVE if active else SIDEBAR,
                             cursor="hand2")
        self.body.pack(side="left", fill="both", expand=True)

        self.dot = None
        if show_dot:
            self.dot = tk.Canvas(self.body, width=s(8), height=s(8),
                                 bg=SIDEBAR_ACTIVE if active else SIDEBAR,
                                 highlightthickness=0, bd=0, cursor="hand2")
            self.dot.pack(side="left", padx=(s(15), s(9)))
            self.dot.create_oval(0, 0, s(8), s(8), fill=dot or MUTED_LIGHT, outline="")

        self.text = tk.Label(self.body, text=label,
                             font=font or (F["nav_active"] if active else F["nav"]),
                             fg=SIDEBAR_TEXT_ACTIVE if active else SIDEBAR_TEXT,
                             bg=SIDEBAR_ACTIVE if active else SIDEBAR,
                             cursor="hand2", anchor="w")
        self.text.pack(side="left", fill="x", expand=True,
                       padx=(0 if show_dot else s(22), s(6)))

        self.count = tk.Label(self.body, text=str(count), font=F["tiny"],
                              fg="#FFFFFF" if active else SIDEBAR_COUNT_FG,
                              bg="#2A3B58" if active else SIDEBAR_COUNT_BG,
                              padx=s(7), pady=s(1), cursor="hand2")
        self.count.pack(side="right", padx=(s(4), s(13)))

        widgets = [self, self.body, self.text, self.count]
        if self.dot is not None:
            widgets.append(self.dot)
        for w in widgets:
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)

    def _click(self, _event=None):
        if self.command:
            self.command()

    def _enter(self, _event=None):
        if self.active or self._hover:
            return
        self._hover = True
        self._paint(SIDEBAR_HOVER)

    def _leave(self, _event=None):
        if self.active or not self._hover:
            return
        self.after(25, self._check_leave)

    def _check_leave(self):
        if not self._hover or self.active:
            return
        try:
            under = self.winfo_containing(*self.winfo_pointerxy())
        except tk.TclError:
            under = None
        if under is None or not is_descendant(under, self):
            self._hover = False
            self._paint(SIDEBAR)

    def _paint(self, bg):
        self.body.configure(bg=bg)
        self.text.configure(bg=bg)
        if self.dot is not None:
            self.dot.configure(bg=bg)
        self.text.configure(fg=SIDEBAR_TEXT_ACTIVE if (self.active or bg != SIDEBAR) else SIDEBAR_TEXT)

    def set_active(self, active: bool):
        self.active = active
        self._hover = False
        bg = SIDEBAR_ACTIVE if active else SIDEBAR
        self.indicator.configure(bg=ACCENT_NAV if active else SIDEBAR)
        self.body.configure(bg=bg)
        self.text.configure(bg=bg, fg=SIDEBAR_TEXT_ACTIVE if active else SIDEBAR_TEXT,
                            font=F["nav_active"] if active else F["nav"])
        self.count.configure(bg="#2A3B58" if active else SIDEBAR_COUNT_BG,
                             fg="#FFFFFF" if active else SIDEBAR_COUNT_FG)
        if self.dot is not None:
            self.dot.configure(bg=bg)

    def set_count(self, count: int):
        self.count.configure(text=str(count))


ACCENT_NAV = "#3B82F6"


class CloudStatusRow(tk.Frame):
    def __init__(self, master, command):
        super().__init__(master, bg=SIDEBAR, height=s(56), cursor="hand2")
        self.pack_propagate(False)
        self.command = command
        self._hover = False
        self._row_color = "#7B8CA3"

        self.dot = tk.Canvas(self, width=s(12), height=s(56), bg=SIDEBAR,
                             highlightthickness=0, bd=0, cursor="hand2")
        self.dot.pack(side="left", padx=(s(15), s(8)))
        self._dot_item = self.dot.create_oval(s(3), s(25), s(9), s(31),
                                              fill=self._row_color, outline="")

        text_box = tk.Frame(self, bg=SIDEBAR, cursor="hand2")
        text_box.pack(side="left", fill="both", expand=True)
        self.title = tk.Label(text_box, text="Awan & Sync", font=F["small"],
                              bg=SIDEBAR, fg=SIDEBAR_TEXT, anchor="w",
                              cursor="hand2")
        self.title.pack(anchor="w", pady=(s(8), 0))
        self.subtitle = tk.Label(text_box, text="Tidak disediakan", font=F["micro"],
                                 bg=SIDEBAR, fg="#6C7E96", anchor="w",
                                 cursor="hand2")
        self.subtitle.pack(anchor="w", pady=(s(1), s(8)))

        self.chevron = tk.Label(self, text="›", font=F["small"], bg=SIDEBAR,
                                fg="#5A6B85", cursor="hand2")
        self.chevron.pack(side="right", padx=(s(2), s(14)))

        self._widgets = [self, self.dot, text_box, self.title, self.subtitle,
                         self.chevron]
        for widget in self._widgets:
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

    def _click(self, _event=None):
        if self.command:
            self.command()

    def _paint(self, bg):
        self.configure(bg=bg)
        self.dot.configure(bg=bg)
        for widget in (self.title, self.subtitle, self.chevron):
            widget.configure(bg=bg)
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=bg)

    def _enter(self, _event=None):
        if not self._hover:
            self._hover = True
            self._paint(SIDEBAR_HOVER)

    def _leave(self, _event=None):
        if not self._hover:
            return
        self.after(25, self._check_leave)

    def _check_leave(self):
        if not self._hover:
            return
        try:
            under = self.winfo_containing(*self.winfo_pointerxy())
        except tk.TclError:
            under = None
        if under is None or not is_descendant(under, self):
            self._hover = False
            self._paint(SIDEBAR)

    def set_state(self, state: dict):
        self._row_color = state.get("color", "#7B8CA3")
        self.dot.itemconfigure(self._dot_item, fill=self._row_color)
        self.subtitle.configure(text=state.get("label", ""),
                                fg=self._row_color)


class StatCard(tk.Frame):
    def __init__(self, master, label, icon_kind, accent, soft):
        super().__init__(master, bg=CARD, highlightthickness=s(1),
                         highlightbackground=BORDER, height=s(101))
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self.icon = tk.Canvas(self, width=s(38), height=s(38), bg=CARD,
                              highlightthickness=0, bd=0)
        self.icon.grid(row=0, column=0, rowspan=3, sticky="n",
                       padx=(s(15), s(12)), pady=(s(16), 0))
        draw_icon(self.icon, icon_kind, accent, soft, s(38))

        self.label = tk.Label(self, text=label.upper(), font=F["stat_label"],
                              bg=CARD, fg=MUTED, anchor="w")
        self.label.grid(row=0, column=1, sticky="w", pady=(s(15), 0),
                        padx=(0, s(12)))
        self.value = tk.Label(self, text="0", font=F["stat"], bg=CARD, fg=INK,
                              anchor="w")
        self.value.grid(row=1, column=1, sticky="w", pady=(s(0), 0),
                        padx=(0, s(12)))
        self.caption = tk.Label(self, text="", font=F["tiny"], bg=CARD,
                                fg=MUTED_LIGHT, anchor="w")
        self.caption.grid(row=2, column=1, sticky="w", pady=(s(0), s(12)),
                          padx=(0, s(10)))

    def update_values(self, value, caption):
        self.value.configure(text=str(value))
        self.caption.configure(text=caption)


class LoanRow(tk.Frame):
    def __init__(self, master, loan, on_open):
        super().__init__(master, bg=CARD)
        self.loan = loan
        self.on_open = on_open
        self._hover = False

        self.content = tk.Frame(self, bg=CARD, height=s(61))
        self.content.pack(fill="x", padx=s(18))
        self.content.pack_propagate(False)
        self.content.grid_propagate(False)

        for col, weight, min_w in TABLE_COLS:
            self.content.grid_columnconfigure(col, weight=weight, uniform="table",
                                              minsize=s(min_w))
        self.content.grid_columnconfigure(ACTION_COL, weight=0, minsize=s(ACTION_WIDTH))
        self.content.grid_rowconfigure(0, weight=1)

        self._bg_widgets = []
        self._bind_widgets = []

        # Applicant cell -----------------------------------------------------
        applicant = tk.Frame(self.content, bg=CARD)
        applicant.grid(row=0, column=0, sticky="nsew")
        applicant.grid_columnconfigure(1, weight=1)
        applicant.grid_rowconfigure(0, weight=1)

        name = loan["name"] or ""
        idx = sum(ord(ch) for ch in (loan["ic"] or name)) % len(AVATAR_PALETTE)
        avatar_fill, avatar_ink = AVATAR_PALETTE[idx]
        self.avatar = tk.Canvas(applicant, width=s(34), height=s(34), bg=CARD,
                                highlightthickness=0, bd=0)
        self.avatar.grid(row=0, column=0, padx=(0, s(10)))
        self.avatar.create_oval(1, 1, s(34) - 1, s(34) - 1,
                                fill=avatar_fill, outline="")
        self.avatar.create_text(s(17), s(17), text=initials(name),
                                font=F["avatar"], fill=avatar_ink)

        name_box = tk.Frame(applicant, bg=CARD)
        name_box.grid(row=0, column=1, sticky="w")
        self.name_label = tk.Label(name_box, text=clip(name, 22), font=F["body_bold"],
                                   bg=CARD, fg=INK, anchor="w")
        self.name_label.pack(anchor="w")
        self.car_label = tk.Label(name_box, text=clip(loan["car"], 27), font=F["small"],
                                  bg=CARD, fg=MUTED, anchor="w")
        self.car_label.pack(anchor="w", pady=(s(1), 0))

        # IC -----------------------------------------------------------------
        ic_cell = tk.Frame(self.content, bg=CARD)
        ic_cell.grid(row=0, column=1, sticky="nsew")
        ic_cell.grid_columnconfigure(0, weight=1)
        ic_cell.grid_rowconfigure(0, weight=1)
        self.ic_label = tk.Label(ic_cell, text=format_ic(loan["ic"]), font=F["label"],
                                 bg=CARD, fg=INK_SOFT, anchor="w")
        self.ic_label.grid(sticky="nsew")

        # Bank ---------------------------------------------------------------
        bank_cell = tk.Frame(self.content, bg=CARD)
        bank_cell.grid(row=0, column=2, sticky="nsew")
        bank_cell.grid_columnconfigure(0, weight=1)
        bank_cell.grid_rowconfigure(0, weight=1)
        self.bank_label = tk.Label(bank_cell, text=clip(loan["bank"], 21), font=F["label"],
                                   bg=CARD, fg=INK_SOFT, anchor="w")
        self.bank_label.grid(sticky="nsew")

        # Amount -------------------------------------------------------------
        amt_cell = tk.Frame(self.content, bg=CARD)
        amt_cell.grid(row=0, column=3, sticky="nsew")
        amt_cell.grid_columnconfigure(0, weight=1)
        amt_cell.grid_rowconfigure(0, weight=1)
        self.amount_label = tk.Label(amt_cell, text=clip(fmt_money(loan["amount"]), 13),
                                     font=F["body_bold"], bg=CARD, fg=INK, anchor="e")
        self.amount_label.grid(sticky="nsew", padx=(0, s(13)))

        # Date ---------------------------------------------------------------
        date_cell = tk.Frame(self.content, bg=CARD)
        date_cell.grid(row=0, column=4, sticky="nsew")
        date_cell.grid_columnconfigure(0, weight=1)
        date_cell.grid_rowconfigure(0, weight=1)
        date_box = tk.Frame(date_cell, bg=CARD)
        date_box.grid(sticky="w")
        self.date_label = tk.Label(date_box, text=fmt_date(loan["applied_date"]),
                                   font=F["label"], bg=CARD, fg=INK_SOFT, anchor="w")
        self.date_label.pack(anchor="w")
        self.age_label = tk.Label(date_box, text=relative_days(loan["applied_date"]),
                                  font=F["micro"], bg=CARD, fg=MUTED_LIGHT, anchor="w")
        self.age_label.pack(anchor="w", pady=(s(1), 0))

        # Status -------------------------------------------------------------
        status_cell = tk.Frame(self.content, bg=CARD)
        status_cell.grid(row=0, column=5, sticky="nsew")
        status_cell.grid_columnconfigure(0, weight=1)
        status_cell.grid_rowconfigure(0, weight=1)
        self.pill = StatusPill(status_cell, loan["status"], bg=CARD,
                               font=F["pill_md"], fixed_width=94)
        self.pill.grid(sticky="w")

        # Chevron ------------------------------------------------------------
        action_cell = tk.Frame(self.content, bg=CARD)
        action_cell.grid(row=0, column=ACTION_COL, sticky="nsew")
        action_cell.grid_columnconfigure(0, weight=1)
        action_cell.grid_rowconfigure(0, weight=1)
        self.chevron = tk.Canvas(action_cell, width=s(24), height=s(24), bg=CARD,
                                 highlightthickness=0, bd=0, cursor="hand2")
        self.chevron.grid(sticky="e")
        self.chevron_text = self.chevron.create_text(s(12), s(12), text="›",
                                                     font=F["chev"], fill=MUTED_LIGHT)
        self.chevron.bind("<Button-1>", self._open)

        for w in (self, self.content, applicant, self.avatar, name_box, self.name_label,
                  self.car_label, ic_cell, self.ic_label, bank_cell, self.bank_label,
                  amt_cell, self.amount_label, date_cell, date_box, self.date_label,
                  self.age_label, status_cell, self.pill, action_cell, self.chevron):
            self._bg_widgets.append(w)
            self._bind_widgets.append(w)

        for w in self._bind_widgets:
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")
            if w is not self.chevron:
                w.bind("<Double-Button-1>", self._open, add="+")

    def _open(self, _event=None):
        if self.on_open:
            self.on_open()

    def _enter(self, _event=None):
        if self._hover:
            return
        self._hover = True
        self._paint(True)

    def _leave(self, _event=None):
        if not self._hover:
            return
        self.after(25, self._check_leave)

    def _check_leave(self):
        if not self._hover:
            return
        try:
            under = self.winfo_containing(*self.winfo_pointerxy())
        except tk.TclError:
            under = None
        if under is None or not is_descendant(under, self):
            self._hover = False
            self._paint(False)

    def _paint(self, hover: bool):
        bg = ROW_HOVER if hover else CARD
        for widget in self._bg_widgets:
            widget.configure(bg=bg)
        self.chevron.itemconfigure(self.chevron_text,
                                   fill=PRIMARY if hover else MUTED_LIGHT)


# ------------------------------------------------------------- dialog ------
class LoanDialog(tk.Toplevel):
    def __init__(self, app, loan=None):
        super().__init__(app)
        self.app = app
        self.db = app.db
        self.loan = loan
        self.edit_id = loan["id"] if loan else None
        self._saved = False
        self._validate_cb = self.register(self._validate_ic)
        self._error_fields: dict[str, tk.Frame] = {}
        self._error_keys: set[str] = set()
        self.boxes: dict[str, tk.Frame] = {}
        self.entries: dict[str, tk.Widget] = {}

        self.title("Butiran Pinjaman" if loan else "Tambah Pinjaman Baharu")
        self.configure(bg=CARD)
        self.resizable(False, False)
        self.transient(app)
        self.withdraw()
        try:
            self.iconphoto(False, app._icon_image)  # type: ignore[attr-defined]
        except Exception:
            pass

        self._build()
        self._populate(loan)
        self._initial_snapshot = self._snapshot()
        self._place_window()
        self.deiconify()
        self.grab_set()
        self.after(60, self._focus_first)

    # -- construction ------------------------------------------------------
    def _build(self):
        width = s(1060) if self.edit_id else s(800)
        height = s(664) if self.edit_id else s(670)
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        width = min(width, wa_w - s(40))
        height = min(height, wa_h - s(50))
        self._target_size = (width, height)
        self.geometry(f"{width}x{height}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=CARD)
        header.grid(row=0, column=0, sticky="ew", padx=s(24), pady=(s(20), s(16)))
        header.grid_columnconfigure(0, weight=1)
        title_box = tk.Frame(header, bg=CARD)
        title_box.grid(row=0, column=0, sticky="w")
        tk.Label(title_box,
                 text="Butiran Pinjaman" if self.edit_id else "Tambah Pinjaman Baharu",
                 font=F["dialog_title"], bg=CARD, fg=INK, anchor="w").pack(anchor="w")
        tk.Label(title_box,
                 text=("Kemas kini maklumat dan pantau sejarah status."
                       if self.edit_id else
                       "Masukkan butiran permohonan pelanggan."),
                 font=F["label"], bg=CARD, fg=MUTED, anchor="w").pack(anchor="w",
                                                                      pady=(s(3), 0))
        close = tk.Label(header, text="✕", font=F["body_lg"], bg=CARD, fg=MUTED_LIGHT,
                         cursor="hand2")
        close.grid(row=0, column=1, sticky="ne")
        close.bind("<Button-1>", lambda _e: self._request_close())
        close.bind("<Enter>", lambda _e: close.configure(fg=INK))
        close.bind("<Leave>", lambda _e: close.configure(fg=MUTED_LIGHT))
        self._close_label = close

        tk.Frame(self, bg=BORDER, height=s(1)).grid(row=1, column=0, sticky="ew")

        body = tk.Frame(self, bg=CARD)
        body.grid(row=2, column=0, sticky="nsew", padx=s(24), pady=(s(18), s(12)))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        form = tk.Frame(body, bg=CARD)
        form.grid(row=0, column=0, sticky="nsew")
        form.grid_columnconfigure(0, weight=1, uniform="form")
        form.grid_columnconfigure(1, weight=1, uniform="form")
        self._build_form(form)

        if self.edit_id:
            body.grid_columnconfigure(2, weight=0, minsize=s(292))
            divider = tk.Frame(body, bg=BORDER, width=s(1))
            divider.grid(row=0, column=1, sticky="ns", padx=(s(18), s(18)))
            panel = tk.Frame(body, bg="#F8FAFD")
            panel.grid(row=0, column=2, sticky="nsew")
            panel.grid_columnconfigure(0, weight=1)
            panel.grid_rowconfigure(2, weight=1)
            tk.Label(panel, text="Sejarah Status", font=F["body_bold"], bg="#F8FAFD",
                     fg=INK, anchor="w").grid(row=0, column=0, sticky="w",
                                              padx=s(16), pady=(s(15), 0))
            tk.Label(panel, text="Direkodkan secara automatik.",
                     font=F["small"], bg="#F8FAFD", fg=MUTED, anchor="w").grid(
                row=1, column=0, sticky="w", padx=s(16), pady=(s(2), s(10)))
            self.history_scroll = ScrollFrame(panel, bg="#F8FAFD")
            self.history_scroll.grid(row=2, column=0, sticky="nsew",
                                     padx=(s(12), s(6)), pady=(0, s(10)))
            self._load_history()

        # footer
        tk.Frame(self, bg=BORDER, height=s(1)).grid(row=3, column=0, sticky="ew")
        footer = tk.Frame(self, bg=FOOTER_BG)
        footer.grid(row=4, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)
        left = tk.Frame(footer, bg=FOOTER_BG)
        left.grid(row=0, column=0, sticky="w", padx=(s(24), s(12)), pady=s(14))
        if self.edit_id:
            self.delete_btn = RoundButton(left, "Padam", command=self._delete,
                                          kind="danger", bg=FOOTER_BG, height=38)
            self.delete_btn.pack(side="left", padx=(0, s(12)))
        self.error_label = tk.Label(left, text="", font=F["error"], bg=FOOTER_BG,
                                    fg=DANGER, anchor="w", justify="left",
                                    wraplength=s(430))
        self.error_label.pack(side="left")

        right = tk.Frame(footer, bg=FOOTER_BG)
        right.grid(row=0, column=2, sticky="e", padx=(s(12), s(24)), pady=s(14))
        RoundButton(right, "Batal", command=self._request_close, kind="ghost",
                    bg=FOOTER_BG, height=38).pack(side="left", padx=(0, s(10)))
        RoundButton(right, "Simpan", command=self._save, kind="primary",
                    bg=FOOTER_BG, height=38, padx=23).pack(side="left")

        self.bind("<Escape>", lambda _e: self._request_close())
        self.bind("<Control-s>", lambda _e: self._save())
        self.bind("<Control-S>", lambda _e: self._save())
        self.bind("<MouseWheel>", self._on_wheel, add="+")
        self.protocol("WM_DELETE_WINDOW", self._request_close)

    def _on_wheel(self, event):
        if hasattr(self, "history_scroll") and self.history_scroll.pointer_inside():
            self.history_scroll.wheel(event)

    def _build_form(self, form):
        def label(text, row, col, span=1, pad_right=0, pad_left=0, top=0):
            frame = tk.Frame(form, bg=CARD)
            tk.Label(frame, text=text, font=F["field_label"], bg=CARD, fg=INK_SOFT,
                     anchor="w").pack(side="left")
            frame.grid(row=row, column=col, columnspan=span, sticky="w",
                       padx=(pad_left, pad_right), pady=(s(top), s(6)))
            return frame

        def blank_box(row, col, span=1, pad_right=0, pad_left=0, height=40):
            box = tk.Frame(form, bg=CARD, height=s(height),
                           highlightthickness=s(1), highlightbackground=BORDER,
                           highlightcolor=PRIMARY)
            box.grid(row=row, column=col, columnspan=span, sticky="ew",
                     padx=(pad_left, pad_right))
            box.grid_propagate(False)
            box.grid_rowconfigure(0, weight=1)
            box.grid_columnconfigure(0, weight=1)
            return box

        def entry_box(row, col, span=1, pad_right=0, pad_left=0, height=40,
                      prefix=None):
            box = blank_box(row, col, span, pad_right, pad_left, height)
            if prefix:
                tk.Label(box, text=prefix, font=F["label"], bg=CARD, fg=MUTED,
                         anchor="w").grid(row=0, column=0, sticky="w",
                                          padx=(s(10), s(2)))
                entry_col = 1
                box.grid_columnconfigure(0, weight=0)
                box.grid_columnconfigure(1, weight=1)
                pad_left_entry = 2
            else:
                entry_col = 0
                pad_left_entry = 10
            entry = tk.Entry(box, font=F["body"], bg=CARD, fg=INK, relief="flat",
                             bd=0, insertbackground=INK, width=1)
            entry.grid(row=0, column=entry_col, sticky="nsew",
                       padx=(s(pad_left_entry), s(8)), pady=(s(7), s(5)))
            return box, entry

        # Name
        label("Nama Penuh", 0, 0, span=2)
        self.name_box, self.name_entry = entry_box(1, 0, span=2)
        self.name_var = tk.StringVar()
        self.name_entry.configure(textvariable=self.name_var)
        self.boxes["name"] = self.name_box
        self.entries["name"] = self.name_entry

        # IC + car
        label("No. Kad Pengenalan", 2, 0, pad_right=s(8), top=14)
        label("Jenis Kereta", 2, 1, pad_left=s(8), top=14)
        self.ic_box, self.ic_entry = entry_box(3, 0, pad_right=s(8))
        self.ic_entry.configure(validate="key", validatecommand=(self._validate_cb, "%P"))
        self.ic_var = tk.StringVar()
        self.ic_entry.configure(textvariable=self.ic_var)
        self.car_box, self.car_entry = entry_box(3, 1, pad_left=s(8))
        self.car_var = tk.StringVar()
        self.car_entry.configure(textvariable=self.car_var)
        self.boxes["ic"] = self.ic_box
        self.boxes["car"] = self.car_box
        self.entries["ic"] = self.ic_entry
        self.entries["car"] = self.car_entry

        # Bank + amount
        label("Bank", 4, 0, pad_right=s(8), top=14)
        label("Jumlah Pinjaman (RM)", 4, 1, pad_left=s(8), top=14)
        self.bank_box = blank_box(5, 0, pad_right=s(8))
        self.bank_var = tk.StringVar()
        self.bank_combo = ttk.Combobox(self.bank_box, textvariable=self.bank_var,
                                       values=BANKS, style="Field.TCombobox",
                                       font=F["body"])
        self.bank_combo.grid(row=0, column=0, columnspan=2, sticky="nsew",
                             padx=(s(5), s(3)), pady=(s(4), s(4)))
        self.amount_box, self.amount_entry = entry_box(5, 1, pad_left=s(8),
                                                       prefix="RM")
        self.amount_var = tk.StringVar()
        self.amount_entry.configure(textvariable=self.amount_var)
        self.boxes["bank"] = self.bank_box
        self.boxes["amount"] = self.amount_box
        self.entries["bank"] = self.bank_combo
        self.entries["amount"] = self.amount_entry

        # Date + status
        label("Tarikh Mohon", 6, 0, pad_right=s(8), top=14)
        label("Status", 6, 1, pad_left=s(8), top=14)
        self.date_box, self.date_entry = entry_box(7, 0, pad_right=s(8))
        self.date_var = tk.StringVar()
        self.date_entry.configure(textvariable=self.date_var)
        self.status_box = blank_box(7, 1, pad_left=s(8))
        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(self.status_box, textvariable=self.status_var,
                                         values=STATUSES, state="readonly",
                                         style="Field.TCombobox", font=F["body"])
        self.status_combo.grid(row=0, column=0, columnspan=2, sticky="nsew",
                               padx=(s(5), s(3)), pady=(s(4), s(4)))
        self.boxes["date"] = self.date_box
        self.boxes["status"] = self.status_box
        self.entries["date"] = self.date_entry
        self.entries["status"] = self.status_combo

        # Notes
        label("Catatan (pilihan)", 8, 0, span=2, top=14)
        notes_box = tk.Frame(form, bg=CARD, height=s(76),
                             highlightthickness=s(1), highlightbackground=BORDER,
                             highlightcolor=PRIMARY)
        notes_box.grid(row=9, column=0, columnspan=2, sticky="ew")
        notes_box.grid_propagate(False)
        notes_box.grid_rowconfigure(0, weight=1)
        notes_box.grid_columnconfigure(0, weight=1)
        self.notes_text = tk.Text(notes_box, font=F["body"], bg=CARD, fg=INK,
                                  relief="flat", bd=0, wrap="word", height=3,
                                  insertbackground=INK, padx=s(8), pady=s(6),
                                  undo=True)
        self.notes_text.grid(row=0, column=0, sticky="nsew")
        self.boxes["notes"] = notes_box
        self.entries["notes"] = self.notes_text

        hint = tk.Label(form, text="Data disimpan secara setempat pada peranti ini.",
                        font=F["small"], bg=CARD, fg=MUTED_LIGHT, anchor="w")
        hint.grid(row=10, column=0, columnspan=2, sticky="w", pady=(s(16), 0))

        # focus highlight + normalisation
        for key, widget in self.entries.items():
            box = self.boxes[key]
            widget.bind("<FocusIn>", lambda _e, k=key, b=box: self._field_focus_in(k, b),
                        add="+")
            widget.bind("<FocusOut>", lambda _e, k=key, b=box: self._field_focus_out(k, b),
                        add="+")
        self.ic_entry.bind("<FocusOut>", self._normalize_ic, add="+")
        self.date_entry.bind("<FocusOut>", self._normalize_date, add="+")
        self.amount_entry.bind("<FocusOut>", self._normalize_amount, add="+")

    def _load_history(self):
        if not hasattr(self, "history_scroll"):
            return
        self.history_scroll.clear()
        rows = self.db.history_for(self.edit_id) if self.edit_id else []
        if not rows:
            tk.Label(self.history_scroll.inner, text="Tiada sejarah direkodkan.",
                     font=F["small"], bg="#F8FAFD", fg=MUTED_LIGHT,
                     anchor="w").pack(fill="x", padx=s(4), pady=s(8))
            return
        for entry in rows:
            card = tk.Frame(self.history_scroll.inner, bg=CARD,
                            highlightthickness=s(1), highlightbackground="#E7ECF5")
            card.pack(fill="x", padx=(0, s(2)), pady=(0, s(8)))
            fg, _fill = STATUS_STYLES.get(entry["to_status"], UNKNOWN_STATUS_STYLE)
            strip = tk.Frame(card, bg=fg, width=s(3))
            strip.pack(side="left", fill="y")
            body = tk.Frame(card, bg=CARD)
            body.pack(side="left", fill="both", expand=True,
                      padx=s(10), pady=s(8))
            pill = StatusPill(body, entry["to_status"], bg=CARD, font=F["pill"],
                              height=20)
            pill.pack(anchor="w")
            meta = fmt_datetime(entry["changed_at"])
            if entry["from_status"]:
                meta += f"  ·  daripada {entry['from_status']}"
            tk.Label(body, text=meta, font=F["micro"], bg=CARD, fg=MUTED_LIGHT,
                     anchor="w", justify="left", wraplength=s(220)).pack(
                anchor="w", pady=(s(3), 0))
            note = (entry["note"] or "").strip()
            if note and note != "Status dikemas kini":
                tk.Label(body, text=note, font=F["micro"], bg=CARD, fg=INK_SOFT,
                         anchor="w", justify="left", wraplength=s(220)).pack(
                    anchor="w", pady=(s(2), 0))

    def _populate(self, loan):
        if loan:
            self.name_var.set(loan["name"] or "")
            self.ic_var.set(format_ic(loan["ic"] or ""))
            self.car_var.set(loan["car"] or "")
            self.bank_var.set(loan["bank"] or "")
            self.amount_var.set(fmt_money_input(loan["amount"]))
            try:
                d = date.fromisoformat(str(loan["applied_date"])[:10])
                self.date_var.set(d.strftime("%d/%m/%Y"))
            except (ValueError, TypeError):
                self.date_var.set("")
            self.status_var.set(loan["status"] or "Baru")
            self.notes_text.insert("1.0", loan["notes"] or "")
        else:
            self.date_var.set(date.today().strftime("%d/%m/%Y"))
            self.status_var.set("Baru")
            self.bank_var.set("")

    def _place_window(self):
        self.update_idletasks()
        width, height = self._target_size
        parent = self.app
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        px = max(wa_x + s(10), min(px, wa_x + wa_w - width - s(20)))
        py = max(wa_y + s(10), min(py, wa_y + wa_h - height - s(30)))
        self.geometry(f"{width}x{height}+{px}+{py}")

    def _focus_first(self):
        try:
            self.name_entry.focus_set()
            self.name_entry.icursor("end")
        except tk.TclError:
            pass

    # -- validation helpers ------------------------------------------------
    def _validate_ic(self, proposed: str) -> bool:
        digits = re.sub(r"\D", "", proposed)
        return len(digits) <= 12 and all(ch.isdigit() or ch in "- " for ch in proposed)

    def _field_focus_in(self, key, box):
        if key in self._error_keys:
            return
        box.configure(highlightbackground=PRIMARY, highlightcolor=PRIMARY)

    def _field_focus_out(self, key, box):
        if key in self._error_keys:
            return
        box.configure(highlightbackground=BORDER, highlightcolor=PRIMARY)

    def _normalize_ic(self, _event=None):
        raw = self.ic_var.get().strip()
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 12:
            self.ic_var.set(format_ic(digits))

    def _normalize_date(self, _event=None):
        raw = self.date_var.get().strip()
        if not raw:
            return
        try:
            self.date_var.set(parse_date(raw).strftime("%d/%m/%Y"))
        except ValueError:
            pass

    def _normalize_amount(self, _event=None):
        raw = self.amount_var.get().strip()
        if not raw:
            return
        try:
            value = parse_amount(raw)
        except ValueError:
            return
        self.amount_var.set(fmt_money_input(value))

    def _clear_errors(self):
        self._error_keys.clear()
        for box in self.boxes.values():
            box.configure(highlightbackground=BORDER, highlightcolor=PRIMARY)
        self.error_label.configure(text="")
        self._error_fields.clear()

    def _mark_error(self, key: str, message: str):
        self._clear_errors()
        self.error_label.configure(text=message)
        widget = self.entries.get(key)
        if widget is not None:
            try:
                widget.focus_set()
            except tk.TclError:
                pass
        if key in self.boxes:
            self._error_keys.add(key)
            self.boxes[key].configure(highlightbackground=DANGER, highlightcolor=DANGER)
            self._error_fields[key] = self.boxes[key]

    def _collect(self):
        name = self.name_var.get().strip()
        if len(name) < 2:
            return None, ("name", "Sila masukkan nama penuh pemohon.")
        raw_ic = self.ic_var.get()
        ic_digits = re.sub(r"\D", "", raw_ic)
        if len(ic_digits) != 12:
            return None, ("ic", "No. IC mesti mengandungi 12 digit (cth. 900101-14-5678).")
        car = self.car_var.get().strip()
        if not car:
            return None, ("car", "Sila masukkan jenis atau model kereta.")
        bank = self.bank_var.get().strip()
        if not bank:
            return None, ("bank", "Sila pilih atau masukkan nama bank.")
        try:
            amount = parse_amount(self.amount_var.get())
        except ValueError:
            return None, ("amount", "Jumlah pinjaman tidak sah. Masukkan nombor sahaja.")
        raw_date = self.date_var.get().strip()
        if not raw_date:
            return None, ("date", "Sila masukkan tarikh permohonan (DD/MM/YYYY).")
        try:
            applied = parse_date(raw_date)
        except ValueError:
            return None, ("date", "Tarikh tidak sah. Gunakan format DD/MM/YYYY.")
        status = self.status_var.get().strip()
        if status not in STATUSES:
            return None, ("status", "Sila pilih status pinjaman.")
        notes = self.notes_text.get("1.0", "end-1c").strip()
        return {
            "name": name,
            "ic": ic_digits,
            "car": car,
            "bank": bank,
            "amount": amount,
            "applied_date": applied.isoformat(),
            "status": status,
            "notes": notes,
        }, None

    def _snapshot(self):
        return (
            self.name_var.get(), self.ic_var.get(), self.car_var.get(),
            self.bank_var.get(), self.amount_var.get(), self.date_var.get(),
            self.status_var.get(), self.notes_text.get("1.0", "end-1c"),
        )

    # -- actions -----------------------------------------------------------
    def _save(self):
        self._clear_errors()
        data, error = self._collect()
        if error:
            self._mark_error(*error)
            return
        try:
            if self.edit_id:
                self.db.update_loan(self.edit_id, data)
                action, loan_id, message = "updated", self.edit_id, "Rekod dikemas kini."
            else:
                loan_id = self.db.create_loan(data)
                action, message = "created", "Pinjaman baharu ditambah."
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Simpan gagal",
                f"Rekod tidak dapat disimpan.\n\n{exc}",
                parent=self,
            )
            return
        self._saved = True
        self.destroy()
        self.app.after_dialog(action, loan_id)
        self.app.toast(message)

    def _delete(self):
        name = self.name_var.get().strip() or "rekod ini"
        confirm = messagebox.askyesno(
            "Padam pinjaman",
            f"Padam rekod untuk {name}?\n\nSemua sejarah status juga akan dipadam. "
            "Tindakan ini tidak boleh dibatalkan.",
            parent=self,
            icon="warning",
        )
        if not confirm:
            return
        try:
            self.db.delete_loan(self.edit_id)
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Padam gagal",
                f"Rekod tidak dapat dipadam.\n\n{exc}",
                parent=self,
            )
            return
        self._saved = True
        self.destroy()
        self.app.after_dialog("deleted", self.edit_id)
        self.app.toast("Rekod dipadam.")

    def _request_close(self):
        if not self._saved and self._snapshot() != self._initial_snapshot:
            if not messagebox.askyesno(
                "Perubahan belum disimpan",
                "Tutup tanpa menyimpan perubahan?",
                parent=self,
                icon="warning",
            ):
                return
        self.destroy()

    def destroy(self):
        if getattr(self.app, "_dialog", None) is self:
            self.app._dialog = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        super().destroy()


# ------------------------------------------------------------- cloud UI ----
class FirebaseGuideDialog(tk.Toplevel):
    def __init__(self, parent, on_close=None):
        super().__init__(parent)
        self._on_close = on_close
        self.title("Panduan Firebase")
        self.configure(bg=CARD)
        self.resizable(False, False)
        self.transient(parent)
        self._build()
        self._place(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _e: self._close())
        self.after(80, self.focus_force)

    def _build(self):
        width, height = s(700), s(700)
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        self._target_size = (min(width, wa_w - s(40)),
                             min(height, wa_h - s(50)))
        self.geometry(f"{self._target_size[0]}x{self._target_size[1]}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=CARD)
        header.grid(row=0, column=0, sticky="ew", padx=s(24), pady=(s(20), s(12)))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="Panduan Persediaan Firebase", font=F["dialog_title"],
                 bg=CARD, fg=INK, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(header, text="Lakukan sekali sahaja dalam Firebase Console.",
                 font=F["label"], bg=CARD, fg=MUTED, anchor="w").grid(
            row=1, column=0, sticky="w", pady=(s(3), 0))
        close = tk.Label(header, text="✕", font=F["body_lg"], bg=CARD,
                         fg=MUTED_LIGHT, cursor="hand2")
        close.grid(row=0, column=1, rowspan=2, sticky="ne")
        close.bind("<Button-1>", lambda _e: self._close())
        close.bind("<Enter>", lambda _e: close.configure(fg=INK))
        close.bind("<Leave>", lambda _e: close.configure(fg=MUTED_LIGHT))

        tk.Frame(self, bg=BORDER, height=s(1)).grid(row=1, column=0, sticky="ew")

        body = tk.Frame(self, bg=CARD)
        body.grid(row=2, column=0, sticky="nsew", padx=s(24), pady=(s(12), s(8)))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        text = tk.Text(body, font=F["body"], bg=CARD, fg=INK_SOFT, relief="flat",
                       bd=0, wrap="word", insertbackground=INK, padx=s(4),
                       pady=s(4), spacing1=s(1), spacing3=s(4))
        scroll = tk.Scrollbar(body, orient="vertical", command=text.yview,
                              width=s(10), relief="flat", bd=0,
                              bg="#CBD5E1", troughcolor=CARD,
                              activebackground="#A8B7C9")
        text.configure(yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns", padx=(s(6), 0))
        text.tag_configure("h", font=F["body_bold"], foreground=INK,
                           spacing1=s(8), spacing3=s(3))
        text.tag_configure("step", font=F["body"], foreground=INK_SOFT,
                           lmargin1=s(4), lmargin2=s(20), spacing3=s(5))
        text.tag_configure("note", font=F["small"], foreground=MUTED,
                           spacing3=s(4))
        text.tag_configure("code", font=("Consolas", -s(10)),
                           background="#F4F6FA", foreground=INK, lmargin1=s(10),
                           lmargin2=s(10), spacing1=s(2), spacing3=s(2))

        def add(text_value, tag=None):
            text.insert("end", text_value, tag or ())

        add("1. Cipta projek Firebase\n", "h")
        add("Buka Firebase Console, klik Add project, namakan projek dan cipta. "
            "Anda boleh abaikan Google Analytics untuk projek ini.\n", "step")
        add("2. Aktifkan Email/Password\n", "h")
        add("Authentication → Get started → Sign-in method → Email/Password → "
            "Enable → Save.\n", "step")
        add("3. Cipta Firestore Database\n", "h")
        add("Firestore Database → Create database → pilih edisi Standard "
            "(Native mode), gunakan database (default) jika diminta, pilih "
            "lokasi terdekat (contoh asia-southeast1), Production mode → Create. "
            "Jangan pilih mod MongoDB/Enterprise untuk app ini.\n", "step")
        add("4. Terbitkan peraturan keselamatan\n", "h")
        add("Buka tab Rules, gantikan kandungan dengan peraturan di bawah, "
            "kemudian tekan Publish. Ini memastikan hanya akaun anda boleh "
            "membaca data anda.\n", "step")
        add(fb.FIREBASE_RULES + "\n", "code")
        add("\n5. Daftarkan Web App dan salin konfigurasi\n", "h")
        add("Project settings (ikon gear) → General → Your apps → Add app → "
            "Web. Daftarkan app, kemudian salin nilai projectId dan apiKey "
            "daripada objek firebaseConfig.\n", "step")
        add("6. Masukkan konfigurasi dalam LoanTrack\n", "h")
        add("Kembali ke dialog Awan & Sync, masukkan Project ID dan Web API "
            "key, simpan, kemudian daftar akaun kata laluan email anda.\n", "step")
        add("Nota API key\n", "h")
        add("Jika anda mengehadkan API key dalam Google Cloud Console, pastikan "
            "Identity Toolkit API dan Cloud Firestore API dibenarkan. Jangan "
            "gunakan sekatan HTTP referrer kerana aplikasi desktop tidak menghantar "
            "referrer.\n", "note")
        add("Nota privasi\n", "h")
        add("Jangan guna peraturan Test mode untuk data sebenar. Data IC akan "
            "disimpan di Firestore dan tertakluk kepada dasar privasi anda. "
            "Kata laluan tidak disimpan oleh LoanTrack.\n", "note")
        text.configure(state="disabled")

        tk.Frame(self, bg=BORDER, height=s(1)).grid(row=3, column=0, sticky="ew")
        footer = tk.Frame(self, bg=FOOTER_BG)
        footer.grid(row=4, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        RoundButton(footer, "Buka Firebase Console",
                    command=lambda: webbrowser.open("https://console.firebase.google.com/"),
                    kind="ghost", bg=FOOTER_BG, height=36).grid(
            row=0, column=1, padx=(s(24), s(8)), pady=s(13))
        RoundButton(footer, "Salin Peraturan", command=self._copy_rules,
                    kind="soft", bg=FOOTER_BG, height=36).grid(
            row=0, column=2, padx=(0, s(8)), pady=s(13))
        RoundButton(footer, "Tutup", command=self._close, kind="primary",
                    bg=FOOTER_BG, height=36, padx=20).grid(
            row=0, column=3, padx=(0, s(24)), pady=s(13))

    def _copy_rules(self):
        self.clipboard_clear()
        self.clipboard_append(fb.FIREBASE_RULES)
        self.update()

    def _place(self, parent):
        self.update_idletasks()
        width, height = self._target_size
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        px = max(wa_x + s(10), min(px, wa_x + wa_w - width - s(20)))
        py = max(wa_y + s(10), min(py, wa_y + wa_h - height - s(30)))
        self.geometry(f"{width}x{height}+{px}+{py}")

    def _close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        if self._on_close:
            self._on_close()


class CloudDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.manager = app.cloud
        self._editing_config = not self.manager.configured
        self._message = ""
        self._message_error = False
        self._auth_fields_ready = False

        self.title("Awan & Sync")
        self.configure(bg=CARD)
        self.resizable(False, False)
        self.transient(app)
        self.withdraw()
        self._build()
        self._refresh(populate_config=True)
        self._place_window()
        self.deiconify()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Escape>", lambda _e: self._close())

    def _build(self):
        width, height = s(740), s(640)
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        width = min(width, wa_w - s(40))
        height = min(height, wa_h - s(50))
        self._target_size = (width, height)
        self.geometry(f"{width}x{height}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=CARD)
        header.grid(row=0, column=0, sticky="ew", padx=s(24), pady=(s(20), s(16)))
        header.grid_columnconfigure(0, weight=1)
        title_box = tk.Frame(header, bg=CARD)
        title_box.grid(row=0, column=0, sticky="w")
        tk.Label(title_box, text="Awan & Sync", font=F["dialog_title"], bg=CARD,
                 fg=INK, anchor="w").pack(anchor="w")
        tk.Label(title_box, text="Firebase Firestore · data setempat kekal sebagai sumber utama.",
                 font=F["label"], bg=CARD, fg=MUTED, anchor="w").pack(
            anchor="w", pady=(s(3), 0))
        close = tk.Label(header, text="✕", font=F["body_lg"], bg=CARD,
                         fg=MUTED_LIGHT, cursor="hand2")
        close.grid(row=0, column=1, sticky="ne")
        close.bind("<Button-1>", lambda _e: self._close())
        close.bind("<Enter>", lambda _e: close.configure(fg=INK))
        close.bind("<Leave>", lambda _e: close.configure(fg=MUTED_LIGHT))

        tk.Frame(self, bg=BORDER, height=s(1)).grid(row=1, column=0, sticky="ew")

        body = tk.Frame(self, bg=CARD)
        body.grid(row=2, column=0, sticky="nsew", padx=s(24), pady=(s(16), s(10)))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(4, weight=1)

        # status card
        status = tk.Frame(body, bg="#F7F9FC", highlightthickness=s(1),
                          highlightbackground="#E8EDF5")
        status.grid(row=0, column=0, sticky="ew")
        status.grid_columnconfigure(1, weight=1)
        self.status_dot = tk.Canvas(status, width=s(16), height=s(60),
                                    bg="#F7F9FC", highlightthickness=0, bd=0)
        self.status_dot.grid(row=0, column=0, rowspan=2, padx=(s(14), s(8)))
        self.status_dot_item = self.status_dot.create_oval(
            s(4), s(26), s(12), s(34), fill="#7B8CA3", outline="")
        self.status_title = tk.Label(status, text="", font=F["body_bold"],
                                     bg="#F7F9FC", fg=INK, anchor="w")
        self.status_title.grid(row=0, column=1, sticky="w", pady=(s(12), 0))
        self.status_detail = tk.Label(status, text="", font=F["small"],
                                      bg="#F7F9FC", fg=MUTED, anchor="w",
                                      justify="left", wraplength=s(560))
        self.status_detail.grid(row=1, column=1, sticky="w",
                                pady=(s(2), s(12)), padx=(0, s(14)))

        # config section
        self.config_section = tk.Frame(body, bg=CARD)
        self.config_section.grid(row=1, column=0, sticky="ew", pady=(s(16), 0))
        heading = tk.Frame(self.config_section, bg=CARD)
        heading.pack(fill="x")
        tk.Label(heading, text="Sambungan Firebase", font=F["body_bold"],
                 bg=CARD, fg=INK, anchor="w").pack(side="left")
        guide_link = tk.Label(heading, text="Panduan persediaan", font=F["small"],
                              bg=CARD, fg=PRIMARY, cursor="hand2")
        guide_link.pack(side="right")
        guide_link.bind("<Button-1>", lambda _e: self._open_guide())

        self.config_summary = tk.Frame(self.config_section, bg=CARD)
        self.config_summary.pack(fill="x", pady=(s(8), 0))
        self.project_text = tk.Label(self.config_summary, text="", font=F["label"],
                                     bg=CARD, fg=INK_SOFT, anchor="w")
        self.project_text.pack(side="left")
        self.console_link = tk.Label(self.config_summary, text="Buka Console",
                                     font=F["small"], bg=CARD, fg=PRIMARY,
                                     cursor="hand2")
        self.console_link.pack(side="right", padx=(s(8), 0))
        self.console_link.bind("<Button-1>", lambda _e: self._open_console())
        self.edit_link = tk.Label(self.config_summary, text="Tukar",
                                  font=F["small"], bg=CARD, fg=PRIMARY,
                                  cursor="hand2")
        self.edit_link.pack(side="right", padx=(s(8), 0))
        self.edit_link.bind("<Button-1>", lambda _e: self._start_edit_config())

        self.config_form = tk.Frame(self.config_section, bg=CARD)
        self.project_box, self.project_entry = self._input_field(
            self.config_form, "Project ID")
        self.key_box, self.key_entry = self._input_field(
            self.config_form, "Web API key")
        self._bind_focus(self.project_entry, self.project_box)
        self._bind_focus(self.key_entry, self.key_box)
        tk.Label(self.config_form,
                 text="Dapatkan kedua-duanya di Firebase Console → Project settings → Your apps.",
                 font=F["micro"], bg=CARD, fg=MUTED_LIGHT, anchor="w").pack(
            fill="x", pady=(0, s(8)))
        save_row = tk.Frame(self.config_form, bg=CARD)
        save_row.pack(fill="x")
        RoundButton(save_row, "Simpan Konfigurasi", command=self._save_config,
                    kind="primary", bg=CARD, height=36, padx=16).pack(side="left")
        self.cancel_edit_btn = RoundButton(
            save_row, "Batal", command=self._cancel_edit_config, kind="ghost",
            bg=CARD, height=36, padx=14
        )
        self.cancel_edit_btn.pack(side="left", padx=(s(8), 0))
        self.config_form.pack(fill="x", pady=(s(8), 0))

        # account section
        self.account_section = tk.Frame(body, bg=CARD)
        self.account_section.grid(row=2, column=0, sticky="ew", pady=(s(18), 0))
        tk.Label(self.account_section, text="Akaun", font=F["body_bold"],
                 bg=CARD, fg=INK, anchor="w").pack(anchor="w")

        self.auth_box = tk.Frame(self.account_section, bg=CARD)
        self.auth_box.pack(fill="x", pady=(s(8), 0))
        self.email_box, self.email_entry = self._input_field(
            self.auth_box, "Email", side_by_side=False)
        self.password_box, self.password_entry = self._input_field(
            self.auth_box, "Kata Laluan", side_by_side=False, show="*")
        self._bind_focus(self.email_entry, self.email_box)
        self._bind_focus(self.password_entry, self.password_box)
        self.email_entry.bind("<Return>", lambda _e: self._do_auth(False))
        self.password_entry.bind("<Return>", lambda _e: self._do_auth(False))
        tk.Label(self.auth_box,
                 text="Kata laluan tidak disimpan. Gunakan satu akaun Firebase "
                      "untuk rekod setempat ini.",
                 font=F["micro"], bg=CARD, fg=MUTED_LIGHT, anchor="w",
                 justify="left", wraplength=s(600)).pack(
            fill="x", pady=(0, s(8)))
        auth_buttons = tk.Frame(self.auth_box, bg=CARD)
        auth_buttons.pack(fill="x")
        RoundButton(auth_buttons, "Log Masuk", command=lambda: self._do_auth(False),
                    kind="primary", bg=CARD, height=36, padx=18).pack(side="left")
        RoundButton(auth_buttons, "Daftar Akaun", command=lambda: self._do_auth(True),
                    kind="ghost", bg=CARD, height=36, padx=14).pack(
            side="left", padx=(s(8), 0))

        self.account_box = tk.Frame(self.account_section, bg=CARD)
        self.account_email = tk.Label(self.account_box, text="", font=F["body_bold"],
                                      bg=CARD, fg=INK, anchor="w")
        self.account_email.pack(anchor="w", pady=(s(8), 0))
        self.account_sync = tk.Label(self.account_box, text="", font=F["small"],
                                     bg=CARD, fg=MUTED, anchor="w")
        self.account_sync.pack(anchor="w", pady=(s(2), s(10)))
        account_buttons = tk.Frame(self.account_box, bg=CARD)
        account_buttons.pack(fill="x")
        self.sync_btn = RoundButton(account_buttons, "Sync Sekarang",
                                    command=self._sync_now, kind="primary",
                                    bg=CARD, height=36, padx=18)
        self.sync_btn.pack(side="left")
        RoundButton(account_buttons, "Log Keluar", command=self._logout,
                    kind="danger", bg=CARD, height=36, padx=14).pack(
            side="left", padx=(s(8), 0))
        tk.Label(self.account_box, text="Sync automatik selepas setiap perubahan.",
                 font=F["micro"], bg=CARD, fg=MUTED_LIGHT, anchor="w").pack(
            anchor="w", pady=(s(8), 0))

        self.message_label = tk.Label(body, text="", font=F["small"], bg=CARD,
                                      fg=MUTED, anchor="w", justify="left",
                                      wraplength=s(630))
        self.message_label.grid(row=3, column=0, sticky="w", pady=(s(12), 0))

        # footer
        tk.Frame(self, bg=BORDER, height=s(1)).grid(row=3, column=0, sticky="ew")
        footer = tk.Frame(self, bg=FOOTER_BG)
        footer.grid(row=4, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        RoundButton(footer, "Panduan Firebase", command=self._open_guide,
                    kind="ghost", bg=FOOTER_BG, height=36).grid(
            row=0, column=1, padx=(s(24), s(8)), pady=s(13))
        RoundButton(footer, "Tutup", command=self._close, kind="ghost",
                    bg=FOOTER_BG, height=36, padx=22).grid(
            row=0, column=2, padx=(0, s(24)), pady=s(13))

    def _input_field(self, parent, label, side_by_side=True, show=None):
        block = tk.Frame(parent, bg=CARD)
        block.pack(fill="x", pady=(0, s(10)))
        tk.Label(block, text=label, font=F["field_label"], bg=CARD,
                 fg=INK_SOFT, anchor="w").pack(anchor="w", pady=(0, s(5)))
        box = tk.Frame(block, bg=CARD, height=s(40), highlightthickness=s(1),
                       highlightbackground=BORDER, highlightcolor=PRIMARY)
        box.pack(fill="x")
        box.pack_propagate(False)
        entry = tk.Entry(box, font=F["body"], bg=CARD, fg=INK, relief="flat",
                         bd=0, insertbackground=INK, show=show or "")
        entry.pack(fill="both", expand=True, padx=s(10), pady=(s(8), s(5)))
        return box, entry

    def _bind_focus(self, entry, box):
        entry.bind("<FocusIn>", lambda _e: box.configure(
            highlightbackground=PRIMARY, highlightcolor=PRIMARY), add="+")
        entry.bind("<FocusOut>", lambda _e: box.configure(
            highlightbackground=BORDER, highlightcolor=PRIMARY), add="+")

    def _place_window(self):
        self.update_idletasks()
        width, height = self._target_size
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        px = self.app.winfo_rootx() + (self.app.winfo_width() - width) // 2
        py = self.app.winfo_rooty() + (self.app.winfo_height() - height) // 2
        px = max(wa_x + s(10), min(px, wa_x + wa_w - width - s(20)))
        py = max(wa_y + s(10), min(py, wa_y + wa_h - height - s(30)))
        self.geometry(f"{width}x{height}+{px}+{py}")

    def _populate_config(self):
        self.project_entry.delete(0, "end")
        self.project_entry.insert(0, self.manager.project_id)
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, self.manager.api_key)

    def _refresh(self, populate_config=False):
        state = self.manager.state()
        self.status_title.configure(text=state["label"])
        self.status_detail.configure(text=state["detail"])
        self.status_dot.itemconfigure(self.status_dot_item, fill=state["color"])

        configured = self.manager.configured
        if not configured:
            self._editing_config = True
        if populate_config:
            self._populate_config()
            if not self._auth_fields_ready:
                self.email_entry.delete(0, "end")
                self.email_entry.insert(0, self.manager.email)
                self._auth_fields_ready = True

        if configured and not self._editing_config:
            self.config_form.pack_forget()
            self.config_summary.pack(fill="x", pady=(s(8), 0))
            self.project_text.configure(
                text=f"Projek: {self.manager.project_id}")
            self.cancel_edit_btn.pack_forget()
        else:
            self.config_summary.pack_forget()
            self.config_form.pack(fill="x", pady=(s(8), 0))
            if configured:
                self.cancel_edit_btn.pack(side="left", padx=(s(8), 0))
            else:
                self.cancel_edit_btn.pack_forget()

        if configured and not self._editing_config:
            self.account_section.grid()
            if self.manager.signed_in:
                self.auth_box.pack_forget()
                self.account_box.pack(fill="x", pady=(s(8), 0))
                self.account_email.configure(text=self.manager.email or "Akaun Firebase")
                result = self.manager.last_result
                if result:
                    pushed = int(result.get("pushed", 0))
                    pulled = int(result.get("inserted", 0)) + int(
                        result.get("updated", 0)
                    )
                    self.account_sync.configure(
                        text=f"Sync terakhir: {pushed} dihantar · {pulled} diterima."
                    )
                elif self.manager.last_sync:
                    self.account_sync.configure(
                        text=f"Terakhir disegerakkan: {fmt_datetime(self.manager.last_sync)}"
                    )
                else:
                    self.account_sync.configure(text="Belum disegerakkan.")
            else:
                self.account_box.pack_forget()
                self.auth_box.pack(fill="x", pady=(s(8), 0))
                if not self.email_entry.get() and self.manager.email:
                    self.email_entry.insert(0, self.manager.email)
        else:
            self.account_section.grid_remove()

        if self._message:
            self.message_label.configure(
                text=self._message,
                fg=DANGER if self._message_error else SUCCESS,
            )
        elif self.manager.auth_error:
            self.message_label.configure(text=self.manager.auth_error, fg=DANGER)
        elif self.manager.last_error:
            self.message_label.configure(text=self.manager.last_error, fg=DANGER)
        else:
            self.message_label.configure(text="")

        self.email_entry.configure(
            state="disabled" if self.manager.auth_running else "normal")
        self.password_entry.configure(
            state="disabled" if self.manager.auth_running else "normal")

        self.update_idletasks()

    def refresh_status(self):
        self._refresh()

    def _start_edit_config(self):
        self._editing_config = True
        self._message = ""
        self._populate_config()
        self._refresh()
        self.after(30, self.project_entry.focus_set)

    def _cancel_edit_config(self):
        if not self.manager.configured:
            return
        self._editing_config = False
        self._message = ""
        self._refresh()

    def _save_config(self):
        ok, message = self.manager.save_config(
            self.project_entry.get(), self.key_entry.get()
        )
        self._message = message
        self._message_error = not ok
        if ok:
            self._editing_config = False
            self._message = "Konfigurasi disimpan. Seterusnya, log masuk atau daftar akaun."
        self._refresh()

    def _do_auth(self, create):
        if self.manager.auth_running:
            return
        self._message = ""
        self._message_error = False
        self._refresh()
        self.manager.sign_in_async(
            self.email_entry.get(), self.password_entry.get(),
            create=create, on_done=self._auth_done,
        )

    def _auth_done(self, error):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        self.password_entry.delete(0, "end")
        if error:
            self._message = error
            self._message_error = True
        else:
            self._message = "Log masuk berjaya."
            self._message_error = False
        self._editing_config = False
        self._auth_fields_ready = True
        self._refresh()

    def _sync_now(self):
        if self.manager.syncing:
            return
        self._message = ""
        self._message_error = False
        self._refresh()
        self.manager.sync_async(manual=True, on_done=self._sync_done)

    def _sync_done(self, error):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if error:
            self._message = error
            self._message_error = True
        else:
            self._message = "Sync selesai."
            self._message_error = False
        self._refresh()

    def _logout(self):
        if self.manager.syncing:
            self._message = "Sila tunggu sync selesai sebelum log keluar."
            self._message_error = True
            self._refresh()
            return
        if not messagebox.askyesno(
            "Log keluar",
            "Log keluar daripada akaun Firebase? Data setempat akan kekal.",
            parent=self,
        ):
            return
        self.manager.sign_out()
        self._message = "Anda telah log keluar."
        self._message_error = False
        self._refresh()

    def _open_console(self):
        webbrowser.open("https://console.firebase.google.com/")

    def _open_guide(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass

        def restore():
            try:
                self.grab_set()
            except tk.TclError:
                pass

        FirebaseGuideDialog(self, on_close=restore)

    def _close(self):
        self.destroy()

    def destroy(self):
        if getattr(self.app, "_cloud_dialog", None) is self:
            self.app._cloud_dialog = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        super().destroy()


# ---------------------------------------------------------------- app ------
class App(tk.Tk):
    def __init__(self, db: Database, data_dir: Path):
        setup_dpi_awareness()
        super().__init__()
        global SCALE
        dpi = self.winfo_fpixels("1i")
        # Scale with Windows DPI, but never beyond what the usable desktop can
        # fit: the minimum window must remain reachable on small laptops.
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        scale = min(
            dpi / 96.0,
            (wa_w - 40) / 1150.0,
            (wa_h - 80) / 650.0,
        )
        SCALE = max(0.8, scale)
        try:
            self.tk.call("tk", "scaling", dpi / 72.0)
        except tk.TclError:
            pass
        init_fonts(self)
        setup_ttk(self)

        self.db = db
        self.data_dir = data_dir
        self.loans = []
        self.status_filter = None
        self._dialog = None
        self._cloud_dialog = None
        self._closing = False
        self._last_cloud_error = ""
        self._search_after = None
        self._toast_widget = None
        self._nav_items: dict = {}
        self._icon_image = None
        self.search_var = tk.StringVar()
        self.cloud = CloudManager(self, db)

        self.withdraw()
        self.title(WINDOW_TITLE)
        self.configure(bg=BG)
        self._set_window_icon()
        self._build_ui()
        self._bind_shortcuts()

        default_w = s(1280)
        default_h = s(780)
        wa_x, wa_y, wa_w, wa_h = work_area(self)
        width = min(default_w, wa_w - s(40))
        height = min(default_h, wa_h - s(50))
        x = wa_x + (wa_w - width) // 2
        y = wa_y + max(0, (wa_h - height) // 2 - s(10))
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(s(1150), s(650))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._reload_loans()
        self.deiconify()
        self.lift()
        self.cloud.start_auto_sync()

    def _set_window_icon(self):
        try:
            icon = resource_path("assets/icon.png")
            if icon.exists():
                self._icon_image = tk.PhotoImage(file=str(icon))
                self.iconphoto(True, self._icon_image)
        except Exception:
            self._icon_image = None

    # -- UI ---------------------------------------------------------------
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()

        main = tk.Frame(self, bg=BG)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        pad = s(24)
        header = tk.Frame(main, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=pad, pady=(s(18), 0))
        header.grid_columnconfigure(0, weight=1)

        title_box = tk.Frame(header, bg=BG)
        title_box.grid(row=0, column=0, sticky="w")
        tk.Label(title_box, text=today_label().upper(), font=F["micro"],
                 bg=BG, fg=MUTED_LIGHT, anchor="w").pack(anchor="w")
        self.page_title = tk.Label(title_box, text="Semua Pinjaman", font=F["h1"],
                                   bg=BG, fg=INK, anchor="w")
        self.page_title.pack(anchor="w", pady=(s(2), 0))
        self.page_subtitle = tk.Label(title_box, text="", font=F["label"],
                                      bg=BG, fg=MUTED, anchor="w")
        self.page_subtitle.pack(anchor="w", pady=(s(2), 0))

        actions = tk.Frame(header, bg=BG)
        actions.grid(row=0, column=1, sticky="e")
        RoundButton(actions, "Eksport CSV", command=self.export_csv, kind="ghost",
                    bg=BG, height=38).pack(side="left", padx=(0, s(10)))
        RoundButton(actions, "+  Tambah Pinjaman", command=self.add_loan,
                    kind="primary", bg=BG, height=38, padx=18).pack(side="left")

        stats = tk.Frame(main, bg=BG)
        stats.grid(row=1, column=0, sticky="ew", padx=pad, pady=(s(16), 0))
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1, uniform="stats")
        self.stat_total = StatCard(stats, "Jumlah Rekod", "doc", "#2563EB", "#EAF1FF")
        self.stat_process = StatCard(stats, "Dalam Proses", "clock", "#D97706", "#FFF4DE")
        self.stat_approved = StatCard(stats, "Diluluskan", "check", "#059669", "#E7F8F0")
        self.stat_rejected = StatCard(stats, "Ditolak", "x", "#DC2626", "#FDECEC")
        for idx, card in enumerate((self.stat_total, self.stat_process,
                                    self.stat_approved, self.stat_rejected)):
            card.grid(row=0, column=idx, sticky="nsew",
                      padx=(0, s(12)) if idx < 3 else 0)

        card = tk.Frame(main, bg=CARD, highlightthickness=s(1),
                        highlightbackground=BORDER)
        card.grid(row=2, column=0, sticky="nsew", padx=pad,
                  pady=(s(16), s(22)))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(4, weight=1)

        top = tk.Frame(card, bg=CARD)
        top.grid(row=0, column=0, sticky="ew", padx=s(18), pady=(s(13), s(11)))
        top.grid_columnconfigure(2, weight=1)
        tk.Label(top, text="Senarai Pinjaman", font=F["card_title"], bg=CARD,
                 fg=INK, anchor="w").grid(row=0, column=0, sticky="w")
        self.count_badge = tk.Label(top, text="0", font=F["tiny"],
                                    bg=PRIMARY_SOFT, fg=PRIMARY, padx=s(7),
                                    pady=s(1))
        self.count_badge.grid(row=0, column=1, sticky="w", padx=(s(8), 0))
        tk.Label(top, text="Klik dua kali untuk butiran", font=F["tiny"],
                 bg=CARD, fg=MUTED_LIGHT, anchor="w").grid(
            row=0, column=2, sticky="w", padx=(s(12), 0))
        self.search_box = SearchBox(top, self.search_var,
                                    "Cari nama, IC, kereta atau bank…",
                                    self._on_search_change, width=290)
        self.search_box.grid(row=0, column=3, sticky="e")

        tk.Frame(card, bg=BORDER, height=s(1)).grid(row=1, column=0, sticky="ew")

        head = tk.Frame(card, bg="#FAFBFE")
        head.grid(row=2, column=0, sticky="ew")
        inner_head = tk.Frame(head, bg="#FAFBFE")
        inner_head.pack(fill="x", padx=s(18), pady=s(9))
        for col, weight, min_w in TABLE_COLS:
            inner_head.grid_columnconfigure(col, weight=weight, uniform="table",
                                            minsize=s(min_w))
        inner_head.grid_columnconfigure(ACTION_COL, weight=0, minsize=s(ACTION_WIDTH))
        heads = ["PEMOHON", "NO. IC", "BANK", "JUMLAH", "TARIKH", "STATUS"]
        for col, text in enumerate(heads):
            anchor = "e" if col == 3 else "w"
            kwargs = {"padx": (0, s(13))} if col == 3 else {}
            tk.Label(inner_head, text=text, font=F["thead"], bg="#FAFBFE",
                     fg="#7B8AA1", anchor=anchor).grid(row=0, column=col,
                                                      sticky="nsew", **kwargs)
        tk.Frame(card, bg=BORDER, height=s(1)).grid(row=3, column=0, sticky="ew")

        self.table_scroll = ScrollFrame(card, bg=CARD)
        self.table_scroll.grid(row=4, column=0, sticky="nsew")
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=SIDEBAR, width=s(232))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(3, weight=1)

        brand = tk.Frame(sidebar, bg=SIDEBAR)
        brand.grid(row=0, column=0, sticky="ew", padx=s(18), pady=(s(22), s(18)))
        logo = tk.Canvas(brand, width=s(38), height=s(38), bg=SIDEBAR,
                         highlightthickness=0, bd=0)
        logo.pack(side="left")
        rounded_rect(logo, 0, 0, s(37), s(37), s(11), fill=PRIMARY, outline=PRIMARY)
        logo.create_text(s(19), s(19), text="LT", font=F["logo"], fill="#FFFFFF")
        brand_text = tk.Frame(brand, bg=SIDEBAR)
        brand_text.pack(side="left", padx=(s(11), 0))
        tk.Label(brand_text, text="LoanTrack", font=F["brand"], bg=SIDEBAR,
                 fg="#FFFFFF", anchor="w").pack(anchor="w")
        tk.Label(brand_text, text="Pemantau Pinjaman", font=F["micro"], bg=SIDEBAR,
                 fg=SIDEBAR_TEXT, anchor="w").pack(anchor="w", pady=(s(1), 0))

        nav = tk.Frame(sidebar, bg=SIDEBAR)
        nav.grid(row=1, column=0, sticky="ew")
        self._nav_items[None] = NavItem(
            nav, "Semua Pinjaman", lambda: self.set_filter(None), count=0,
            dot=ACCENT_NAV, active=True,
        )
        self._nav_items[None].pack(fill="x")

        section = tk.Frame(sidebar, bg=SIDEBAR)
        section.grid(row=2, column=0, sticky="ew", pady=(s(16), s(6)))
        tk.Label(section, text="STATUS", font=F["micro"], bg=SIDEBAR,
                 fg="#5A6B85", anchor="w").pack(anchor="w", padx=s(22))
        status_nav = tk.Frame(sidebar, bg=SIDEBAR)
        status_nav.grid(row=3, column=0, sticky="new")
        for status in STATUSES:
            item = NavItem(status_nav, status,
                           lambda st=status: self.set_filter(st),
                           count=0, dot=STATUS_DOTS.get(status))
            item.pack(fill="x")
            self._nav_items[status] = item

        tools = tk.Frame(sidebar, bg=SIDEBAR)
        tools.grid(row=4, column=0, sticky="ew", pady=(s(12), 0))
        self.cloud_row = CloudStatusRow(tools, self.open_cloud_dialog)
        self.cloud_row.pack(fill="x", pady=(0, s(10)))
        self.cloud_row.set_state(self.cloud.state())
        tk.Frame(tools, bg=SIDEBAR_LINE, height=s(1)).pack(fill="x",
                                                           padx=s(18), pady=(0, s(12)))
        export = NavItem(tools, "Eksport CSV", self.export_csv, show_dot=False,
                         font=F["small"])
        export.count.pack_forget()
        export.pack(fill="x")
        folder = NavItem(tools, "Buka Folder Data", self.open_data_folder,
                         show_dot=False, font=F["small"])
        folder.count.pack_forget()
        folder.pack(fill="x")

        footer = tk.Frame(sidebar, bg=SIDEBAR)
        footer.grid(row=5, column=0, sticky="ew", padx=s(22), pady=(s(18), s(18)))
        tk.Label(footer, text="Data setempat · SQLite", font=F["micro"], bg=SIDEBAR,
                 fg="#5A6B85", anchor="w").pack(anchor="w")
        tk.Label(footer, text=f"Versi {APP_VERSION}", font=F["micro"], bg=SIDEBAR,
                 fg="#44546B", anchor="w").pack(anchor="w", pady=(s(2), 0))

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda _e: self.add_loan())
        self.bind("<Control-f>", lambda _e: self.search_box.focus())
        self.bind("<Control-e>", lambda _e: self.export_csv())

    # -- data / rendering --------------------------------------------------
    def _reload_loans(self, reset_scroll=False, toast_msg=None):
        position = None
        if not reset_scroll:
            position = self.table_scroll.canvas.yview()[0]
        self.loans = self.db.list_loans()
        self._update_nav_counts()
        self._update_stats()
        self._render_table(reset_scroll=reset_scroll, position=position)
        if toast_msg:
            self.toast(toast_msg)

    def _filtered_loans(self):
        # Local filtering is intentionally done in Python: the dataset is small
        # and this keeps search instant while typing.
        query = self.search_var.get().strip().lower()
        query_digits = re.sub(r"\D", "", query)
        rows = []
        for loan in self.loans:
            if self.status_filter and loan["status"] != self.status_filter:
                continue
            if query:
                haystack = " ".join([
                    loan["name"] or "", loan["car"] or "", loan["bank"] or "",
                    loan["notes"] or "", loan["status"] or "",
                ]).lower()
                digits_match = (len(query_digits) >= 4
                                and query_digits in (loan["ic"] or ""))
                if query not in haystack and not digits_match:
                    continue
            rows.append(loan)
        return rows

    def _update_nav_counts(self):
        counts = Counter(loan["status"] for loan in self.loans)
        if None in self._nav_items:
            self._nav_items[None].set_count(len(self.loans))
        for status in STATUSES:
            item = self._nav_items.get(status)
            if item:
                item.set_count(counts.get(status, 0))

    def _update_stats(self):
        total = len(self.loans)
        processing = sum(1 for l in self.loans if l["status"] in PROCESS_STATUSES)
        approved = sum(1 for l in self.loans if l["status"] in APPROVED_STATUSES)
        rejected = sum(1 for l in self.loans if l["status"] in REJECTED_STATUSES)
        total_value = sum(float(l["amount"] or 0) for l in self.loans)
        approved_value = sum(float(l["amount"] or 0) for l in self.loans
                             if l["status"] in APPROVED_STATUSES)
        pct = (rejected / total * 100) if total else 0

        self.stat_total.update_values(
            f"{total:,}",
            f"{fmt_compact(total_value)} jumlah nilai" if total else "Belum ada rekod",
        )
        self.stat_process.update_values(
            f"{processing:,}",
            "Menunggu keputusan" if processing else "Tiada tindakan tertunggak",
        )
        self.stat_approved.update_values(
            f"{approved:,}",
            f"{fmt_compact(approved_value)} nilai diluluskan" if approved
            else "Belum ada kelulusan",
        )
        self.stat_rejected.update_values(
            f"{rejected:,}",
            f"{pct:.0f}% kadar penolakan" if total else "—",
        )

    def _render_table(self, reset_scroll=False, position=None):
        rows = self._filtered_loans()
        count = len(rows)

        title = self.status_filter or "Semua Pinjaman"
        self.page_title.configure(text=title)
        if count:
            total_value = sum(float(l["amount"] or 0) for l in rows)
            self.page_subtitle.configure(
                text=f"{count} rekod · {fmt_compact(total_value)} jumlah nilai")
        else:
            self.page_subtitle.configure(text="Tiada rekod untuk dipaparkan")
        self.count_badge.configure(text=str(count))

        self.table_scroll.clear()
        if not rows:
            self._render_empty_state()
        else:
            for loan in rows:
                row = LoanRow(self.table_scroll.inner, loan,
                              on_open=lambda lid=loan["id"]: self.open_dialog(lid))
                row.pack(fill="x")
                tk.Frame(self.table_scroll.inner, bg=BORDER,
                         height=s(1)).pack(fill="x")

        if reset_scroll:
            self.table_scroll.scroll_to_top()
        elif position is not None:
            self.update_idletasks()
            self.table_scroll.canvas.yview_moveto(position)
        self.update_idletasks()
        self.table_scroll._sync_bar()

    def _render_empty_state(self):
        searching = bool(self.loans) and (
            bool(self.search_var.get().strip()) or bool(self.status_filter)
        )
        wrap = tk.Frame(self.table_scroll.inner, bg=CARD)
        wrap.pack(fill="both", expand=True, pady=(s(42), s(36)))
        icon = tk.Canvas(wrap, width=s(60), height=s(60), bg=CARD,
                         highlightthickness=0, bd=0)
        icon.pack()
        draw_empty_icon(icon, "search" if searching else "doc")
        if searching:
            heading = "Tiada rekod ditemui"
            body = "Cuba tukar kata kunci carian atau tapis status yang lain."
        else:
            heading = "Belum ada rekod pinjaman"
            body = "Tambah rekod pertama anda untuk mula memantau status pinjaman."
        tk.Label(wrap, text=heading, font=F["card_title"], bg=CARD, fg=INK).pack(
            pady=(s(12), 0))
        tk.Label(wrap, text=body, font=F["label"], bg=CARD, fg=MUTED,
                 wraplength=s(380), justify="center").pack(pady=(s(4), s(14)))
        if searching:
            RoundButton(wrap, "Set Semula Tapisan", command=self.reset_filters,
                        kind="soft", bg=CARD, height=36).pack()
        else:
            RoundButton(wrap, "+  Tambah Pinjaman", command=self.add_loan,
                        kind="primary", bg=CARD, height=36).pack()

    def _on_search_change(self):
        if self._search_after is not None:
            try:
                self.after_cancel(self._search_after)
            except tk.TclError:
                pass
        self._search_after = self.after(120, self._apply_search)

    def _apply_search(self):
        self._search_after = None
        self._render_table(reset_scroll=True)

    def set_filter(self, status):
        if self.status_filter == status:
            return
        self.status_filter = status
        for key, item in self._nav_items.items():
            item.set_active(key == status)
        self._render_table(reset_scroll=True)

    def reset_filters(self):
        self.status_filter = None
        for key, item in self._nav_items.items():
            item.set_active(key is None)
        self.search_var.set("")
        self._render_table(reset_scroll=True)

    # -- dialog / actions --------------------------------------------------
    def add_loan(self):
        self.open_dialog(None)

    def open_dialog(self, loan_id):
        if self._dialog is not None:
            try:
                if self._dialog.winfo_exists():
                    self._dialog.lift()
                    self._dialog.focus_force()
                    return
            except tk.TclError:
                pass
            self._dialog = None
        loan = self.db.get_loan(loan_id) if loan_id is not None else None
        if loan_id is not None and loan is None:
            messagebox.showerror("Rekod tidak ditemui", "Rekod ini telah dipadam.",
                                 parent=self)
            self._reload_loans()
            return
        self._dialog = LoanDialog(self, loan)

    def after_dialog(self, action, loan_id=None):
        if action == "created":
            self.status_filter = None
            for key, item in self._nav_items.items():
                item.set_active(key is None)
            if self.search_var.get():
                self.search_var.set("")
            self._reload_loans(reset_scroll=True)
        else:
            self._reload_loans()
        self.cloud.schedule_sync(900)

    # -- cloud UI ----------------------------------------------------------
    def open_cloud_dialog(self):
        if self._cloud_dialog is not None:
            try:
                if self._cloud_dialog.winfo_exists():
                    self._cloud_dialog.lift()
                    self._cloud_dialog.focus_force()
                    return
            except tk.TclError:
                pass
            self._cloud_dialog = None
        self._cloud_dialog = CloudDialog(self)

    def on_cloud_change(self):
        if self._closing:
            return
        try:
            self.cloud_row.set_state(self.cloud.state())
        except tk.TclError:
            pass
        if self._cloud_dialog is not None:
            try:
                if self._cloud_dialog.winfo_exists():
                    self._cloud_dialog.refresh_status()
                else:
                    self._cloud_dialog = None
            except tk.TclError:
                self._cloud_dialog = None
        error = self.cloud.last_error
        if error and error != self._last_cloud_error:
            try:
                self.toast("Sync awan gagal. Buka Awan & Sync untuk butiran.")
            except tk.TclError:
                pass
        self._last_cloud_error = error

    def on_cloud_sync_finished(self, result, manual):
        if self._closing:
            return
        changed = (int(result.get("inserted", 0))
                   + int(result.get("updated", 0))
                   + int(result.get("removed", 0)))
        if changed:
            self._reload_loans()
            try:
                self.toast(f"{changed} rekod dikemas kini daripada awan.")
            except tk.TclError:
                pass
        elif manual:
            try:
                self.toast("Sync selesai. Data sudah selaras.")
            except tk.TclError:
                pass

    def export_csv(self):
        rows = self._filtered_loans()
        if not rows:
            messagebox.showinfo("Tiada data", "Tiada rekod untuk dieksport.",
                                parent=self)
            return
        default_name = f"pinjaman_{date.today().isoformat()}.csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Eksport senarai pinjaman",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("Fail CSV", "*.csv"), ("Semua fail", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "Nama", "No. IC", "Jenis Kereta", "Bank",
                    "Jumlah Pinjaman (RM)", "Tarikh Mohon", "Status",
                    "Catatan", "Dikemas Kini",
                ])
                for loan in rows:
                    writer.writerow([
                        loan["name"],
                        format_ic(loan["ic"]),
                        loan["car"],
                        loan["bank"],
                        "" if loan["amount"] is None else f"{float(loan['amount']):.2f}",
                        fmt_date(loan["applied_date"], short=False),
                        loan["status"],
                        loan["notes"] or "",
                        fmt_datetime(loan["updated_at"]),
                    ])
        except OSError as exc:
            messagebox.showerror("Eksport gagal", f"Fail tidak dapat disimpan.\n\n{exc}",
                                 parent=self)
            return
        self.toast(f"{len(rows)} rekod dieksport ke CSV.")

    def open_data_folder(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(self.data_dir))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{self.data_dir}"')
            else:
                os.system(f'xdg-open "{self.data_dir}"')
        except Exception as exc:
            messagebox.showerror("Folder data", f"Folder tidak dapat dibuka.\n\n{exc}",
                                 parent=self)

    # -- misc --------------------------------------------------------------
    def _on_mousewheel(self, event):
        if self._dialog is not None:
            return
        if self.table_scroll.pointer_inside():
            self.table_scroll.wheel(event)

    def toast(self, message: str):
        if self._toast_widget is not None:
            try:
                self._toast_widget.destroy()
            except tk.TclError:
                pass
            self._toast_widget = None
        font = F["toast"]
        height = s(40)
        width = font.measure(message) + s(56)
        canvas = tk.Canvas(self, width=width, height=height, bg=BG,
                           highlightthickness=0, bd=0)
        rounded_rect(canvas, 0, 0, width - 1, height - 1, s(11),
                     fill="#0F1B2D", outline="#0F1B2D")
        cy = height / 2
        canvas.create_oval(s(13), cy - s(8), s(29), cy + s(8),
                           fill="#10B981", outline="")
        canvas.create_line(s(17), cy, s(20), cy + s(3), s(25), cy - s(3),
                           fill="#FFFFFF", width=max(1, s(2)),
                           capstyle="round", joinstyle="round")
        canvas.create_text(s(37), cy + 0.5, text=message, anchor="w",
                           font=font, fill="#F8FAFC")
        canvas.place(relx=1.0, rely=1.0, x=-s(28), y=-s(24), anchor="se")
        canvas.tk.call("raise", canvas._w)
        self._toast_widget = canvas
        self.after(3000, lambda c=canvas: self._hide_toast(c))

    def _hide_toast(self, canvas):
        if self._toast_widget is canvas:
            try:
                canvas.destroy()
            except tk.TclError:
                pass
            self._toast_widget = None

    def _on_close(self):
        self._closing = True
        try:
            self.cloud.dispose()
        except Exception:
            pass
        self.db.close()
        self.destroy()


# --------------------------------------------------------------- startup ----
def resolve_data_dir() -> Path:
    override = os.environ.get("LOANTRACK_DATA_DIR")
    if override:
        path = Path(override).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    preferred = app_dir() / "data"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return preferred
    except OSError:
        fallback = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LoanTrack"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def main() -> None:
    setup_dpi_awareness()
    data_dir = resolve_data_dir()
    db_path = data_dir / "loantrack.db"
    make_backup(db_path, data_dir / "backups")
    try:
        db = Database(db_path)
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "LoanTrack tidak dapat dibuka",
            f"Pangkalan data tidak dapat dibuka.\n\n{exc}\n\nLokasi: {db_path}",
            parent=root,
        )
        root.destroy()
        return
    app = App(db, data_dir)
    app.mainloop()


if __name__ == "__main__":
    main()

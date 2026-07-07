import sys, os, math, random, threading, time
from pathlib import Path

if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QStackedWidget, QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem,
    QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSize,
    QRect, QRectF, pyqtSignal, QThread, QObject, QSequentialAnimationGroup,
    QParallelAnimationGroup
)
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient,
    QFont, QPainterPath, QCursor, QPalette, QMouseEvent
)

try:
    sys.path.insert(0, str(Path(__file__).parent))
    from chat import IDManager, NetworkInfo, CryptoManager, P2PConnection, PeerDiscovery, CONFIG
    BACKEND_OK = True
except ImportError:
    BACKEND_OK = False
    CONFIG = {'TCP_PORT': 6006, 'UDP_PORT': 5005, 'SEARCH_TIMEOUT': 10,
              'BUFFER_SIZE': 4096, 'TCP_BUFFER_SIZE': 65536}
    class IDManager:
        @staticmethod
        def load_or_create_id(f='my_id.txt'): return 'DEMO1234'
    class NetworkInfo:
        @staticmethod
        def get_local_ip(): return '127.0.0.1'
        @staticmethod
        def get_public_ip(): return None
    class CryptoManager: pass
    class P2PConnection:
        peer_id = None; peer_ip = None; connected = False
        def connect_to_peer(self, ip): return False
        def exchange_public_keys(self): return False
        def send_message(self, m): return False
        def receive_message(self): return None
        def close(self): pass
    class PeerDiscovery:
        def __init__(self, *a): pass
        def setup_socket(self): pass
        def search_peer(self, *a): return None

T = {
    'BG_DEEP':    '#0D1117',
    'BG_SURFACE': '#161B22',
    'BG_CARD':    '#21262D',
    'BG_HOVER':   '#30363D',
    'ACCENT':     '#2EA043',
    'ACCENT_DIM': '#238636',
    'WARM':       '#D29922',
    'TEXT':       '#8B949E',
    'TEXT_BRIGHT':'#C9D1D9',
    'MUTED':      '#484F58',
    'DANGER':     '#F85149',
    'BORDER':     '#30363D',
    'MSG_OUT':    '#1C2128',
    'MSG_IN':     '#161B22',
}

def qc(h): return QColor(h)
def font(sz, w=QFont.Normal): return QFont('Segoe UI', sz, w)
def mono(sz): return QFont('Consolas', sz)


class RoundedFrame(QFrame):
    def __init__(self, radius=6, bg=T['BG_CARD'], border=T['BORDER'], parent=None):
        super().__init__(parent)
        self._r = radius; self._bg = qc(bg); self._b = qc(border)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        rc = QRectF(self.rect().adjusted(1,1,-1,-1))
        path = QPainterPath(); path.addRoundedRect(rc, self._r, self._r)
        p.fillPath(path, QBrush(self._bg))
        p.setPen(QPen(self._b, 1)); p.drawPath(path)


class _RippleState:
    __slots__ = ('x','y','r','max_r','alpha')
    def __init__(self, x, y, max_r):
        self.x = x; self.y = y; self.r = 0.0; self.max_r = max_r; self.alpha = 0.7


class GlowButton(QPushButton):
    def __init__(self, text='', accent=T['ACCENT'], parent=None):
        super().__init__(text, parent)
        self._acc = qc(accent); self._alpha = 0.0
        self._hover = False; self._press = False
        self._ripples: list = []
        t = QTimer(self); t.timeout.connect(self._tick); t.start(16)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(font(11, QFont.Bold)); self.setMinimumHeight(46)
        self.setStyleSheet("background: transparent; border: none;")

    def _tick(self):
        target = 0.75 if self._press else (0.5 if self._hover else 0.0)
        self._alpha += (target - self._alpha) * 0.15
        if abs(target - self._alpha) < 0.005: self._alpha = target
        for rp in self._ripples:
            rp.r = min(rp.r + 4.0, rp.max_r)
            rp.alpha = max(0.0, rp.alpha - 0.025)
        self._ripples = [rp for rp in self._ripples if rp.alpha > 0]
        self.update()

    def enterEvent(self, e): self._hover = True
    def leaveEvent(self, e): self._hover = False; self._press = False

    def mousePressEvent(self, e):
        self._press = True
        max_r = math.hypot(self.width(), self.height())
        rp = _RippleState(e.x(), e.y(), max_r)
        self._ripples.append(rp)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e): self._press = False; super().mouseReleaseEvent(e)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()); radius = 6
        path = QPainterPath(); path.addRoundedRect(r, radius, radius)
        base_alpha = 0.12 + self._alpha * 0.18
        bg = QColor(self._acc); bg.setAlphaF(base_alpha)
        p.fillPath(path, QBrush(bg))
        p.setClipPath(path)
        for rp in self._ripples:
            rc = QColor(self._acc); rc.setAlphaF(rp.alpha * 0.25)
            p.setBrush(QBrush(rc)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPoint(int(rp.x), int(rp.y)), int(rp.r), int(rp.r))
        p.setClipping(False)
        bc = QColor(self._acc); bc.setAlphaF(0.4 + self._alpha * 0.6)
        p.setPen(QPen(bc, 1.0)); p.drawPath(path)
        tc = QColor(self._acc); tc.setAlphaF(0.75 + self._alpha * 0.25)
        p.setPen(tc); p.setFont(self.font()); p.drawText(r, Qt.AlignCenter, self.text())


class GlowInput(QLineEdit):
    def __init__(self, placeholder='', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFont(font(11)); self.setMinimumHeight(40)
        self.setStyleSheet(
            f"QLineEdit {{"
            f"background:{T['BG_DEEP']};border:1px solid {T['BORDER']};"
            f"border-radius:6px;color:{T['TEXT_BRIGHT']};padding:7px 12px;"
            f"selection-background-color:{T['ACCENT_DIM']};}}"
            f"QLineEdit:focus{{border:1px solid {T['ACCENT']};"
            f"background:{T['BG_CARD']};outline:none;}}"
        )
        self._fx = None

    def focusInEvent(self, e):
        self.setStyleSheet(self.styleSheet()); super().focusInEvent(e)

    def focusOutEvent(self, e):
        self.setGraphicsEffect(None); super().focusOutEvent(e)

    def shake(self):
        orig = self.pos()
        offsets = [6, -6, 5, -5, 3, -3, 1, 0]
        self._shake_idx = 0
        self._shake_orig = orig
        def _step():
            if self._shake_idx >= len(offsets):
                self.move(self._shake_orig); return
            self.move(orig.x() + offsets[self._shake_idx], orig.y())
            self._shake_idx += 1
            QTimer.singleShot(30, _step)
        _step()


class PulseIndicator(QWidget):
    def __init__(self, color=T['ACCENT'], parent=None):
        super().__init__(parent)
        self._color = qc(color); self._phase = 0.0
        self.setFixedSize(10, 10)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(50)

    def _tick(self):
        self._phase = (self._phase + 0.08) % (2 * math.pi); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        alpha = 0.5 + 0.5 * math.sin(self._phase)
        c = QColor(self._color); c.setAlphaF(alpha)
        p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
        p.drawEllipse(1, 1, 8, 8)


class TypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0; self._visible = False
        self.setFixedHeight(20)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(400)

    def _tick(self):
        if self._visible:
            self._phase = (self._phase + 1) % 4; self.update()

    def set_visible(self, v):
        self._visible = v; self.setVisible(v)

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for i in range(3):
            c = QColor(T['ACCENT']); alpha = 0.8 if i == self._phase else 0.3
            c.setAlphaF(alpha); p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
            p.drawEllipse(8 + i * 14, 7, 7, 7)


class Particle:
    def __init__(self, w, h):
        self.reset(w, h)

    def reset(self, w, h):
        self.x = random.uniform(0, w); self.y = random.uniform(0, h)
        self.vx = random.uniform(-0.3, 0.3); self.vy = random.uniform(-0.5, -0.1)
        self.life = random.uniform(0.3, 1.0); self.decay = random.uniform(0.003, 0.007)
        self.size = random.uniform(1.5, 3.5)

    def update(self, w, h):
        self.x += self.vx; self.y += self.vy; self.life -= self.decay
        if self.life <= 0 or self.x < 0 or self.x > w or self.y < 0 or self.y > h:
            self.reset(w, h); self.life = random.uniform(0.1, 0.5)


class ParticleBackground(QWidget):
    def __init__(self, count=40, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._particles = []
        self._count = count
        t = QTimer(self); t.timeout.connect(self._tick); t.start(33)

    def _init_particles(self):
        w, h = max(self.width(), 1), max(self.height(), 1)
        self._particles = [Particle(w, h) for _ in range(self._count)]

    def _tick(self):
        if not self._particles and self.width() > 0: self._init_particles()
        w, h = self.width(), self.height()
        for p in self._particles: p.update(w, h)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for pt in self._particles:
            c = QColor(T['ACCENT']); c.setAlphaF(pt.life * 0.5)
            p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
            r = pt.size
            p.drawEllipse(int(pt.x - r), int(pt.y - r), int(r*2), int(r*2))


class SpinningLogo(QWidget):
    def __init__(self, size=28, parent=None):
        super().__init__(parent)
        self._size = size; self._angle = 0.0
        self.setFixedSize(size, size)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(33)

    def _tick(self): self._angle = (self._angle + 1.5) % 360; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        s = self._size; cx, cy = s//2, s//2
        p.translate(cx, cy); p.rotate(self._angle); p.translate(-cx, -cy)
        path = QPainterPath()
        path.moveTo(cx, 2)
        for i in range(1, 6):
            a = math.radians(i * 72 - 90)
            r = (s//2 - 2) if i % 2 == 0 else (s//4)
            path.lineTo(cx + r * math.cos(a), cy + r * math.sin(a))
        path.closeSubpath()
        grad = QLinearGradient(0, 0, s, s)
        grad.setColorAt(0, qc(T['ACCENT'])); grad.setColorAt(1, qc(T['ACCENT_DIM']))
        p.fillPath(path, QBrush(grad))
        p.setPen(Qt.NoPen)


class RadarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0; self._blips = []
        self.setMinimumSize(120, 120)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(33)

    def _tick(self):
        self._angle = (self._angle + 1.5) % 360
        if random.random() < 0.02:
            a = math.radians(random.uniform(0, 360))
            r = random.uniform(0.2, 0.9)
            self._blips.append([a, r, 1.0])
        self._blips = [[a, r, l-0.01] for a, r, l in self._blips if l > 0]
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w//2, h//2; rad = min(cx, cy) - 4
        p.setPen(QPen(qc(T['MUTED']), 1))
        p.setBrush(Qt.NoBrush)
        for i in range(1, 4):
            r = rad * i // 3
            p.drawEllipse(cx-r, cy-r, r*2, r*2)
        for deg in range(0, 360, 45):
            a = math.radians(deg)
            p.drawLine(cx, cy, int(cx+rad*math.cos(a)), int(cy+rad*math.sin(a)))
        sweep_end = QColor(T['ACCENT']); sweep_end.setAlpha(0)
        sweep_start = QColor(T['ACCENT']); sweep_start.setAlpha(80)
        from PyQt5.QtGui import QConicalGradient
        cg = QConicalGradient(cx, cy, -self._angle)
        cg.setColorAt(0, sweep_start); cg.setColorAt(0.25, sweep_end); cg.setColorAt(1, sweep_end)
        p.setBrush(QBrush(cg)); p.setPen(Qt.NoPen)
        p.drawEllipse(cx-rad, cy-rad, rad*2, rad*2)
        line_c = QColor(T['ACCENT']); line_c.setAlpha(180)
        p.setPen(QPen(line_c, 1.5))
        a = math.radians(self._angle)
        p.drawLine(cx, cy, int(cx+rad*math.cos(a)), int(cy+rad*math.sin(a)))
        for ba, br, bl in self._blips:
            bx = cx + int(rad * br * math.cos(ba))
            by = cy + int(rad * br * math.sin(ba))
            bc = QColor(T['ACCENT']); bc.setAlphaF(bl * 0.9)
            p.setBrush(QBrush(bc)); p.setPen(Qt.NoPen)
            p.drawEllipse(bx-3, by-3, 6, 6)


class HexGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._phase = 0.0
        t = QTimer(self); t.timeout.connect(self._tick); t.start(60)

    def _tick(self): self._phase = (self._phase + 0.03) % (2*math.pi); self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        size = 22; w, h = self.width(), self.height()
        dx = size * 1.5; dy = size * math.sqrt(3)
        cols = int(w / dx) + 2; rows = int(h / dy) + 2
        for row in range(rows):
            for col in range(cols):
                cx = col * dx; cy = row * dy + (dx if col%2 else 0)
                d = math.sqrt((cx - w/2)**2 + (cy - h/2)**2)
                alpha = max(0, 0.06 - d/5000 + 0.02*math.sin(self._phase + d*0.01))
                c = QColor(T['ACCENT']); c.setAlphaF(alpha)
                p.setPen(QPen(c, 0.8)); p.setBrush(Qt.NoBrush)
                pts = []
                for i in range(6):
                    a = math.radians(60*i + 30)
                    pts.append(QPoint(int(cx + size*math.cos(a)), int(cy + size*math.sin(a))))
                from PyQt5.QtGui import QPolygon
                p.drawPolygon(QPolygon(pts))


class FlashOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._alpha = 0.0; self._active = False
        t = QTimer(self); t.timeout.connect(self._tick); t.start(16)

    def flash(self):
        self._alpha = 0.35; self._active = True; self.update()

    def _tick(self):
        if self._active:
            self._alpha = max(0.0, self._alpha - 0.025)
            if self._alpha <= 0: self._active = False
            self.update()

    def paintEvent(self, e):
        if self._alpha <= 0: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QColor(T['ACCENT']); c.setAlphaF(self._alpha)
        p.fillRect(self.rect(), c)


class ScanLineOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, e):
        p = QPainter(self)
        c = QColor(0, 0, 0); c.setAlphaF(0.04)
        p.setPen(QPen(c, 1))
        for y in range(0, self.height(), 3):
            p.drawLine(0, y, self.width(), y)


class GlitchLabel(QLabel):
    _GLITCH = '!@#$%^&*<>?/\\|~`'
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self._orig = text
        self._glitch_timer = QTimer(self)
        self._glitch_timer.timeout.connect(self._glitch_frame)
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._start_glitch)
        self._frame_timer.start(5000)

    def _start_glitch(self):
        self._glitch_frames = 0
        self._glitch_timer.start(45)

    def _glitch_frame(self):
        self._glitch_frames += 1
        if self._glitch_frames > 6:
            self._glitch_timer.stop()
            self.setText(self._orig)
            return
        s = list(self._orig)
        idx = random.randint(0, len(s)-1)
        s[idx] = random.choice(self._GLITCH)
        self.setText(''.join(s))


class _BurstParticle:
    __slots__ = ('x','y','vx','vy','life','color','size')
    def __init__(self, x, y):
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(1.5, 5.0)
        self.x = float(x); self.y = float(y)
        self.vx = speed * math.cos(angle); self.vy = speed * math.sin(angle)
        self.life = 1.0; self.color = random.choice([T['ACCENT'], T['TEXT_BRIGHT'], T['WARM']])
        self.size = random.uniform(2.0, 5.0)

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.vy += 0.12; self.life -= 0.04


class ParticleBurst(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._particles: list = []
        t = QTimer(self); t.timeout.connect(self._tick); t.start(16)

    def burst(self, gpos):
        lpos = self.mapFromGlobal(gpos)
        self._particles += [_BurstParticle(lpos.x(), lpos.y()) for _ in range(22)]

    def _tick(self):
        if self._particles:
            for p in self._particles: p.update()
            self._particles = [p for p in self._particles if p.life > 0]
            self.update()

    def paintEvent(self, e):
        if not self._particles: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for pt in self._particles:
            c = QColor(pt.color); c.setAlphaF(pt.life)
            p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
            r = pt.size * pt.life
            p.drawEllipse(int(pt.x-r), int(pt.y-r), int(r*2), int(r*2))


class ChatStatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet(f"background:{T['BG_DEEP']}; border-top:1px solid {T['BORDER']};")
        self._start_time = None
        self._tx_bytes = 0

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(16)

        self._lbl_uptime  = QLabel("uptime: --:--")
        self._lbl_tx      = QLabel("tx: 0 B")
        self._lbl_latency = QLabel("latency: -- ms")
        self._lbl_crypto  = QLabel("AES-256-GCM ✓")

        for lbl in (self._lbl_uptime, self._lbl_tx, self._lbl_latency):
            lbl.setFont(mono(8)); lbl.setStyleSheet(f"color:{T['MUTED']};background:transparent;")
        self._lbl_crypto.setFont(mono(8))
        self._lbl_crypto.setStyleSheet(f"color:{T['ACCENT']};background:transparent;")

        lay.addWidget(self._lbl_uptime)
        lay.addWidget(self._lbl_tx)
        lay.addWidget(self._lbl_latency)
        lay.addStretch()
        lay.addWidget(self._lbl_crypto)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_uptime)

    def start_session(self):
        self._start_time = time.time(); self._tx_bytes = 0
        self._lbl_latency.setText("latency: <10 ms")
        self._timer.start(1000)

    def add_tx(self, n_bytes):
        self._tx_bytes += n_bytes
        if self._tx_bytes < 1024:
            self._lbl_tx.setText(f"tx: {self._tx_bytes} B")
        else:
            self._lbl_tx.setText(f"tx: {self._tx_bytes//1024} KB")

    def _update_uptime(self):
        if self._start_time is None: return
        dt = int(time.time() - self._start_time)
        m, s = divmod(dt, 60); h, m = divmod(m, 60)
        if h:
            self._lbl_uptime.setText(f"uptime: {h}:{m:02d}:{s:02d}")
        else:
            self._lbl_uptime.setText(f"uptime: {m:02d}:{s:02d}")


class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self._drag_pos = None
        self.setStyleSheet(f"background: {T['BG_DEEP']};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 8, 0)
        lay.setSpacing(8)

        logo = SpinningLogo(size=22)
        title = GlitchLabel("QuoKat")
        title.setFont(font(13, QFont.Bold))
        title.setStyleSheet(f"color:{T['TEXT_BRIGHT']};background:transparent;")
        subtitle = QLabel("encrypted p2p")
        subtitle.setFont(font(9))
        subtitle.setStyleSheet(f"color:{T['MUTED']};background:transparent;")

        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addWidget(subtitle)
        lay.addStretch()

        for sym, tip, slot in [("−", "Свернуть", self._minimize), ("✕", "Закрыть", self._close)]:
            btn = QPushButton(sym)
            btn.setFixedSize(32, 32)
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            hover_c = T['DANGER'] if sym == "✕" else T['BG_HOVER']
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;border:none;color:{T['MUTED']};"
                f"border-radius:6px;font-size:14px;}}"
                f"QPushButton:hover{{background:{hover_c};color:{T['TEXT_BRIGHT']};}}"
            )
            btn.clicked.connect(slot)
            lay.addWidget(btn)

    def _minimize(self):
        w = self.window(); w.showMinimized()

    def _close(self):
        self.window().close()

    def set_status(self, msg, is_error=False):
        pass

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self.window().move(e.globalPos() - self._drag_pos)


class _GradientBubbleFrame(QFrame):
    def __init__(self, is_mine: bool, parent=None):
        super().__init__(parent)
        self._is_mine = is_mine
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;border:none;")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        path = QPainterPath(); path.addRoundedRect(r, 8, 8)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        if self._is_mine:
            grad.setColorAt(0, QColor('#1C2128')); grad.setColorAt(1, QColor('#161B22'))
        else:
            grad.setColorAt(0, QColor('#21262D')); grad.setColorAt(1, QColor('#1C2128'))
        p.fillPath(path, QBrush(grad))
        border = QColor(T['ACCENT_DIM'] if self._is_mine else T['BORDER'])
        border.setAlphaF(0.6)
        p.setPen(QPen(border, 1.0)); p.drawPath(path)


class MessageBubble(QWidget):
    def __init__(self, text: str, sender: str, is_mine: bool, parent=None):
        super().__init__(parent)
        self._text = text; self._is_mine = is_mine
        self._opacity = 0.0; self._y_off = 20

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 4, 12, 4)

        bubble = _GradientBubbleFrame(is_mine)
        b_lay = QVBoxLayout(bubble)
        b_lay.setContentsMargins(14, 10, 14, 10)
        b_lay.setSpacing(4)

        if not is_mine:
            name_lbl = QLabel(sender)
            name_lbl.setFont(font(9, QFont.Bold))
            name_lbl.setStyleSheet(f"color:{T['ACCENT']};background:transparent;border:none;")
            b_lay.addWidget(name_lbl)

        msg_lbl = QLabel(text)
        msg_lbl.setFont(font(11))
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color:{T['TEXT_BRIGHT']};background:transparent;border:none;")
        msg_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        b_lay.addWidget(msg_lbl)

        ts = QLabel(time.strftime("%H:%M"))
        ts.setFont(font(8))
        ts.setStyleSheet(f"color:{T['MUTED']};background:transparent;border:none;")
        ts.setAlignment(Qt.AlignRight)
        b_lay.addWidget(ts)

        if is_mine: lay.addStretch()
        lay.addWidget(bubble)
        if not is_mine: lay.addStretch()
        bubble.setMaximumWidth(420)

        self._fx = QGraphicsDropShadowEffect(self)
        self._fx.setOffset(0, 4); self._fx.setBlurRadius(12)
        c = QColor(T['ACCENT'] if is_mine else '#000000')
        c.setAlpha(60 if is_mine else 40)
        self._fx.setColor(c); bubble.setGraphicsEffect(self._fx)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_in)
        self._anim_timer.start(16)

    def _animate_in(self):
        self._opacity = min(1.0, self._opacity + 0.08)
        self._y_off = max(0, self._y_off - 1.5)
        if self._opacity >= 1.0 and self._y_off <= 0: self._anim_timer.stop()
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setOpacity(self._opacity)
        p.translate(0, self._y_off); super().paintEvent(e); p.end()


class ChatScreen(QWidget):
    sig_send = pyqtSignal(str)
    sig_exit = pyqtSignal()

    def __init__(self, my_id: str, parent=None):
        super().__init__(parent)
        self._my_id = my_id
        self._peer_id = ''
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet(
            f"QFrame{{background:{T['BG_CARD']};border-bottom:1px solid {T['BORDER']};}}"
            f"QPushButton{{background:transparent;border:1px solid {T['DANGER']};"
            f"border-radius:6px;color:{T['DANGER']};padding:4px 12px;}}"
            f"QPushButton:hover{{background:{T['DANGER']};color:white;}}"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 0, 16, 0)

        self._lbl_peer = QLabel("Подключение...")
        self._lbl_peer.setFont(font(11, QFont.Bold))
        self._lbl_peer.setStyleSheet(f"color:{T['TEXT_BRIGHT']};background:transparent;")

        self._pulse = PulseIndicator(T['ACCENT'])
        self._typing_ind = TypingIndicator()

        badge = QLabel("AES-256-GCM")
        badge.setFont(mono(8))
        badge.setStyleSheet(
            f"color:{T['ACCENT']};background:{T['BG_DEEP']};"
            f"border:1px solid {T['ACCENT_DIM']};border-radius:3px;padding:1px 5px;"
        )

        btn_exit = QPushButton("Отключиться")
        btn_exit.setFont(font(9)); btn_exit.setFixedHeight(30)
        btn_exit.clicked.connect(self.sig_exit)

        h_lay.addWidget(self._pulse)
        h_lay.addWidget(self._lbl_peer)
        h_lay.addWidget(self._typing_ind)
        h_lay.addStretch()
        h_lay.addWidget(badge)
        h_lay.addSpacing(8)
        h_lay.addWidget(btn_exit)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea{{background:{T['BG_SURFACE']};border:none;}}"
            f"QScrollBar:vertical{{background:{T['BG_DEEP']};width:6px;border-radius:3px;}}"
            f"QScrollBar::handle:vertical{{background:{T['BORDER']};border-radius:3px;min-height:30px;}}"
            f"QScrollBar::handle:vertical:hover{{background:{T['MUTED']};}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}"
        )

        self._msg_container = QWidget()
        self._msg_container.setStyleSheet(f"background:{T['BG_SURFACE']};")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(0, 8, 0, 8)
        self._msg_layout.setSpacing(2)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_container)

        self._hex_grid = HexGrid(self)
        self._hex_grid.lower()

        input_frame = QFrame()
        input_frame.setFixedHeight(68)
        input_frame.setStyleSheet(
            f"QFrame{{background:{T['BG_CARD']};border-top:1px solid {T['BORDER']};}}"
        )
        i_lay = QHBoxLayout(input_frame)
        i_lay.setContentsMargins(16, 12, 16, 12)
        i_lay.setSpacing(10)

        self._inp = GlowInput("Зашифрованное сообщение...")
        self._btn_send = GlowButton("Отправить ➤")
        self._btn_send.setFixedWidth(130)
        self._btn_send.clicked.connect(self._send)
        self._inp.returnPressed.connect(self._send)

        i_lay.addWidget(self._inp)
        i_lay.addWidget(self._btn_send)

        self._status_bar = ChatStatusBar()
        self._burst = ParticleBurst(self)

        root.addWidget(header)
        root.addWidget(self._scroll, 1)
        root.addWidget(input_frame)
        root.addWidget(self._status_bar)

        self._reveal_timer = QTimer(self)
        self._reveal_timer.timeout.connect(self._reveal_tick)
        self._reveal_text = ''
        self._reveal_idx = 0

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._hex_grid.setGeometry(0, 0, self.width(), self.height())
        self._burst.setGeometry(0, 0, self.width(), self.height())

    def _send(self):
        text = self._inp.text().strip()
        if not text:
            self._inp.shake(); return
        self._inp.clear()
        self.add_message(text, self._my_id, True)
        self._lbl_peer.setText(self._lbl_peer.text())
        gpos = self._btn_send.mapToGlobal(
            QPoint(self._btn_send.width()//2, self._btn_send.height()//2))
        self._burst.burst(gpos)
        self.sig_send.emit(text)
        self._status_bar.add_tx(len(text.encode('utf-8')))
        QTimer.singleShot(320, lambda: self._lbl_peer.setText(self._lbl_peer.text()))

    def add_message(self, text: str, sender: str, is_mine: bool):
        bub = MessageBubble(text, sender, is_mine, self._msg_container)
        self._msg_layout.insertWidget(self._msg_layout.count()-1, bub)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def add_system(self, text: str):
        lbl = QLabel()
        lbl.setFont(font(9)); lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color:{T['MUTED']};background:transparent;padding:4px;")
        self._msg_layout.insertWidget(self._msg_layout.count()-1, lbl)
        chars = list(text); idx = [0]
        def _tw():
            if idx[0] <= len(chars):
                lbl.setText(''.join(chars[:idx[0]])); idx[0] += 1
                QTimer.singleShot(18, _tw)
        _tw()
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar(); sb.setValue(sb.maximum())

    def set_peer(self, peer_id: str, peer_ip: str):
        self._peer_id = peer_id
        full = f"{peer_id}  •  {peer_ip}" if peer_ip else peer_id
        self._reveal_text = full; self._reveal_idx = 0
        self._lbl_peer.setText('')
        self._reveal_timer.start(55)

    def _reveal_tick(self):
        self._reveal_idx += 1
        self._lbl_peer.setText(self._reveal_text[:self._reveal_idx])
        if self._reveal_idx >= len(self._reveal_text):
            self._reveal_timer.stop()


class ConnWorker(QThread):
    sig_ok     = pyqtSignal(str, str)
    sig_fail   = pyqtSignal(str)
    sig_status = pyqtSignal(str)

    def __init__(self, mode: str, my_id: str, target_id='', peer_ip='', parent=None):
        super().__init__(parent)
        self._mode = mode
        self._my_id = my_id
        self._target_id = target_id
        self._peer_ip = peer_ip
        self._crypto = None
        self._conn = None
        self.connection = None

    def run(self):
        if not BACKEND_OK:
            self.sig_fail.emit("Бэкенд недоступен (chat.py не найден)")
            return
        try:
            self._crypto = CryptoManager()
            self._conn = P2PConnection(self._my_id, self._crypto)
            if self._mode in ('connect_id', 'connect_ip'):
                if self._mode == 'connect_id':
                    self.sig_status.emit("🔍 Поиск в локальной сети...")
                    disc = PeerDiscovery(self._my_id)
                    disc.setup_socket()
                    found_ip = disc.search_peer(self._target_id, timeout=CONFIG['SEARCH_TIMEOUT'])
                    if found_ip:
                        self._peer_ip = found_ip
                        self.sig_status.emit(f"✅ Найден! IP: {found_ip}")
                    elif not self._peer_ip:
                        self.sig_fail.emit("Пользователь не найден в локальной сети")
                        return
                self.sig_status.emit("🔗 Подключаюсь...")
                if not self._conn.connect_to_peer(self._peer_ip):
                    self.sig_fail.emit("Не удалось подключиться")
                    return
                self._conn.peer_id = self._target_id
            else:
                self.sig_status.emit(f"⏳ Ожидание на порту {CONFIG['TCP_PORT']}...")
                if not self._conn.accept_connection(timeout=60):
                    self.sig_fail.emit("Таймаут ожидания (60 сек)")
                    return
            self.sig_status.emit("🔑 Обмен ключами шифрования...")
            if not self._conn.exchange_public_keys():
                self.sig_fail.emit("Ошибка при обмене ключами")
                return
            self.connection = self._conn
            self.sig_ok.emit(self._conn.peer_id or '', self._conn.peer_ip or '')
        except Exception as e:
            self.sig_fail.emit(f"Ошибка: {e}")


class MessageReceiver(QThread):
    sig_message    = pyqtSignal(str)
    sig_disconnect = pyqtSignal()

    def __init__(self, connection, parent=None):
        super().__init__(parent)
        self._conn = connection
        self._running = True

    def stop(self): self._running = False

    def run(self):
        while self._running and self._conn.connected:
            msg = self._conn.receive_message()
            if msg:
                self.sig_message.emit(msg)
            else:
                if self._running and self._conn.connected:
                    self._conn.close()
                    self.sig_disconnect.emit()
                break
            time.sleep(0.05)


class QuoKatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(720, 540)
        self.resize(820, 600)
        self._my_id = IDManager.load_or_create_id()
        self._local_ip = NetworkInfo.get_local_ip()
        self._conn_worker = None
        self._msg_receiver = None
        self._active_conn = None
        self._last_peer_id = ''
        self._last_peer_ip = ''
        self._build_ui()
        self._center()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        root.setStyleSheet(
            f"QWidget#root{{background:{T['BG_DEEP']};border-radius:8px;"
            f"border:1px solid {T['BORDER']};}}"
        )
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._title_bar = TitleBar(self)
        outer.addWidget(self._title_bar)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack, 1)

        self._flash = FlashOverlay(self)
        self._scanlines = ScanLineOverlay(self)

        self._connect_screen = self._build_connect_screen()
        self._chat_screen = ChatScreen(self._my_id)
        self._stack.addWidget(self._connect_screen)
        self._stack.addWidget(self._chat_screen)

        self._chat_screen.sig_send.connect(self._on_send)
        self._chat_screen.sig_exit.connect(self._on_exit_chat)

    def _build_connect_screen(self):
        w = QWidget()
        w.setStyleSheet(f"background:{T['BG_DEEP']};")
        outer = QVBoxLayout(w)
        outer.setAlignment(Qt.AlignCenter)

        card = RoundedFrame(radius=8)
        card.setFixedWidth(440)
        outer.addWidget(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(20)

        radar = RadarWidget()
        radar.setFixedSize(120, 120)
        radar_row = QHBoxLayout()
        radar_row.addStretch(); radar_row.addWidget(radar); radar_row.addStretch()
        lay.addLayout(radar_row)

        id_lbl = QLabel(f"Ваш ID:  {self._my_id}")
        id_lbl.setFont(mono(10))
        id_lbl.setAlignment(Qt.AlignCenter)
        id_lbl.setStyleSheet(
            f"color:{T['TEXT_BRIGHT']};background:{T['BG_DEEP']};"
            f"border:1px solid {T['BORDER']};border-radius:4px;padding:6px;"
        )
        lay.addWidget(id_lbl)

        ip_lbl = QLabel(f"IP:  {self._local_ip}")
        ip_lbl.setFont(mono(9))
        ip_lbl.setAlignment(Qt.AlignCenter)
        ip_lbl.setStyleSheet(f"color:{T['MUTED']};background:transparent;")
        lay.addWidget(ip_lbl)

        lay.addSpacing(4)

        self._stack_inputs = QStackedWidget()
        self._stack_inputs.setFixedHeight(100)

        pane_id = QWidget()
        pid = QVBoxLayout(pane_id)
        pid.setContentsMargins(0, 0, 0, 0)
        self._inp_id = GlowInput("ID собеседника...")
        self._lbl_id_status = QLabel("")
        self._lbl_id_status.setFont(font(9))
        self._lbl_id_status.setStyleSheet(f"color:{T['MUTED']};background:transparent;")
        pid.addWidget(self._inp_id)
        pid.addWidget(self._lbl_id_status)

        pane_ip = QWidget()
        pip = QVBoxLayout(pane_ip)
        pip.setContentsMargins(0, 0, 0, 0)
        self._inp_ip = GlowInput("IP-адрес собеседника...")
        self._lbl_ip_status = QLabel("")
        self._lbl_ip_status.setFont(font(9))
        self._lbl_ip_status.setStyleSheet(f"color:{T['MUTED']};background:transparent;")
        pip.addWidget(self._inp_ip)
        pip.addWidget(self._lbl_ip_status)

        pane_wait = QWidget()
        pwt = QVBoxLayout(pane_wait)
        pwt.setContentsMargins(0, 0, 0, 0)
        self._lbl_wait_status = QLabel("Ожидание подключения...")
        self._lbl_wait_status.setFont(font(9))
        self._lbl_wait_status.setAlignment(Qt.AlignCenter)
        self._lbl_wait_status.setStyleSheet(f"color:{T['MUTED']};background:transparent;")
        pwt.addWidget(self._lbl_wait_status)

        self._stack_inputs.addWidget(pane_id)
        self._stack_inputs.addWidget(pane_ip)
        self._stack_inputs.addWidget(pane_wait)
        lay.addWidget(self._stack_inputs)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_by_id = GlowButton("По ID")
        self._btn_by_ip = GlowButton("По IP")
        self._btn_wait  = GlowButton("Ждать", accent=T['WARM'])
        btn_row.addWidget(self._btn_by_id)
        btn_row.addWidget(self._btn_by_ip)
        btn_row.addWidget(self._btn_wait)
        lay.addLayout(btn_row)

        self._btn_connect = GlowButton("Подключиться")
        self._btn_connect.setVisible(False)
        lay.addWidget(self._btn_connect)

        self._btn_by_id.clicked.connect(lambda: self._select_mode('id'))
        self._btn_by_ip.clicked.connect(lambda: self._select_mode('ip'))
        self._btn_wait.clicked.connect(lambda: self._select_mode('wait'))
        self._btn_connect.clicked.connect(self._start_connect)

        bg = ParticleBackground(count=40)
        bg.setParent(w)
        bg.lower()

        return w

    def _select_mode(self, mode):
        idx = {'id': 0, 'ip': 1, 'wait': 2}.get(mode, 0)
        self._stack_inputs.setCurrentIndex(idx)
        self._btn_connect.setVisible(mode != 'wait')
        if mode == 'wait':
            self._start_connect_wait()

    def _set_status(self, msg, is_error=False):
        if self._stack_inputs.currentIndex() == 0:
            lbl = self._lbl_id_status
        elif self._stack_inputs.currentIndex() == 1:
            lbl = self._lbl_ip_status
        else:
            lbl = self._lbl_wait_status
        c = T['DANGER'] if is_error else T['ACCENT']
        lbl.setStyleSheet(f"color:{c};background:transparent;")
        lbl.setText(msg)

    def _start_connect(self):
        idx = self._stack_inputs.currentIndex()
        if idx == 0:
            tid = self._inp_id.text().strip()
            if not tid:
                self._inp_id.shake()
                self._set_status("Введите ID", is_error=True); return
            self._run_worker('connect_id', target_id=tid)
        elif idx == 1:
            ip = self._inp_ip.text().strip()
            if not ip:
                self._inp_ip.shake()
                self._set_status("Введите IP", is_error=True); return
            self._run_worker('connect_ip', peer_ip=ip)

    def _start_connect_wait(self):
        self._run_worker('wait')

    def _run_worker(self, mode, target_id='', peer_ip=''):
        if self._conn_worker and self._conn_worker.isRunning():
            self._conn_worker.quit()
        self._set_status("Подключаюсь...")
        self._conn_worker = ConnWorker(mode, self._my_id, target_id, peer_ip, self)
        self._conn_worker.sig_ok.connect(self._on_connected)
        self._conn_worker.sig_fail.connect(lambda m: self._set_status(m, is_error=True))
        self._conn_worker.sig_status.connect(self._set_status)
        self._conn_worker.start()

    def _on_connected(self, peer_id, peer_ip):
        self._last_peer_id = peer_id; self._last_peer_ip = peer_ip
        self._active_conn = self._conn_worker.connection
        self._chat_screen.set_peer(peer_id, peer_ip)
        self._chat_screen.add_system(f"✅ Подключено: {peer_id}")
        self._chat_screen._status_bar.start_session()
        self._fade_to(1)
        self._start_receiver()
        self._flash.flash()

    def _start_receiver(self):
        if self._msg_receiver:
            self._msg_receiver.stop()
        self._msg_receiver = MessageReceiver(self._active_conn, self)
        self._msg_receiver.sig_message.connect(self._on_message)
        self._msg_receiver.sig_disconnect.connect(self._on_disconnect)
        self._msg_receiver.start()

    def _on_message(self, text):
        self._chat_screen.add_message(text, self._last_peer_id, False)

    def _on_disconnect(self):
        self._chat_screen.add_system("❌ Соединение разорвано")
        QTimer.singleShot(2000, self._try_reconnect)

    def _try_reconnect(self):
        if self._last_peer_ip:
            self._chat_screen.add_system("🔄 Переподключение...")
            self._run_worker('connect_ip', target_id=self._last_peer_id, peer_ip=self._last_peer_ip)

    def _on_send(self, text):
        if self._active_conn:
            ok = self._active_conn.send_message(text)
            if not ok:
                self._chat_screen.add_system("⚠️ Ошибка отправки")

    def _on_exit_chat(self):
        if self._msg_receiver: self._msg_receiver.stop()
        if self._active_conn: self._active_conn.close()
        self._active_conn = None
        self._go_to_connect()

    def _go_to_connect(self):
        self._fade_to(0)

    def _fade_to(self, idx):
        self._stack.setCurrentIndex(idx)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._flash.setGeometry(0, 0, self.width(), self.height())
        self._scanlines.setGeometry(0, 0, self.width(), self.height())

    def _center(self):
        from PyQt5.QtWidgets import QDesktopWidget
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp); self.move(qr.topLeft())


def _make_app_icon():
    from PyQt5.QtGui import QIcon, QPixmap
    size = 64
    px = QPixmap(size, size)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    bg   = QColor(T['BG_CARD'])
    acc  = QColor(T['ACCENT'])
    acc2 = QColor(T['TEXT_BRIGHT'])
    p.setBrush(QBrush(bg)); p.setPen(QPen(acc, 1.5))
    p.drawRoundedRect(2, 2, 60, 60, 10, 10)
    lx, ly = 8, 10
    p.setPen(QPen(acc, 3, Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush)
    from PyQt5.QtCore import QRectF as _RF
    p.drawArc(_RF(lx+2, ly, 16, 14), 0*16, 180*16)
    p.setBrush(QBrush(acc)); p.setPen(Qt.NoPen)
    p.drawRoundedRect(lx, ly+10, 20, 15, 3, 3)
    p.setBrush(QBrush(QColor(T['BG_DEEP'])))
    p.drawEllipse(lx+7, ly+13, 6, 6)
    p.drawRect(lx+9, ly+17, 2, 5)
    kx, ky = 32, 22
    p.setPen(QPen(acc2, 2.5, Qt.SolidLine, Qt.RoundCap)); p.setBrush(Qt.NoBrush)
    p.drawEllipse(kx, ky, 12, 12)
    p.drawLine(kx+12, ky+6, kx+26, ky+6)
    for dx, dy in [(kx+20, ky+6), (kx+23, ky+6)]:
        p.drawLine(dx, dy, dx, ky+10)
    p.end()
    return QIcon(px)


def main():
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('QuoKat.P2P.Messenger')
        except Exception:
            pass

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("QuoKat")
    app.setQuitOnLastWindowClosed(False)

    icon = _make_app_icon()
    app.setWindowIcon(icon)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window,          qc(T['BG_DEEP']))
    pal.setColor(QPalette.WindowText,      qc(T['TEXT']))
    pal.setColor(QPalette.Base,            qc(T['BG_SURFACE']))
    pal.setColor(QPalette.AlternateBase,   qc(T['BG_CARD']))
    pal.setColor(QPalette.Text,            qc(T['TEXT_BRIGHT']))
    pal.setColor(QPalette.Button,          qc(T['BG_CARD']))
    pal.setColor(QPalette.ButtonText,      qc(T['TEXT']))
    pal.setColor(QPalette.Highlight,       qc(T['ACCENT']))
    pal.setColor(QPalette.HighlightedText, qc(T['BG_DEEP']))
    app.setPalette(pal)

    win = QuoKatWindow()
    win.setWindowIcon(icon)
    win.show()

    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(icon, app)
        tray.setToolTip("QuoKat — зашифрованный P2P мессенджер")
        menu = QMenu()
        _style = (
            "QMenu{background:" + T['BG_CARD'] + ";color:" + T['TEXT_BRIGHT'] + ";"
            "border:1px solid " + T['BORDER'] + ";border-radius:4px;padding:4px;}"
            "QMenu::item{padding:6px 20px;border-radius:3px;}"
            "QMenu::item:selected{background:" + T['BG_HOVER'] + ";}"
        )
        menu.setStyleSheet(_style)
        act_show = QAction("Показать / Скрыть", app)
        act_quit = QAction("Выйти", app)
        def _toggle():
            if win.isVisible(): win.hide()
            else: win.show(); win.raise_(); win.activateWindow()
        act_show.triggered.connect(_toggle)
        act_quit.triggered.connect(app.quit)
        tray.activated.connect(
            lambda reason: _toggle() if reason == QSystemTrayIcon.DoubleClick else None)
        menu.addAction(act_show); menu.addSeparator(); menu.addAction(act_quit)
        tray.setContextMenu(menu); tray.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

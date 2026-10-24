"""
Bauernhaus - Gebaeudeteil 1 (linker Teil im Grundriss, Raeume mit Kennung (1))
Fusion-Skript: erzeugt ein Volumenmodell KG / EG / OG / DG / Dach.

Quelle: Grundrisse Keller- bis Dachgeschoss, M 1:100 (Bestand/Abbruch/Neu).
Alle Masse in Metern; Fusion arbeitet intern in cm (Faktor 100 in den Backends).

Koordinatensystem (Z oben):
  X = Plan-Rechts (Giebelwand links im Plan = x 0), Gebaeudetrennwand bei x 7.82
  Y = Nordfassade y 0 ... Suedfassade y 13.195  (Planoben = Sueden, Draufsicht = Plan)
  Z = 0.00 = OKFF EG

Plan-Koordinaten (x, yp) werden 1:1 aus den Masslinien uebernommen, yp von der
Planoberkante (Suedfassade, Aussenkante) nach unten gemessen; Umrechnung Y = D - yp.

Annahmen (nicht im Grundriss bemasst) stehen gesammelt unter ANNAHMEN.
"""

import math

try:
    import adsk.core
    import adsk.fusion
    import traceback
except ImportError:  # Vorschau ausserhalb von Fusion
    adsk = None

# ---------------------------------------------------------------------------
# Bemassung aus dem Grundriss
# ---------------------------------------------------------------------------
D = 13.195             # Gebaeudetiefe Teil 1 (Nord-Sued)
X_IN = 7.82            # Innenkante Gebaeudetrennwand (0.65 + 4.18 + 0.24 + 2.75)
T_TRENN = 0.74         # Gebaeudetrennwand
KG_B = 6.29            # Kellerbreite (1.07 + 4.15 + 1.07)

# ---------------------------------------------------------------------------
# ANNAHMEN (Hoehen / Dach) - hier anpassen
# ---------------------------------------------------------------------------
TRENNWAND_VOLL = True  # True: volle 74 cm Trennwand, False: bis Achse
H_GESCHOSS = 2.75      # Geschosshoehe EG/OG (OKFF-OKFF)
T_DECKE = 0.30         # Deckenstaerke
Z_EG = 0.00
Z_OG = Z_EG + H_GESCHOSS
Z_DG = Z_OG + H_GESCHOSS
Z_KG = -2.65           # OKFF Keller (Gewoelbe: Kaempfer +1.00, mittl. Hoehe ~1.90 lt. Plan)
KG_KAEMPFER = 1.00
KG_STICH = 1.20

DACH_NEIGUNG = 40.0    # Grad
DACH_T = 0.30          # Dachaufbau senkrecht zur Dachflaeche
KNIESTOCK = 0.30       # Oberkante Dachflaeche ueber OKFF DG in Fassadenflucht
UEBERSTAND_TRAUFE = 0.40
UEBERSTAND_ORTGANG = 0.30

GAUBE_X = (1.49, 6.25)       # Suedgaube, aus Masskette DG
GAUBE_WANGE = 0.24
GAUBE_FRONT_T = 0.30
GAUBE_OK_FRONT = 7.90        # OK Gaubendach an der Fassade (absolut)
GAUBE_NEIGUNG = 15.0
GAUBE_DACH_T = 0.22

KEHLBALKENDECKE = True       # Decke ueber DG bei +2.60 ueber OKFF DG
BALKON = True
GELAENDE = True

FENSTER_BRUESTUNG = 0.90
TUER_H = 2.10
INNENTUER_H = 2.01

X_END = X_IN + (T_TRENN if TRENNWAND_VOLL else T_TRENN / 2)
TA = math.tan(math.radians(DACH_NEIGUNG))
SA, CA = math.sin(math.radians(DACH_NEIGUNG)), math.cos(math.radians(DACH_NEIGUNG))
ZT = Z_DG + KNIESTOCK                    # Trauflinie Dachoberseite in Fassadenflucht
Z_FIRST = ZT + D / 2 * TA


def Y(yp):
    return D - yp


# ---------------------------------------------------------------------------
# Geometrie-Bausteine (backend-unabhaengig)
# ---------------------------------------------------------------------------
def norm(v):
    l = math.sqrt(sum(c * c for c in v))
    return tuple(c / l for c in v)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def add(a, b, s=1.0):
    return tuple(x + s * y for x, y in zip(a, b))


class Builder:
    def __init__(self, G):
        self.G = G
        self.parts = {}   # (komponente, kategorie) -> [bodies]

    # -- Primitive ---------------------------------------------------------
    def box(self, x0, x1, y0, y1, z0, z1):
        return self.G.box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1))

    def pbox(self, x0, x1, yp0, yp1, z0, z1):
        """Quader in Plan-Koordinaten."""
        return self.box(x0, x1, Y(yp0), Y(yp1), z0, z1)

    def obox(self, c, u, v, lu, lv, lw):
        return self.G.obox(c, norm(u), norm(v), lu, lv, lw)

    def halfspace(self, p, n, size=100.0):
        """Grosser Quader auf der Seite +n der Ebene durch p."""
        n = norm(n)
        a = (1, 0, 0) if abs(n[0]) < 0.9 else (0, 1, 0)
        u = norm(cross(a, n))
        v = cross(n, u)
        return self.G.obox(add(p, n, size / 2), u, v, size, size, size)

    def prism(self, pts, z0, z1):
        """Konvexes Prisma aus Modell-(x,y)-Punkten."""
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        b = self.box(min(xs), max(xs), min(ys), max(ys), z0, z1)
        area = sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))
        sgn = -1 if area > 0 else 1   # area>0 -> Punkte im Uhrzeigersinn
        for i in range(len(pts)):
            a, c = pts[i - 1], pts[i]
            dx, dy = c[0] - a[0], c[1] - a[1]
            n = (sgn * dy, -sgn * dx, 0)  # Aussennormale
            b = self.G.diff(b, self.halfspace((a[0], a[1], 0), n))
        return b

    def emit(self, comp, cat, body):
        if body is not None:
            self.parts.setdefault((comp, cat), []).append(body)

    # -- Waende mit Oeffnungen --------------------------------------------
    def wall(self, comp, a, b, t, z0, z1, ops=(), cat='Waende', clip=None):
        """Wand mit Mittellinie a->b (Modell x,y). ops: (s0, s1, zb, zt, art), s ab a,
        zb/zt relativ zu z0. art: 'F' Fenster, 'T' Aussentuer, 'G' Fenstertuer, 'O' Durchgang."""
        G = self.G
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        u = (dx / L, dy / L, 0)
        w = (-u[1], u[0], 0)
        c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (z0 + z1) / 2)
        body = self.obox(c, u, w, L, t, z1 - z0)
        for s0, s1, zb, zt, art in ops:
            sm, ow, oh = (s0 + s1) / 2, s1 - s0, zt - zb
            oc = (a[0] + u[0] * sm, a[1] + u[1] * sm, z0 + (zb + zt) / 2)
            body = G.diff(body, self.obox(oc, u, w, ow, t + 0.2, oh))
            if art in ('F', 'G', 'T'):
                frame = self.obox(oc, u, w, ow, 0.08, oh)
                frame = G.diff(frame, self.obox(oc, u, w, ow - 0.12, 0.2, oh - 0.12))
                self.emit(comp, 'Fensterrahmen', frame)
                if art == 'T':
                    self.emit(comp, 'Tueren', self.obox(oc, u, w, ow - 0.12, 0.06, oh - 0.12))
                else:
                    self.emit(comp, 'Verglasung', self.obox(oc, u, w, ow - 0.12, 0.02, oh - 0.12))
        if clip is not None:
            body = G.inter(body, G.copy(clip))
        self.emit(comp, cat, body)

    def hwall(self, comp, yp0, yp1, x0, x1, z0, z1, ops=(), **kw):
        """Wand parallel X, belegt Plan-y [yp0, yp1]; ops in absoluten x."""
        ym = Y((yp0 + yp1) / 2)
        o = [(xa - x0, xb - x0, zb, zt, k) for xa, xb, zb, zt, k in ops]
        self.wall(comp, (x0, ym), (x1, ym), yp1 - yp0, z0, z1, o, **kw)

    def vwall(self, comp, x0, x1, yp0, yp1, z0, z1, ops=(), **kw):
        """Wand parallel Y, belegt x [x0, x1]; ops in absoluten Plan-y."""
        xm = (x0 + x1) / 2
        o = [(ya - yp0, yb - yp0, zb, zt, k) for ya, yb, zb, zt, k in ops]
        self.wall(comp, (xm, Y(yp0)), (xm, Y(yp1)), x1 - x0, z0, z1, o, **kw)

    def dwall(self, comp, p0, p1, t, z0, z1, ops=(), **kw):
        """Wand zwischen zwei Plan-Punkten (Mittellinie); ops in m ab p0."""
        self.wall(comp, (p0[0], Y(p0[1])), (p1[0], Y(p1[1])), t, z0, z1, ops, **kw)

    def stair(self, comp, x0, x1, yp_start, yp_end, z_base, rise_total, n, t=0.16):
        """Gerader Lauf, steigt von Plan-y yp_start nach yp_end (n Steigungen)."""
        h = rise_total / n
        g = (yp_start - yp_end) / (n - 1)
        steps = None
        for i in range(1, n):
            a, b = yp_start - (i - 1) * g, yp_start - i * g
            z_top = z_base + i * h
            s = self.pbox(x0, x1, b, a, max(z_base, z_top - h - t), z_top)
            steps = s if steps is None else self.G.union(steps, s)
        self.emit(comp, 'Treppe', steps)


# ---------------------------------------------------------------------------
# Modell
# ---------------------------------------------------------------------------
def build(B):
    G = B.G
    F, T, GT, O = 'F', 'T', 'G', 'O'
    fb = FENSTER_BRUESTUNG

    # Dachebenen: Oberseite / Unterseite Sued und Nord
    n_s, n_n = (0, SA, CA), (0, -SA, CA)
    p_s, p_n = (0, D, ZT), (0, 0, ZT)
    p_s_u, p_n_u = add(p_s, n_s, -DACH_T), add(p_n, n_n, -DACH_T)

    def unter_dach():
        """Raum unterhalb der Dachunterseite."""
        r = B.box(-10, X_END + 10, -10, D + 10, -20, 40)
        r = G.diff(r, B.halfspace(p_s_u, n_s))
        return G.diff(r, B.halfspace(p_n_u, n_n))

    inner = unter_dach()

    # Gaube (Schleppgaube Sued)
    tb = math.tan(math.radians(GAUBE_NEIGUNG))
    n_g = (0, math.sin(math.radians(GAUBE_NEIGUNG)), math.cos(math.radians(GAUBE_NEIGUNG)))
    p_g = (0, D, GAUBE_OK_FRONT)
    p_g_u = add(p_g, n_g, -GAUBE_DACH_T)
    gd = (GAUBE_OK_FRONT - ZT) / (TA - tb)     # Gaubentiefe bis Dachverschneidung
    gx0, gx1 = GAUBE_X
    gi0, gi1 = gx0 + GAUBE_WANGE, gx1 - GAUBE_WANGE

    gaube_raum = B.box(gi0, gi1, D - gd, D - GAUBE_FRONT_T, Z_DG, 20)
    gaube_raum = G.diff(gaube_raum, B.halfspace(p_g_u, n_g))
    dg_raum = G.union(G.copy(inner), gaube_raum)

    # Schornstein (Plan: x 0.70-1.08, yp 5.39-5.77)
    def kamin():
        return B.pbox(0.70, 1.08, 5.39, 5.77, Z_EG - T_DECKE, Z_FIRST + 0.50)

    # ======================= KG =========================================
    kz0, kz1 = Z_KG, Z_EG - T_DECKE
    B.vwall('KG', 0, 1.07, 0, D, kz0, kz1, cat='Waende')
    B.vwall('KG', KG_B - 1.07, KG_B, 0, D, kz0, kz1, cat='Waende')
    B.hwall('KG', 0, 0.50, 1.07, KG_B - 1.07, kz0, kz1,
            [(1.64, 2.06, 1.45, 1.95, F), (3.53, 4.00, 1.45, 1.95, F)])
    B.hwall('KG', D - 0.65, D, 1.07, KG_B - 1.07, kz0, kz1, [(2.55, 3.34, 1.45, 1.95, F)])
    B.hwall('KG', 4.175, 4.675, 1.07, KG_B - 1.07, kz0, kz1, [(2.80, 3.65, 0, 1.95, O)])
    # Vorsatzschale NEU (schraffiert)
    B.vwall('KG', 4.93, 5.15, 1.78, 12.545, kz0, kz0 + KG_KAEMPFER, cat='Innenwaende')
    B.emit('KG', 'Boden', B.box(0, KG_B, 0, D, kz0 - 0.20, kz0))
    # Segmentbogen-Tonnengewoelbe, Spannweite 4.15
    s = KG_B - 2 * 1.07
    R = (s * s / 4 + KG_STICH ** 2) / (2 * KG_STICH)
    zc = kz0 + KG_KAEMPFER + KG_STICH - R
    xc = KG_B / 2
    for yp0, yp1 in ((4.675, 12.545), (0.50, 4.175)):
        v = B.pbox(1.07, KG_B - 1.07, yp0, yp1, kz0 + KG_KAEMPFER, kz1)
        v = G.diff(v, G.cyl((xc, Y(yp1) - 0.1, zc), (xc, Y(yp0) + 0.1, zc), R))
        B.emit('KG', 'Gewoelbe', v)

    # ======================= EG =========================================
    z0, z1 = Z_EG, Z_OG - T_DECKE
    slab = B.box(0, X_IN, 0, D, Z_EG - T_DECKE, Z_EG)
    B.emit('EG', 'Bodenplatte', G.diff(slab, kamin()))
    # Aussenwaende
    B.hwall('EG', 0, 0.50, 0, X_IN, z0, z1,
            [(1.46, 2.28, 0, TUER_H, T), (5.33, 6.15, 0, TUER_H, T)], cat='Aussenwaende')
    B.hwall('EG', 12.545, D, 0, X_IN, z0, z1,
            [(1.14, 2.09, fb, fb + 1.20, F), (3.81, 4.82, 0, TUER_H + 0.10, T),
             (5.14, 7.61, 0, 2.20, T)], cat='Aussenwaende')
    B.vwall('EG', 0, 0.74, 0.50, 6.45, z0, z1, cat='Aussenwaende')
    B.vwall('EG', 0, 0.65, 6.45, 12.545, z0, z1, [(6.45, 7.36, fb, fb + 1.20, F)],
            cat='Aussenwaende')
    # Innenwaende
    B.hwall('EG', 3.295, 3.41, 0.74, 4.83, z0, z1, [(3.81, 4.63, 0, INNENTUER_H, O)],
            cat='Innenwaende')
    B.hwall('EG', 7.795, 8.035, 0.65, 4.83, z0, z1, [(3.81, 4.63, 0, INNENTUER_H, O)],
            cat='Innenwaende')
    B.vwall('EG', 4.83, 5.07, 0.50, 12.545, z0, z1, [(9.90, 10.75, 0, INNENTUER_H, O)],
            cat='Innenwaende')
    B.hwall('EG', 10.93, 11.045, 3.17, 4.83, z0, z1, [(3.35, 4.15, 0, INNENTUER_H, O)],
            cat='Innenwaende')
    B.vwall('EG', 3.17, 3.285, 11.045, 12.545, z0, z1, cat='Innenwaende')
    B.stair('EG', 0.65, 1.60, 12.50, 9.00, Z_EG, H_GESCHOSS, 15)

    # ======================= OG =========================================
    z0, z1 = Z_OG, Z_DG - T_DECKE
    slab = B.box(0, X_IN, 0, D, Z_OG - T_DECKE, Z_OG)
    slab = G.diff(slab, B.pbox(0.59, 1.60, 9.00, 12.25, -20, 40))          # Treppe
    slab = G.diff(slab, B.pbox(1.60, 3.20, 9.00, 11.55, -20, 40))          # Luftraum
    slab = G.diff(slab, B.prism([(3.20, Y(9.00)), (4.78, Y(9.00)), (3.20, Y(11.55))], -20, 40))
    B.emit('OG', 'Decke', G.diff(slab, kamin()))
    B.hwall('OG', 0, 0.50, 0, X_IN, z0, z1,
            [(1.49, 4.50, 0, 2.135, GT), (5.24, 6.25, 0, 2.135, GT)], cat='Aussenwaende')
    B.hwall('OG', 12.605, D, 0, X_IN, z0, z1,
            [(1.13, 2.06, fb, fb + 1.26, F), (3.81, 4.74, fb, fb + 1.26, F),
             (6.63, 7.56, fb, fb + 1.26, F)], cat='Aussenwaende')
    B.vwall('OG', 0, 0.59, 0.50, 12.605, z0, z1, [(6.66, 7.92, fb, fb + 1.26, F)],
            cat='Aussenwaende')
    # Abstellraum (10)
    B.vwall('OG', 4.78, 4.895, 6.54, 7.935, z0, z1, [(6.75, 7.60, 0, INNENTUER_H, O)],
            cat='Innenwaende')
    B.hwall('OG', 6.54, 6.655, 4.895, X_IN, z0, z1, cat='Innenwaende')
    B.hwall('OG', 7.82, 7.935, 4.895, X_IN, z0, z1, cat='Innenwaende')
    # WC (8)
    B.hwall('OG', 10.85, 10.965, 4.85, X_IN, z0, z1, [(6.10, 6.90, 0, INNENTUER_H, O)],
            cat='Innenwaende')
    B.vwall('OG', 4.85, 4.965, 10.965, 12.605, z0, z1, cat='Innenwaende')
    # Wandvorlage NEU an Kueche
    B.vwall('OG', 4.85, 5.07, 0.50, 1.70, z0, z1, cat='Innenwaende')
    # Galeriegelaender am Luftraum
    for p, q in (((1.60, 9.00), (4.78, 9.00)), ((4.78, 9.00), (3.20, 11.55)),
                 ((3.20, 11.55), (1.60, 11.55))):
        B.dwall('OG', p, q, 0.04, Z_OG, Z_OG + 1.00, cat='Gelaender')
    B.stair('OG', 0.59, 1.60, 12.50, 9.00, Z_OG, H_GESCHOSS, 15)

    # Balkon Sued (13): x 1.26-6.59, Tiefe 3.00
    if BALKON:
        bz = Z_OG - 0.05
        B.emit('OG', 'Balkon', B.box(1.26, 6.59, D, D + 3.00, bz - 0.20, bz))
        for p, q in (((1.28, -0.0), (1.28, -3.00)), ((6.57, 0.0), (6.57, -3.00)),
                     ((1.26, -2.98), (3.47, -2.98)), ((4.42, -2.98), (6.59, -2.98))):
            B.dwall('OG', p, q, 0.04, bz, bz + 1.00, cat='Gelaender')
        for x in (1.40, 6.45):
            B.emit('OG', 'Balkon', B.box(x - 0.08, x + 0.08, D + 2.77, D + 2.93, -0.15, bz - 0.20))
        # Aussentreppe zum Garten
        B.stair('OG', 3.47, 4.42, -2.98 - 15 * 0.27, -2.98, -0.15, bz + 0.15, 16)

    # ======================= DG =========================================
    z0 = Z_DG
    z1 = Z_DG + 2.60
    slab = B.box(0, X_IN, 0, D, Z_DG - T_DECKE, Z_DG)
    slab = G.diff(slab, B.pbox(0.59, 1.60, 9.00, 12.25, -20, 40))
    B.emit('DG', 'Decke', G.diff(slab, kamin()))
    # Kniestock Sued / Nord (unter Dach beschnitten), unter der Gaube voll
    for xa, xb in ((0, gx0), (gx1, X_IN)):
        B.hwall('DG', 0, 0.50, xa, xb, z0, ZT, cat='Aussenwaende', clip=inner)
    B.hwall('DG', 0, 0.50, gx0, gx1, z0, ZT, cat='Aussenwaende')
    B.hwall('DG', D - 0.59, D, 0, X_IN, z0, ZT, cat='Aussenwaende', clip=inner)
    # Giebelwand
    B.vwall('DG', 0, 0.59, 0, D, z0, Z_FIRST, cat='Aussenwaende', clip=inner)
    # Gaube: Front, Wangen, Dach
    wb = 0.80
    B.hwall('DG', 0, GAUBE_FRONT_T, gx0, gx1, ZT, GAUBE_OK_FRONT + 0.5,
            [(1.73, 2.99, Z_DG + wb - ZT, Z_DG + wb + 1.26 - ZT, F),
             (3.24, 4.50, Z_DG + wb - ZT, Z_DG + wb + 1.26 - ZT, F),
             (4.75, 6.01, Z_DG + wb - ZT, Z_DG + wb + 1.26 - ZT, F)],
            cat='Gaube', clip=G.diff(B.box(-10, 20, -10, 30, -20, 40), B.halfspace(p_g_u, n_g)))
    for xa, xb in ((gx0, gi0), (gi1, gx1)):
        w = B.box(xa, xb, D - gd - 0.1, D - GAUBE_FRONT_T, Z_DG, 20)
        w = G.diff(w, B.halfspace(p_g_u, n_g))
        w = G.diff(w, B.halfspace(p_s, (0, -SA, -CA)))
        B.emit('DG', 'Gaube', w)
    # Innenwaende DG (d = 11.5 cm), beschnitten auf Dachraum
    t = 0.115
    kw = dict(cat='Innenwaende', clip=dg_raum)
    B.vwall('DG', 4.60, 4.715, 0.50, 5.26, z0, z1, **kw)
    B.hwall('DG', 5.26, 5.375, 0.59, 1.59, z0, z1, **kw)
    B.hwall('DG', 5.26, 5.375, 2.36, 5.17, z0, z1, [(3.57, 4.45, 0, INNENTUER_H, O)], **kw)
    B.vwall('DG', 3.44, 3.555, 5.375, 6.25, z0, z1, **kw)
    B.dwall('DG', (3.4975, 6.25), (1.79, 7.84), t, z0, z1, **kw)
    B.hwall('DG', 7.7825, 7.8975, 0.59, 1.79, z0, z1, **kw)
    B.dwall('DG', (5.17, 5.3175), (6.12, 6.31), t, z0, z1, [(0.25, 1.05, 0, INNENTUER_H, O)], **kw)
    B.hwall('DG', 6.2525, 6.3675, 6.12, X_IN, z0, z1, **kw)
    B.dwall('DG', (6.12, 6.31), (5.45, 7.27), t, z0, z1, [(0.15, 0.95, 0, INNENTUER_H, O)], **kw)
    B.hwall('DG', 7.27, 7.385, 3.95, 5.45, z0, z1, [(4.10, 4.90, 0, INNENTUER_H, O)], **kw)
    B.vwall('DG', 5.07, 5.185, 7.385, 12.605, z0, z1, **kw)
    B.dwall('DG', (3.95, 7.3275), (2.2525, 8.99), t, z0, z1, **kw)
    B.vwall('DG', 2.195, 2.31, 8.99, 12.605, z0, z1, **kw)
    if KEHLBALKENDECKE:
        c = B.box(0.59, X_IN, 0, D, z1, z1 + 0.20)
        c = G.inter(c, G.copy(dg_raum))
        B.emit('DG', 'Kehlbalkendecke', G.diff(c, kamin()))

    # ======================= Dach =======================================
    ov = UEBERSTAND_TRAUFE
    z_low = ZT - ov * TA - DACH_T / CA - 0.02
    dach = B.box(-UEBERSTAND_ORTGANG, X_END, -ov, D + ov, z_low, Z_FIRST + 1)
    dach = G.diff(dach, B.halfspace(p_s, n_s))
    dach = G.diff(dach, B.halfspace(p_n, n_n))
    dach = G.diff(dach, G.copy(inner))
    dach = G.diff(dach, B.box(gx0, gx1, D - gd, D + ov + 1, -20, 40))       # Gaubenoeffnung
    # Dachflaechenfenster Nord 90 x 140 (x aus Masskette DG)
    u_n = (0, CA, SA)
    yc = 1.75
    pc_top = (0, yc, ZT + yc * TA)
    for xa, xb in ((1.145, 2.045), (3.825, 4.725), (6.645, 7.545)):
        cx = (xa + xb) / 2
        c = add((cx, pc_top[1], pc_top[2]), n_n, -DACH_T / 2)
        dach = G.diff(dach, B.obox(c, (1, 0, 0), u_n, xb - xa, 1.40, DACH_T + 0.4))
        fr = B.obox(add(c, n_n, DACH_T / 2 - 0.06), (1, 0, 0), u_n, xb - xa, 1.40, 0.12)
        fr = G.diff(fr, B.obox(add(c, n_n, DACH_T / 2 - 0.06), (1, 0, 0), u_n,
                               xb - xa - 0.12, 1.28, 0.4))
        B.emit('Dach', 'Fensterrahmen', fr)
        B.emit('Dach', 'Verglasung', B.obox(add(c, n_n, DACH_T / 2 - 0.08), (1, 0, 0), u_n,
                                            xb - xa - 0.12, 1.28, 0.02))
    B.emit('Dach', 'Dachflaechen', G.diff(dach, kamin()))
    # Gaubendach
    u_g = (0, -math.cos(math.radians(GAUBE_NEIGUNG)), math.sin(math.radians(GAUBE_NEIGUNG)))
    y_front, y_back = D + 0.25, D - gd - 0.8
    Lg = (y_front - y_back) / math.cos(math.radians(GAUBE_NEIGUNG))
    p_front = (0, y_front, GAUBE_OK_FRONT - (y_front - D) * tb)
    c = add(add(p_front, u_g, Lg / 2), n_g, -GAUBE_DACH_T / 2)
    c = ((gx0 + gx1) / 2, c[1], c[2])
    gdach = B.obox(c, (1, 0, 0), u_g, gx1 - gx0 + 0.30, Lg, GAUBE_DACH_T)
    gdach = G.diff(gdach, B.halfspace(p_s, (0, -SA, -CA)))
    B.emit('Dach', 'Gaubendach', gdach)
    B.emit('Dach', 'Schornstein', kamin())

    # ======================= Gebaeudetrennwand ===========================
    tw = B.box(X_IN, X_END, 0, D, Z_EG - T_DECKE, Z_FIRST)
    B.emit('Trennwand', 'Gebaeudetrennwand', G.inter(tw, G.copy(inner)))

    if GELAENDE:
        g = B.box(-6, X_END + 6, -6, D + 9, -0.40, -0.15)
        B.emit('Gelaende', 'Gelaende', G.diff(g, B.box(0, KG_B, 0, D, -5, 1)))


# ---------------------------------------------------------------------------
# Fusion-Backend (TemporaryBRepManager)
# ---------------------------------------------------------------------------
CM = 100.0

FARBEN = {
    'Aussenwaende': (236, 230, 216), 'Waende': (170, 162, 150), 'Innenwaende': (245, 245, 240),
    'Gewoelbe': (150, 140, 128), 'Boden': (120, 120, 120), 'Bodenplatte': (160, 160, 160),
    'Decke': (190, 190, 190), 'Kehlbalkendecke': (200, 170, 130), 'Treppe': (160, 110, 60),
    'Fensterrahmen': (60, 60, 60), 'Verglasung': (150, 200, 230), 'Tueren': (110, 75, 45),
    'Gelaender': (60, 60, 60), 'Balkon': (150, 150, 150), 'Gaube': (236, 230, 216),
    'Dachflaechen': (120, 50, 40), 'Gaubendach': (70, 70, 70), 'Schornstein': (150, 60, 50),
    'Gebaeudetrennwand': (200, 120, 120), 'Gelaende': (120, 160, 90),
}


class FusionGeo:
    def __init__(self):
        self.tbm = adsk.fusion.TemporaryBRepManager.get()

    @staticmethod
    def _p(p):
        return adsk.core.Point3D.create(p[0] * CM, p[1] * CM, p[2] * CM)

    @staticmethod
    def _v(v):
        return adsk.core.Vector3D.create(v[0], v[1], v[2])

    def box(self, x0, x1, y0, y1, z0, z1):
        return self.obox(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                         (1, 0, 0), (0, 1, 0), x1 - x0, y1 - y0, z1 - z0)

    def obox(self, c, u, v, lu, lv, lw):
        ob = adsk.core.OrientedBoundingBox3D.create(self._p(c), self._v(u), self._v(v),
                                                   lu * CM, lv * CM, lw * CM)
        return self.tbm.createBox(ob)

    def cyl(self, p0, p1, r):
        return self.tbm.createCylinderOrCone(self._p(p0), r * CM, self._p(p1), r * CM)

    def copy(self, b):
        return self.tbm.copy(b)

    def _op(self, a, b, t):
        self.tbm.booleanOperation(a, b, t)
        return a

    def union(self, a, b):
        return self._op(a, b, adsk.fusion.BooleanTypes.UnionBooleanType)

    def diff(self, a, b):
        return self._op(a, b, adsk.fusion.BooleanTypes.DifferenceBooleanType)

    def inter(self, a, b):
        return self._op(a, b, adsk.fusion.BooleanTypes.IntersectionBooleanType)


def _appearance(app, design, name, rgb):
    try:
        existing = design.appearances.itemByName('BH1 ' + name)
        if existing:
            return existing
        base = None
        for libname in ('Fusion Appearance Library', 'Fusion 360 Appearance Library'):
            lib = app.materialLibraries.itemByName(libname)
            if not lib:
                continue
            want = 'glass' if name == 'Verglasung' else 'paint - enamel glossy'
            for i in range(lib.appearances.count):
                a = lib.appearances.item(i)
                if want in a.name.lower():
                    base = a
                    break
            if base:
                break
        if not base:
            return None
        ap = design.appearances.addByCopy(base, 'BH1 ' + name)
        for i in range(ap.appearanceProperties.count):
            p = adsk.core.ColorProperty.cast(ap.appearanceProperties.item(i))
            if p and not p.isReadOnly:
                p.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 0)
                break
        return ap
    except Exception:
        return None


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        root.name = 'Bauernhaus Teil 1'

        B = Builder(FusionGeo())
        build(B)

        comps = {}
        order = ['KG', 'EG', 'OG', 'DG', 'Dach', 'Trennwand', 'Gelaende']
        for (comp, cat), bodies in sorted(B.parts.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][1])):
            if comp not in comps:
                occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                occ.component.name = comp
                comps[comp] = occ.component
            c = comps[comp]
            body = bodies[0]
            for b in bodies[1:]:
                B.G.union(body, b)
            if design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
                bf = c.features.baseFeatures.add()
                bf.startEdit()
                fb = c.bRepBodies.add(body, bf)
                bf.finishEdit()
                fb = bf.bodies.item(0) if bf.bodies.count else fb
            else:
                fb = c.bRepBodies.add(body)
            fb.name = cat
            ap = _appearance(app, design, cat, FARBEN.get(cat, (200, 200, 200)))
            if ap:
                fb.appearance = ap

        app.activeViewport.fit()
        ui.messageBox('Bauernhaus Teil 1 erzeugt.\nFirst: {:.2f} m ueber OKFF EG'.format(Z_FIRST))
    except Exception:
        if ui:
            ui.messageBox('Fehler:\n{}'.format(traceback.format_exc()))

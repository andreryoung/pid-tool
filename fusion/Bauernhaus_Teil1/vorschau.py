"""
Vorschau ohne Fusion: baut dieselbe CSG mit manifold3d, exportiert ein Mesh (GLB/STL)
und rendert Horizontalschnitte je Geschoss sowie eine 3D-Ansicht.

    pip install manifold3d trimesh matplotlib
    python vorschau.py [ausgabeordner]
"""
import os
import sys

import numpy as np
import manifold3d as m3
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.path import Path
from matplotlib.patches import PathPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Bauernhaus_Teil1 as bh  # noqa: E402


class ManifoldGeo:
    def box(self, x0, x1, y0, y1, z0, z1):
        return m3.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

    def obox(self, c, u, v, lu, lv, lw):
        w = bh.cross(u, v)
        m = m3.Manifold.cube([lu, lv, lw], center=True)
        M = [[u[0], v[0], w[0], c[0]], [u[1], v[1], w[1], c[1]], [u[2], v[2], w[2], c[2]]]
        return m.transform(M)

    def cyl(self, p0, p1, r):
        d = np.subtract(p1, p0)
        h = float(np.linalg.norm(d))
        z = d / h
        a = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
        x = np.cross(a, z); x /= np.linalg.norm(x)
        y = np.cross(z, x)
        m = m3.Manifold.cylinder(h, r, r, 96)
        M = [[x[0], y[0], z[0], p0[0]], [x[1], y[1], z[1], p0[1]], [x[2], y[2], z[2], p0[2]]]
        return m.transform(M)

    def copy(self, b):
        return b

    def union(self, a, b):
        return a + b

    def diff(self, a, b):
        return a - b

    def inter(self, a, b):
        return a ^ b


def _fill(ax, polys, col):
    """Polygone mit Loechern (even-odd) zeichnen."""
    verts, codes = [], []
    for p in polys:
        p = np.asarray(p)
        if len(p) < 3:
            continue
        verts += list(p) + [p[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(p) - 1) + [Path.CLOSEPOLY]
    if verts:
        ax.add_patch(PathPatch(Path(verts, codes), facecolor=col, edgecolor='k', linewidth=0.4))


def main(out):
    os.makedirs(out, exist_ok=True)
    B = bh.Builder(ManifoldGeo())
    bh.build(B)

    scene = trimesh.Scene()
    merged = {}
    for (comp, cat), bodies in B.parts.items():
        body = bodies[0]
        for b in bodies[1:]:
            body = body + b
        merged[(comp, cat)] = body
        mesh = body.to_mesh()
        if len(mesh.tri_verts) == 0:
            print('LEER:', comp, cat)
            continue
        tm = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False)
        rgb = bh.FARBEN.get(cat, (200, 200, 200))
        tm.visual.face_colors = list(rgb) + [255]
        scene.add_geometry(tm, node_name=f'{comp}_{cat}')
        print(f'{comp:10s} {cat:18s} V={body.volume():8.2f} m3')
    scene.export(os.path.join(out, 'Bauernhaus_Teil1.glb'))

    # Horizontalschnitte
    cuts = {'KG': bh.Z_KG + 0.6, 'EG': 1.0, 'OG': bh.Z_OG + 1.0, 'DG': bh.Z_DG + 1.0}
    fig, axs = plt.subplots(1, 4, figsize=(24, 10))
    for ax, (name, z) in zip(axs, cuts.items()):
        for (comp, cat), body in merged.items():
            if cat in ('Gelaende',):
                continue
            cs = body.slice(z)
            col = np.array(bh.FARBEN.get(cat, (200, 200, 200))) / 255
            _fill(ax, cs.to_polygons(), col)
        ax.set_title(f'{name} Schnitt z={z:+.2f}')
        ax.set_aspect('equal')
        ax.set_xlim(-1, 9.5); ax.set_ylim(-1, bh.D + 4)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'schnitte.png'), dpi=110)

    # 3D-Ansichten
    fig = plt.figure(figsize=(20, 10))
    for k, (el, az) in enumerate(((22, -120), (22, 60))):
        ax = fig.add_subplot(1, 2, k + 1, projection='3d')
        for (comp, cat), body in merged.items():
            if cat == 'Gelaende':
                continue
            mesh = body.to_mesh()
            v, f = mesh.vert_properties[:, :3], mesh.tri_verts
            if len(f) == 0:
                continue
            col = np.array(bh.FARBEN.get(cat, (200, 200, 200))) / 255
            alpha = 0.35 if cat == 'Verglasung' else 1.0
            pc = Poly3DCollection(v[f], facecolor=col, edgecolor=(0, 0, 0, 0.15),
                                  linewidth=0.2, alpha=alpha)
            ax.add_collection3d(pc)
        ax.set_xlim(-2, 12); ax.set_ylim(-1, 17); ax.set_zlim(-3, 12)
        ax.set_box_aspect((14, 18, 15))
        ax.view_init(el, az)
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'ansicht_3d.png'), dpi=110)

    # Querschnitt (Y-Z) bei x = 3.0
    fig, ax = plt.subplots(figsize=(10, 8))
    for (comp, cat), body in merged.items():
        # (x, y, z) -> (z, -y, x): rechtshaendig, Schnitt bei neuem z = altem x
        cs = body.transform([[0, 0, 1, 0], [0, -1, 0, 0], [1, 0, 0, 0]]).slice(3.0)
        col = np.array(bh.FARBEN.get(cat, (200, 200, 200))) / 255
        _fill(ax, [np.c_[-np.array(p)[:, 1], np.array(p)[:, 0]] for p in cs.to_polygons() if len(p)], col)
    ax.set_aspect('equal'); ax.grid(alpha=0.3)
    ax.set_title('Querschnitt x = 3.00 (Y nach rechts = Sued)')
    fig.savefig(os.path.join(out, 'querschnitt.png'), dpi=110)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'vorschau_out')

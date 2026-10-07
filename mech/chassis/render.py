"""Shaded renders of the chassis for review and for the design document.

    python render.py

Tessellates each part straight out of the kernel so the picture always matches
the model, and writes PNGs into ``export/``.
"""

import os

import numpy as np
import pyvista as pv

import model
import params as P

pv.OFF_SCREEN = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, *P.EXPORT_DIR.split("/"))

ALU = "#b8bcc0"
PARTS = [
    ("frame", lambda: model.frame(), ALU, 1.0),
    ("battery", lambda: model.battery(), "#303338", 1.0),
    ("drivers", lambda: model.drivers(), "#1d6b3a", 1.0),
    ("electronics", lambda: model.electronics(), "#55505e", 1.0),
]
MODULE_PARTS = [
    ("wheel", model.hub_motor, "#2b2b2e", 1.0),
    ("yoke", model.steering_yoke, "#9aa0a6", 1.0),
    ("kingpin", model.kingpin_tube, "#c89b2c", 1.0),
    ("housing", model.bearing_housing, ALU, 1.0),
    ("steer_motor", model.steer_motor, "#4a7fb5", 1.0),
    ("steer_bracket", model.steer_bracket, ALU, 1.0),
]


def _mesh(shape, tol=0.3):
    verts, tris = shape.val().tessellate(tol)
    pts = np.array([[v.x, v.y, v.z] for v in verts], dtype=float)
    faces = np.hstack([np.full((len(tris), 1), 3), np.array(tris, dtype=int)]).ravel()
    return pv.PolyData(pts, faces)


def _add_all(pl, with_shell):
    for _, fn, colour, opacity in [(n, f, c, o) for n, f, c, o in PARTS]:
        pl.add_mesh(_mesh(fn()), color=colour, opacity=opacity, smooth_shading=False)
    rails, cell, spring = model.suspension()
    extras = [(rails, "#6e7276"), (cell, "#c25450"), (spring, "#86a886")]
    for _, cx, cy in [(n, x, y) for n, x, y in P.CORNERS]:
        mirror = cy < 0
        for _, fn, colour, _o in MODULE_PARTS:
            s = fn()
            s = s.mirror("XZ") if mirror else s
            pl.add_mesh(_mesh(s).translate((cx, cy, 0)), color=colour, smooth_shading=False)
        for solid, colour in extras:
            s = solid.mirror("XZ") if mirror else solid
            pl.add_mesh(_mesh(s).translate((cx, cy, 0)), color=colour, smooth_shading=False)
    if with_shell:
        for nm, col in [('shell_skirt', '#2b2e31'), ('shell_upper', '#e6e7e4'), ('shell_belt', '#141618'), ('shell_cover', '#232629'), ('shell_panels', '#3b4044'), ('shell_light', '#eef3ff'), ('estop', '#b8282a')]:
            pl.add_mesh(_mesh(getattr(model, nm)()), color=col, smooth_shading=False)


def render(name, direction, with_shell, zoom=1.0, bounds=None, size=(1500, 1050)):
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    _add_all(pl, with_shell)
    pl.enable_parallel_projection()
    pl.view_vector(direction, viewup=(0, 0, 1))
    pl.reset_camera(bounds=bounds)
    pl.camera.zoom(zoom)
    pl.add_light(pv.Light(position=(2500, -2000, 3000), light_type="scene light", intensity=0.5))
    pl.screenshot(os.path.join(OUT, name + ".png"))
    pl.close()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    iso = (1.0, -1.1, 0.62)
    render("render_iso_shell", iso, True, zoom=1.12)
    render("render_iso_bare", iso, False, zoom=1.12)
    render("render_corner", (0.9, -1.0, 0.45), False, zoom=1.05,
           bounds=(180, 480, 100, 400, 0, 400), size=(1300, 1000))
    print("wrote renders to", OUT)

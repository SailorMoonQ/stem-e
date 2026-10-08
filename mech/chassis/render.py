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
import web_export as W

pv.OFF_SCREEN = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, *P.EXPORT_DIR.split("/"))

# One palette for the whole project, kept in web_export so the renders, the
# glTF and the viewer legend cannot drift apart.  They did: a part added to
# the model reached the renders but not the colour table, and only surfaced
# as a KeyError deep inside the export.
COLOURS = W.COLOURS
PARTS = ["frame", "battery", "drivers", "electronics"]
MODULE_PARTS = [("wheel", model.hub_motor), ("yoke", model.steering_yoke),
                ("kingpin", model.kingpin_tube), ("housing", model.bearing_housing),
                ("steer_motor", model.steer_motor),
                ("steer_bracket", model.steer_bracket)]


def _mesh(shape, tol=0.3):
    verts, tris = shape.val().tessellate(tol)
    pts = np.array([[v.x, v.y, v.z] for v in verts], dtype=float)
    faces = np.hstack([np.full((len(tris), 1), 3), np.array(tris, dtype=int)]).ravel()
    return pv.PolyData(pts, faces)


def _add_all(pl, with_shell):
    for nm in PARTS:
        pl.add_mesh(_mesh(getattr(model, nm)()), color=COLOURS[nm], smooth_shading=False)
    rails, cell, spring = model.suspension()
    extras = [(rails, COLOURS["rails"]), (cell, COLOURS["loadcell"]),
              (spring, COLOURS["spring"])]
    for _, cx, cy in P.CORNERS:
        mirror = cy < 0
        for nm, fn in MODULE_PARTS:
            s = fn()
            s = s.mirror("XZ") if mirror else s
            pl.add_mesh(_mesh(s).translate((cx, cy, 0)), color=COLOURS[nm],
                        smooth_shading=False)
        for solid, colour in extras:
            s = solid.mirror("XZ") if mirror else solid
            pl.add_mesh(_mesh(s).translate((cx, cy, 0)), color=colour,
                        smooth_shading=False)
    if with_shell:
        for nm in W.SHELL_PARTS:
            pl.add_mesh(_mesh(getattr(model, nm)()), color=COLOURS[nm],
                        smooth_shading=False)


def render(name, direction, with_shell, zoom=1.0, bounds=None, size=(1500, 1050)):
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("#dfe3e6")
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

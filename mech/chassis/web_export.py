"""Export the chassis as a glTF binary for the interactive web viewer.

    python web_export.py

Parts that turn with the steering go in per corner nodes whose origin sits on
the kingpin axis, so a viewer can rotate them directly.  Everything else is
exported in world coordinates.
"""

import json
import os

import numpy as np
import trimesh

import model
import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "export")
TOL = 0.55

COLOURS = {
    "frame": (0.70, 0.72, 0.74),
    "shell": (0.30, 0.52, 0.72),
    "battery": (0.17, 0.18, 0.20),
    "drivers": (0.09, 0.42, 0.18),
    "wheel": (0.14, 0.14, 0.15),
    "yoke": (0.62, 0.65, 0.68),
    "kingpin": (0.80, 0.62, 0.20),
    "housing": (0.70, 0.72, 0.74),
    "steer_motor": (0.27, 0.51, 0.71),
    "steer_bracket": (0.62, 0.65, 0.68),
    "rails": (0.42, 0.44, 0.46),
    "loadcell": (0.78, 0.33, 0.31),
    "spring": (0.50, 0.72, 0.52),
}


def _mesh(shape, key, opacity=1.0):
    verts, tris = shape.val().tessellate(TOL)
    pts = np.array([[v.x, v.y, v.z] for v in verts], dtype=np.float32)
    m = trimesh.Trimesh(vertices=pts, faces=np.array(tris, dtype=np.int64), process=False)
    r, g, b = COLOURS[key]
    m.visual = trimesh.visual.TextureVisuals(
        material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=[r, g, b, opacity],
            metallicFactor=0.25,
            roughnessFactor=0.55,
            alphaMode="BLEND" if opacity < 1.0 else "OPAQUE",
        )
    )
    return m


def build_scene():
    scene = trimesh.Scene()
    scene.add_geometry(_mesh(model.frame(), "frame"), node_name="frame")
    scene.add_geometry(_mesh(model.battery(), "battery"), node_name="battery")
    scene.add_geometry(_mesh(model.drivers(), "drivers"), node_name="drivers")
    scene.add_geometry(_mesh(model.shell(), "shell", 0.26), node_name="shell")

    rails, cell, spring = model.suspension()
    turning = [("wheel", model.hub_motor()), ("yoke", model.steering_yoke()),
               ("kingpin", model.kingpin_tube())]
    fixed = [("housing", model.bearing_housing()), ("steer_motor", model.steer_motor()),
             ("steer_bracket", model.steer_bracket()), ("rails", rails),
             ("loadcell", cell), ("spring", spring)]

    for name, cx, cy in P.CORNERS:
        T = trimesh.transformations.translation_matrix([cx, cy, 0.0])
        mirror = cy < 0
        for key, solid in turning:
            s = solid.mirror("XZ") if mirror else solid
            scene.add_geometry(_mesh(s, key), node_name="turn_%s_%s" % (name, key), transform=T)
        for key, solid in fixed:
            s = solid.mirror("XZ") if mirror else solid
            scene.add_geometry(_mesh(s, key), node_name="fix_%s_%s" % (name, key), transform=T)
    return scene


THREE_VER = "0.147.0"
CDN = "https://cdn.jsdelivr.net/npm/three@" + THREE_VER + "/"
LIBS = [
    ("three.min.js", "build/three.min.js"),
    ("OrbitControls.js", "examples/js/controls/OrbitControls.js"),
    ("GLTFLoader.js", "examples/js/loaders/GLTFLoader.js"),
]


def _vendor(name, rel):
    """Cache a pinned library next to the exports so the offline page is self contained."""
    import urllib.request
    d = os.path.join(OUT, "vendor")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    if not os.path.exists(p):
        with urllib.request.urlopen(CDN + rel, timeout=120) as r, open(p, "wb") as fh:
            fh.write(r.read())
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def write_pages(glb_path):
    """Emit the artifact page and a double clickable offline page.

    The artifact host's CSP blocks fetching a data: URI, so the model travels
    as a base64 string that the page decodes and hands to GLTFLoader.parse.
    """
    import base64
    with open(glb_path, "rb") as fh:
        uri = "data:model/gltf-binary;base64," + base64.b64encode(fh.read()).decode("ascii")
    with open(os.path.join(HERE, "viewer.html"), encoding="utf-8") as fh:
        html = fh.read()

    import build as B
    import massprops
    curb, _, _ = massprops.chassis_mass_properties()
    st = B.stability()
    fields = {
        "BODY": "%.0f × %.0f × %.0f" % (P.BODY_L, P.BODY_W, P.DECK_Z),
        "CURB": "%.1f" % curb,
        "WB": "%.0f" % P.WHEELBASE,
        "TR": "%.0f" % P.TRACK,
        "GC": "%.0f" % P.GROUND_CLEARANCE,
        "V": "%.2f" % P.V_RATED,
        "FP": "%.0f" % P.F_TRACTIVE_PEAK,
        "SF": "%.2f / %.2f" % (st["fwd_sf"], st["lat_sf"]),
        "IP": "%.1f" % P.I_BUS_PEAK,
        "LIM": "%.0f" % P.STEER_LIMIT_DEG,
        "CORNERS": "{" + ", ".join(
            "%s:[%.0f,%.0f]" % (n, x, y) for n, x, y in P.CORNERS) + "}",
    }
    for k, val in fields.items():
        token = "{{%s}}" % k
        assert token in html, "placeholder missing: " + token
        html = html.replace(token, val)
    assert "{{" not in html, "unsubstituted placeholder left in viewer.html"

    marker = "(function(){"
    assert html.count(marker) == 1, "viewer.html script shape changed"
    html = html.replace(marker, 'var MODEL_URI = "%s";\n%s' % (uri, marker))

    artifact = os.path.join(OUT, "viewer_artifact.html")
    with open(artifact, "w", encoding="utf-8") as fh:
        fh.write(html)

    # Offline copy: its own charset and the three libraries inlined, so the file
    # opens straight off disk with no network at all.  No explicit head or body
    # tags; the parser puts the title, link and style in head and the rest in
    # body on its own.
    local = html
    for name, rel in LIBS:
        tag = '<script src="%s%s"></script>' % (CDN, rel)
        assert tag in local, "script tag not found: " + tag
        local = local.replace(tag, "<script>\n" + _vendor(name, rel) + "\n</script>")
    local = ('<!doctype html>\n<html lang="zh-CN">\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
             + local + "\n</html>\n")

    offline = os.path.join(OUT, "viewer_offline.html")
    with open(offline, "w", encoding="utf-8") as fh:
        fh.write(local)

    for p in (artifact, offline):
        print("wrote %s  %.1f MB" % (p, os.path.getsize(p) / 1e6))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    scene = build_scene()
    path = os.path.join(OUT, "chassis.glb")
    scene.export(path)

    meta = {
        "corners": {n: [x, y] for n, x, y in P.CORNERS},
        "wheelbase": P.WHEELBASE,
        "track": P.TRACK,
        "body": [P.BODY_L, P.BODY_W, P.DECK_Z],
        "steer_limit_deg": P.STEER_LIMIT_DEG,
        "susp_travel_nominal": P.SUSP_TRAVEL_NOMINAL,
        "susp_travel_mech": P.SUSP_TRAVEL_MECH,
        "wheel_od": P.HUB_TIRE_OD,
        "ground_clearance": P.GROUND_CLEARANCE,
    }
    with open(os.path.join(OUT, "chassis_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("wrote %s  %.1f MB" % (path, os.path.getsize(path) / 1e6))

    write_pages(path)



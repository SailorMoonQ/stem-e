"""Build one viewer page carrying both battery layouts, so they can be
switched back and forth rather than opened side by side.

    python build.py && STEM_BATTERY=side python build.py   # or just web_export
    python compare.py

Reads the glb each variant's ``web_export`` produced and emits
``export/compare_artifact.html`` (three.js from the CDN, for publishing) and
``export/compare_offline.html`` (everything inlined, opens off disk).
"""

import base64
import json
import os

import params as P
import web_export as W

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "export")
VARIANTS = ("rear", "side")


def _uri(name):
    path = os.path.join(OUT, name, "chassis.glb")
    if not os.path.exists(path):
        raise SystemExit("missing %s; run STEM_BATTERY=%s python web_export.py" % (path, name))
    with open(path, "rb") as fh:
        return "data:model/gltf-binary;base64," + base64.b64encode(fh.read()).decode("ascii")


def main():
    with open(os.path.join(HERE, "viewer.html"), encoding="utf-8") as fh:
        html = fh.read()

    import build as B
    import massprops
    curb = massprops.chassis_mass_properties()[0]
    st = B.stability()
    fields = {
        "BODY": "%.0f × %.0f × %.0f" % (P.BODY_L, P.BODY_W, P.DECK_Z),
        "CURB": "%.1f" % curb,
        "WB": "%.0f" % P.WHEELBASE,
        "TR": "%.0f" % P.TRACK,
        "GC": "%.0f" % P.GROUND_CLEARANCE,
        "V": "%.2f" % P.V_RATED,
        "FP": "%.0f" % P.F_TRACTIVE_PEAK,
        "SF": "随方案变，见左侧",
        "IP": "%.1f" % P.I_BUS_PEAK,
        "LIM": "%.0f" % P.STEER_LIMIT_DEG,
        "CORNERS": "{" + ", ".join("%s:[%.0f,%.0f]" % (n, x, y) for n, x, y in P.CORNERS) + "}",
    }
    for k, v in fields.items():
        token = "{{%s}}" % k
        assert token in html, "placeholder missing: " + token
        html = html.replace(token, v)
    assert "{{" not in html

    models = json.dumps({n: _uri(n) for n in VARIANTS}, ensure_ascii=False)
    marker = "(function(){"
    assert html.count(marker) == 1
    html = html.replace(marker, "var MODELS = %s;\n%s" % (models, marker))

    art = os.path.join(OUT, "compare_artifact.html")
    with open(art, "w", encoding="utf-8") as fh:
        fh.write(html)

    local = html
    for name, rel in W.LIBS:
        tag = '<script src="%s%s"></script>' % (W.CDN, rel)
        assert tag in local, tag
        local = local.replace(tag, "<script>\n" + W._vendor(name, rel) + "\n</script>")
    local = ('<!doctype html>\n<html lang="zh-CN">\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
             + local + "\n</html>\n")
    off = os.path.join(OUT, "compare_offline.html")
    with open(off, "w", encoding="utf-8") as fh:
        fh.write(local)

    for p in (art, off):
        print("wrote %s  %.1f MB" % (p, os.path.getsize(p) / 1e6))


if __name__ == "__main__":
    main()

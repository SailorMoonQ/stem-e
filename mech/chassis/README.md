# STEM-E 底盘 mechanical

参数化 CAD 源码。设计依据和决策见 `docs/specs/2026-10-06-chassis-design.md`。

```bash
python build.py            # 干涉检查、质量报告、稳定性、STEP/STL/SVG 导出
python drawing.py          # 二维总布置图 A3，PDF/SVG/PNG
python render.py           # 着色渲染
python massprops.py        # 质量与质心明细
python compare_ranger.py   # 与 AgileX Ranger Air 的同工况对比
python error_budget.py     # 四角称重的误差预算
python height_floor.py     # 甲板高度被什么卡住，各条降高路线的代价
python web_export.py       # 交互式 3D 查看器，模型内联进单个 HTML
python compare.py          # 两套电池方案合成一个可切换的查看器

STEM_BATTERY=side python build.py    # 另一套电池方案，输出进 export/side/
```

需要 `cadquery matplotlib pyvista trimesh`。输出全部落在 `export/`，不入版本库。
`viewer.html` 是查看器模板，`{{...}}` 占位符由 `web_export.py` 从 `params` 填入
（填不满会断言失败），所以页面上的数字不会和模型脱节。直接用浏览器打开模板没用，要开 `export/` 下的产物。`web_export.py` 把模型以 base64 内联进页面，产出两份：

- `export/viewer_offline.html` —— 连 three.js 一起内联，双击即可打开，不需要联网
- `export/viewer_artifact.html` —— three.js 走 CDN，用于发布成 Artifact

模型不走 `loader.load()`：Artifact 宿主的 CSP 会拦截对 `data:` URI 的 fetch，
所以页面自己把 base64 解成 ArrayBuffer 再交给 `GLTFLoader.parse()`。

`params.py` 是唯一的几何事实来源。模型、图纸、质量、稳定性校核都从它派生，
所以图上的尺寸不可能和模型脱节。改一个数字重跑三条命令即可。

`build.py` 生成 `export/chassis_params.yaml` 供 `src/description/` 读取，
URDF 不应重复声明这里的几何（见根 CLAUDE.md 不变量 2）。

# luce-svg

A small SVG parser and flattener for Luce/Base. It reads an SVG string (paths,
rects, circles, and group transforms), flattens curves and arcs to polylines,
and produces a `Drawing`: a viewBox size plus contours (fill/stroke/closed) over
a flat point buffer, in viewBox coordinates. Rendering is left to the caller, so
the package depends only on the standard library.

Assets: rounded icons by Dy Mokomi (luciaos-assets), CC BY 4.0.

## Rasteriser and conformance

`rasterize(drawing, width, height, coverage)` fills an 8-bit coverage bitmap with
exact-area anti-aliasing (the signed-area accumulation font rasterisers use):
fills by the nonzero rule, strokes with their width, round caps and joins, dash
patterns, and fill/stroke opacity. luce-ui draws icons through it as tinted masks.

`tools/conformance.py` renders every luciaos-assets icon with resvg and with
`tools/render.lucb` at 256 px, ranks the differences and writes a side-by-side
sheet of the worst (`build/conformance/worst.png`). On 2026-09-22 all 157 icons
were within 0.26 % of resvg's pixels (150 within 0.2 %); synthetic shapes match
their analytic areas to 0.05 %. Needs `brew install resvg` and
`python3 -m venv build/env && build/env/bin/pip install pillow numpy`.

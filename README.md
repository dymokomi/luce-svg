# luce-svg

A small SVG parser, flattener and rasteriser for Luce/Base. It reads an SVG
string (path, rect, circle, ellipse, line, polyline, polygon and nested `g`),
flattens curves and arcs to polylines, and produces a `Drawing`: a viewBox size
plus contours over a flat point buffer, in viewBox coordinates. Each contour
records its element (an element's subpaths fill together by the nonzero rule)
and its paints: fill and stroke as sRGB colors or currentColor, opacities,
stroke width, round caps and joins, and dashes. It depends only on luce-std.

## Paints and colors

`fill`, `stroke`, `fill-opacity`, `stroke-opacity`, `opacity` and the stroke
properties are read from `style="..."` first, then from presentation attributes,
and inherit through groups. Colors are `#rgb`, `#rrggbb`, `rgb(r, g, b)` with
numbers or percentages, and the 148 CSS named colors; paints add `none`,
`transparent`, `inherit` and `currentColor`. SVG's defaults hold: fill black,
stroke none. `opacity` multiplies into both paints of everything inside it (not
as an isolated group layer). Paints the parser cannot draw, such as gradient
`url(...)`s, fall back to black. Contents of `defs`, `clipPath`, `mask`,
`symbol`, `pattern` and `marker` are skipped. `parse_color(text) -> Color?`
parses a color on its own.

`rasterize_rgba(drawing, width, height, pixels, current)` draws in color into
`width * height * 4` floats of straight-alpha RGBA in **linear light**: every
paint is decoded from sRGB before blending, and `current` is the sRGB `Color`
that `currentColor` means. Element by element in document order, the fill and
then the stroke composite source-over, with the same exact-area anti-aliasing
as the coverage rasteriser.

Assets: rounded icons by Dy Mokomi (luciaos-assets), CC BY 4.0.

## Rasteriser and conformance

`rasterize(drawing, width, height, coverage)` fills an 8-bit coverage bitmap with
exact-area anti-aliasing (the signed-area accumulation font rasterisers use):
fills by the nonzero rule, strokes with their width, round caps and joins, dash
patterns, and fill/stroke opacity; it ignores colors. luce-ui draws icons through
it as tinted masks.

`tools/conformance.py` renders every luciaos-assets icon with resvg and with
`tools/render.lucb` at 256 px, ranks the differences and writes a side-by-side
sheet of the worst (`build/conformance/worst.png`). On 2026-09-22 all 157 icons
were within 0.26 % of resvg's pixels (150 within 0.2 %); synthetic shapes match
their analytic areas to 0.05 %. Needs `brew install resvg` and
`python3 -m venv build/env && build/env/bin/pip install pillow numpy`.

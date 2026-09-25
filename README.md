# luce-svg

A small SVG parser, flattener and rasteriser for Luce/Base. It reads an SVG
string (path, rect, circle, ellipse, line, polyline, polygon and nested `g`),
flattens curves and arcs to polylines, and produces a `Drawing`: a viewBox size
plus contours over a flat point buffer, in viewBox coordinates. Each contour
records its element (an element's subpaths fill together by the nonzero rule)
and its paints: fill and stroke as sRGB colors, currentColor or gradients,
opacities, and its pen (width, caps, joins, miter limit, dashes). It depends
only on luce-std.

## Paints and colors

`fill`, `stroke`, `fill-opacity`, `stroke-opacity`, `opacity` and the stroke
properties are read from `style="..."` first, then from presentation attributes,
and inherit through groups. Colors are `#rgb`, `#rrggbb`, `rgb(r, g, b)` with
numbers or percentages, and the 148 CSS named colors; paints add `none`,
`transparent`, `inherit` and `currentColor`. SVG's defaults hold: fill black,
stroke none. `opacity` multiplies into both paints of everything inside it (not
as an isolated group layer). `parse_color(text) -> Color?` parses a color on its
own.

`url(#id)` paints with a `linearGradient` or `radialGradient` found anywhere in
the document: stops with `offset`, `stop-color` and `stop-opacity` (attributes
or style), `gradientUnits` (`objectBoundingBox`, the default, or
`userSpaceOnUse`), `gradientTransform`, `x1 y1 x2 y2`, `cx cy r fx fy`, and
`href`/`xlink:href` inheritance of stops and attributes. Stops blend in sRGB, as
browsers do, before decoding to linear. A missing or stopless gradient paints
the fallback written after the `url(...)`, else nothing.

Strokes are traced as one shape per element under the nonzero rule: a
rectangle per segment, `stroke-linejoin` miter (the default, with
`stroke-miterlimit`, default 4, falling back to bevel), round or bevel at every
vertex, and `stroke-linecap` butt, round or square at open ends.

`rasterize_rgba(drawing, width, height, pixels, current)` draws in color into
`width * height * 4` floats of straight-alpha RGBA in **linear light**: every
paint is decoded from sRGB before blending, and `current` is the sRGB `Color`
that `currentColor` means. Element by element in document order, the fill and
then the stroke composite source-over, with the same exact-area anti-aliasing
as the coverage rasteriser.

## Text

luce-svg has no fonts, so it does not draw `<text>`; it reads it into runs for a
caller that has them (luce-image sets them with luce-fonts). `text_count()` and
`text_run(index) -> TextRun` give each run of one style — the `<text>` itself or
a `<tspan>` — with its characters (entities decoded, white space collapsed as
browsers collapse it), the first value of `x`, `y`, `dx` and `dy`, whether it
opens a `<text>` or starts an anchored chunk, `text-anchor`, the `font-family`
list (`family_count()`, `family(i)`; generics as written), `font-size` (px, pt,
pc, mm, cm, in, em, ex, rem, %, keywords) in the run's own units, `font-weight`,
`font-style`, its fill (color, currentColor, or a gradient's first stop) and
opacity, the `transform` (a `Matrix`) from its coordinates to the viewBox, and
its `order`: how many shape elements paint before it.

To draw text in paint order, clear the pixels, then for each run call
`rasterize_rgba_elements(drawing, width, height, pixels, current, drawn, order)`
for the shapes before it, set the run over them, and finish with the shapes up
to `element_count()`. `pixel_transform(drawing, width, height)` maps the viewBox
onto the bitmap as the rasterisers place it.

## Limits

- Text is read, not drawn (see above); only the first value of `x`, `y`, `dx`
  and `dy` is used, and `rotate`, `textLength`, `textPath`, stroked text,
  `dominant-baseline` and vertical writing are not read.
- Every `spreadMethod` pads (reflect and repeat draw as pad).
- Contents of `defs`, `clipPath`, `mask`, `symbol`, `pattern` and `marker` are
  not drawn; there is no `use`, clipping, masking, pattern paint, filter,
  `fill-rule="evenodd"` or image.
- Group `opacity` fades each paint rather than compositing the group as a layer.
- An unknown color name paints black; `rgba()`, `hsl()` and 4/8-digit hex are
  not read.

Assets: rounded icons by Dy Mokomi (luciaos-assets), CC BY 4.0.

## Rasteriser and conformance

`rasterize(drawing, width, height, coverage)` fills an 8-bit coverage bitmap with
exact-area anti-aliasing (the signed-area accumulation font rasterisers use):
fills by the nonzero rule, strokes with their width, caps, joins and dash
patterns, and fill/stroke opacity; it ignores colors and gradients. luce-ui draws icons through
it as tinted masks.

`tools/conformance.py` renders every luciaos-assets icon with resvg and with
`tools/render.lucb` at 256 px, ranks the differences and writes a side-by-side
sheet of the worst (`build/conformance/worst.png`). On 2026-09-22 all 157 icons
were within 0.26 % of resvg's pixels (150 within 0.2 %); synthetic shapes match
their analytic areas to 0.05 %. Needs `brew install resvg` and
`python3 -m venv build/env && build/env/bin/pip install pillow numpy`.

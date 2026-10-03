# luce-svg

A small SVG parser, flattener and rasteriser for Luce/Base. It reads an SVG
string (path, rect, circle, ellipse, line, polyline, polygon and nested `g`),
flattens curves and arcs to polylines, and produces a `Drawing`: a viewBox size
plus contours over a flat point buffer, in viewBox coordinates. Each contour
records its element (an element's subpaths fill together by the nonzero rule)
and its paints: fill and stroke as sRGB colors, currentColor or gradients,
opacities, and its pen (width, caps, joins, miter limit, dashes). The parser
depends on luce-std and luce-color (sRGB decoding); the picture renderer adds
luce-fonts for text (its platform faces), and the full renderer luce-fonts' font files
and shaping for text and luce-png, luce-jpeg and luce-compress for images.

## The full renderer

`load(source, options) -> interop.Reference[Picture]` reads a whole SVG document the
way resvg (and so, closely, a browser) does, and `render(picture, transform, width,
height, pixels)` draws it into straight-alpha sRGB RGBA bytes (`render_float` gives
floats, encoded or in linear light; `fit_transform` stretches the picture's size over
the bitmap). It is built in four stages, each its own set of fragments:

- **XML** (`xml.lucb`): elements, attributes, text and CDATA, the five predefined
  entities, character references and a DOCTYPE's own `<!ENTITY>`s (which may hold
  markup), namespace prefixes (only SVG, XLink and XML matter), malformed markup an
  error.
- **The SVG tree** (`tree*.lucb`, `css.lucb`): only SVG elements are kept; every
  element's attributes are cascaded from presentation attributes, `<style>` rules
  (type, `*`, `.class`, `#id`, attribute tests, `:first-child`, descendant, child and
  sibling combinators, ordered by specificity, `!important` honoured) and its `style`
  attribute; `inherit` is resolved; `use` gets a copy of its target as its child; text
  white space is collapsed as SVG 1.1 and Chrome do.
- **Conversion** (`convert*.lucb`) into a render tree (`scene.lucb`) of groups, shapes
  and images with every property resolved: lengths in every unit against the nearest
  viewport, `display`, `visibility`, conditional processing (`switch`,
  `systemLanguage`, `requiredFeatures`), `use`/`symbol`/nested `svg` viewports with
  viewBox, preserveAspectRatio and overflow clipping, transforms with
  `transform-origin` (lengths and keywords, as svgtypes reads them), fills and strokes (colors, `currentColor`, gradients with
  fallbacks, `fill-rule`, dashes, caps, joins including `miter-clip`, `paint-order`,
  `shape-rendering`), markers (start, mid and end; orient auto and
  auto-start-reverse, markerUnits, viewBox, refX/refY, overflow clipping) with
  `context-fill` and `context-stroke` (in markers and in `use`), `paint-order`, and
  groups only where one is needed (opacity, blend mode, isolation, clip path, mask,
  filter).
- **Rendering** (`raster.lucb`, `scanline.lucb`, `stroker.lucb`, `canvas.lucb`,
  `shade.lucb`, `render_scene.lucb`): curves flattened to a twentieth of a device
  pixel, coverage from sixteen sub-scanlines a row with exact horizontal spans and true
  nonzero and even-odd winding, strokes built in user space (so a skewed transform
  skews them), gradients with pad, reflect and repeat spreads and two-point conical
  radial gradients (the focal radius `fr` included), group layers composited with
  opacity and all sixteen CSS blend modes, clip paths (nested, with clip-rule) and
  masks (luminance or alpha, nested, with their region). Patterns (with `href`
  inheritance, both unit systems, viewBox and patternTransform) are drawn as a tile at
  the device's scale and repeated, sampled bicubically unless the tile lands on the
  pixel grid, as resvg samples them.
- **Images**: `<image>` from data URLs (base64 or percent-encoded, the format from the
  MIME type or sniffed) or from files relative to `Options.resources` (never from inside
  an image that is itself an SVG); PNG and JPEG decode through luce-png and luce-jpeg,
  SVG and gzip-compressed SVGZ images convert into the picture as vector groups. Fitted
  by preserveAspectRatio (clipped when slicing), sampled as image-rendering asks. GIF
  and WebP are recognised but not decoded.
- **Filters** (`convert_filter.lucb`, `convert_primitive.lucb`, `convert_fe.lucb`,
  `filter_*.lucb`): `filter` lists of `url(#id)` and the CSS filter functions (blur,
  drop-shadow, brightness, contrast, grayscale, hue-rotate, invert, opacity, saturate,
  sepia); filter elements with `href` inheritance, filterUnits and primitiveUnits,
  subregions, named results and color-interpolation-filters (each image converted
  between sRGB and linearRGB as a primitive needs); every primitive resvg renders —
  feBlend, feColorMatrix, feComponentTransfer, feComposite (with arithmetic),
  feConvolveMatrix, feDisplacementMap, feDropShadow, feFlood, feGaussianBlur (box
  blurs for large deviations, a Gaussian kernel for small), feImage (images and
  document elements), feMerge, feMorphology, feOffset, feTile, feTurbulence, and
  feDiffuseLighting and feSpecularLighting with distant, point and spot lights. A
  filtered group is drawn in a layer round its filter regions, up to twice the
  canvas past each side, so offsets and blurs can bring in content from beyond it.
- **Text** (`text_*.lucb`): `<text>`, `<tspan>`, `<tref>`, `<a>` and `<textPath>` laid
  out as usvg lays them: chunks at each absolute x or y, per-character x, y, dx, dy and
  rotate lists, text-anchor, letter-spacing, word-spacing, kerning, textLength with
  lengthAdjust, baseline-shift (lengths, percentages, sub and super),
  dominant-baseline and alignment-baseline, underline, overline and line-through
  painted as the element that asks for them, text along a path (startOffset, glyphs
  turned with the path and hidden past its ends), and each span's fill, stroke and
  paint-order, with bounding-box paint servers measuring the whole text, and vertical
  writing modes (CJK upright, other scripts turned a quarter). Glyphs come from a
  `GlyphSource` — faces chosen by family list, weight, style and stretch, glyphs by
  scalar with a fallback face, advances, pair kerning, metrics and outlines, and
  (optionally) `shape`, which shapes a run of one direction as HarfBuzz does
  (ligatures, marks, contextual forms, small caps); a source that does not shape maps
  a scalar at a time with pair kerning. luce-svg itself splits each chunk into bidi
  runs (UAX #9 for one left-to-right paragraph, `text_bidi.lucb`), shapes the chunk
  per span as usvg does, and forms clusters from the shaped glyphs.
- **Fonts** (`text_font_files.lucb`, `text_font_catalog.lucb`): `FontFiles` is the
  GlyphSource over font files, read and shaped by luce-fonts' `opentype` and
  `shaping` modules (HarfBuzz's default shaper). `FontFiles.system()` catalogues the
  platform's font directories, `FontFiles.open(directories)` the caller's (recursively;
  .ttf, .otf, .ttc and .otc); only each face's small tables are read until its glyphs
  are needed. Families match without regard to case, styles and weights by CSS's
  rules, generic families stand for each platform's usual faces unless
  `set_generic("serif", "Noto Serif")` says otherwise, an uninstalled list falls back
  to serif, and a character a face lacks comes from the first face that has it. Faces
  with bitmap or SVG color glyphs are left out. When `Options.glyphs` is none, `load`
  sets text in `FontFiles.system()` (catalogued once per process, on the first text
  that needs it; conversions that use it take turns); `Options(system_fonts = false)`
  leaves such text undrawn. Arabic joining and Indic reordering need the shaper's
  complex-script shapers, and variable fonts (font-variation-settings), vertical glyph
  substitutes and color fonts need additions to luce-fonts and the source interface.

**Compositing is in sRGB**, as browsers and resvg composite: colors blend as their
encoded values, so half-transparent black over white is 50 % grey. This is the default
of the full renderer only; `RenderOptions(linear = true)` composites in linear light
instead. The Drawing renderer below keeps its linear-light compositing, unchanged for
its callers (luce-image's pictures, luce-vector's tiles).

The value parsers are public so other code can share one spec-correct reading:
`parse_number`, `parse_length` (a `Length` with its `Unit`), `parse_angle`,
`parse_transform_list` (all six functions), `parse_view_box`, `parse_aspect_ratio` and
`view_box_transform`, `parse_path_data` into a `Path` (move, line, cubic, close;
quadratics and arcs become cubics; tight `bounds`), `parse_points`, `iri` and
`func_iri`, and `parse_rgba` (every CSS color: hex in four lengths, the named colors,
`rgb`/`rgba`/`hsl`/`hsla` in both syntaxes, `hwb`, `lab`, `lch`, `oklab`, `oklch` and
`color()` in the predefined spaces, converted with luce-color); `parse_color` reads the
same colors without their alpha.

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

## SVG files as pictures

`svg_render` (module `render`) is what an image editor opening an SVG wants:
`is_svg(path)` and `render_svg(path, max_bytes, max_pixels) -> Rendered`, the
file drawn in color at its own size, scaled up until its longer side is at least
1024 pixels, in linear light with straight alpha (`Rendered.pixels`, 4 floats a
pixel in the heap; free them there), `currentColor` black. Its `<text>` is set
with the system's fonts through luce-fonts, in paint order among the shapes
(`text.lucb`, with faces chosen in `faces.lucb`): a run's family list is tried in
order, generic families stand for each platform's usual faces, and the style
nearest its weight and slant is taken; a run whose font cannot be set is left
out. This moved here from luce-image (2026-09-27).

## Text

The parser reads `<text>` into runs; `svg_render` sets them, and a caller with
its own fonts can too. `text_count()` and
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

## Limits of the Drawing

- The parser only reads text (see above); only the first value of `x`, `y`, `dx`
  and `dy` is used, and `rotate`, `textLength`, `textPath`, stroked text,
  `dominant-baseline` and vertical writing are not read.
- Every `spreadMethod` pads (reflect and repeat draw as pad).
- Contents of `defs`, `clipPath`, `mask`, `symbol`, `pattern` and `marker` are
  not drawn; there is no `use`, clipping, masking, pattern paint, filter,
  `fill-rule="evenodd"` or image.
- Group `opacity` fades each paint rather than compositing the group as a layer.
- In the Drawing, an unknown color name paints black and a color's alpha is dropped.

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

## resvg's test suite

`tools/suite.py` measures the full renderer against resvg's 1719 integration tests
(`crates/resvg/tests/tests` of https://github.com/linebender/resvg, cloned into
`../.donors/resvg`; the suite is never committed here). `tools/suite.lucb` draws
each test 300 pixels wide, as resvg drew its reference PNGs; a pixel differs when a
premultiplied RGBA8 channel is off by more than 40, and a test passes when at most
0.5 % of its pixels differ. That absorbs anti-aliasing differences (tiny-skia samples
four sub-scanlines a pixel, so its edge coverage is off the exact area by up to an
eighth) but not a missing or misplaced feature. It prints a pass table per feature
directory and category; `--save run.json` and `--compare run.json` track changes
between runs, `--list-failing` names the failures, `--only painting/fill` runs a
subset and `--drawing` measures the Drawing renderer.

Baseline (2026-10-03, the Drawing renderer before this work, in linear light): 472 of
1719 — filters 77/397, masking 8/93, paint-servers 99/153, painting 117/306, shapes
91/133, structure 62/258, text 18/379.

The full renderer (2026-10-03): 1308 of 1719 without a GlyphSource — filters 389/397,
masking 88/93, paint-servers 151/153, painting 285/306, shapes 133/133, structure
244/258, text 18/379 (text needs glyphs). With FontFiles over the suite's fonts
(`crates/resvg/tests/fonts`, which `tools/suite.py` passes as `--fonts`, with resvg's
generic families; `--system-fonts` sets text in the system's instead), 2026-10-03:
1671 of 1719 — filters 396, masking 93, paint-servers 152, painting 305, shapes 133,
structure 254, text 338. What still fails: GIF and WebP images (no decoders), `rgba()` with a percentage alpha (read as
CSS Color 4 reads it; resvg rejects it), two transform-precision cases, and text that
needs more of its source than that one gives — Arabic joining and Indic shaping,
variable fonts, color fonts.

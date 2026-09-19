# luce-svg

A small SVG parser and flattener for Luce/Base. It reads an SVG string (paths,
rects, circles, and group transforms), flattens curves and arcs to polylines,
and produces a `Drawing`: a viewBox size plus contours (fill/stroke/closed) over
a flat point buffer, in viewBox coordinates. Rendering is left to the caller, so
the package depends only on the standard library.

Assets: rounded icons by Dy Mokomi (luciaos-assets), CC BY 4.0.

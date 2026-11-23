"""Documented rectilinear crop of a 360-degree (equirectangular) street panorama.

Used when the only open-licensed modern photo of a place is a Panoramax 360 image. The crop is a
derivative work (CC BY-SA 4.0 applies); every parameter is recorded in the pair JSON so the view
can be reproduced. Only the modern photo is ever transformed; historical sheets are never touched.

Conventions: ``pano_az`` is Panoramax ``view:azimuth`` (compass heading of the image centre),
``yaw`` is the compass heading of the crop centre, ``pitch`` > 0 looks up, ``fov`` is horizontal.
"""

from __future__ import annotations

import math
import sys

import cv2
import numpy as np


def rectilinear(img: np.ndarray, pano_az: float, yaw: float, fov: float, size: tuple[int, int],
                pitch: float = 0.0) -> np.ndarray:
    """Pinhole view out of an equirectangular image. ``size`` = (width, height) in pixels."""
    h, w = img.shape[:2]
    out_w, out_h = size
    f = (out_w / 2) / math.tan(math.radians(fov) / 2)
    xs, ys = np.meshgrid(np.arange(out_w) - out_w / 2 + 0.5, np.arange(out_h) - out_h / 2 + 0.5)
    d = np.stack([xs, -ys, np.full_like(xs, f)], -1)
    p = -math.radians(pitch)
    rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    d = d @ rx.T
    a = math.radians(yaw - pano_az)
    x = d[..., 0] * math.cos(a) + d[..., 2] * math.sin(a)
    z = -d[..., 0] * math.sin(a) + d[..., 2] * math.cos(a)
    lon = np.arctan2(x, z)
    lat = np.arctan2(d[..., 1], np.hypot(x, z))
    map_x = ((lon / math.pi) + 1) / 2 * w
    map_y = (0.5 - lat / math.pi) * h
    return cv2.remap(img, map_x.astype(np.float32), map_y.astype(np.float32), cv2.INTER_CUBIC,
                     borderMode=cv2.BORDER_WRAP)


if __name__ == "__main__":
    src, dst, pano_az, yaw, fov, width, height, pitch = sys.argv[1:9]
    image = cv2.imread(src)
    view = rectilinear(image, float(pano_az), float(yaw), float(fov), (int(width), int(height)), float(pitch))
    cv2.imwrite(dst, view, [cv2.IMWRITE_JPEG_QUALITY, 92])

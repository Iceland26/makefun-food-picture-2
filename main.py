#!/usr/bin/env python3
"""food-picture-01: bird-eye procedural ramen bowl (stdlib only, deterministic)."""
import os, zlib, struct, math

W = H = 640

def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)

def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

def smooth(lo, hi, x):
    if hi == lo:
        return 0.0 if x < lo else 1.0
    t = clamp01((x - lo) / (hi - lo))
    return t * t * (3 - 2 * t)

def sd_circle(px, py, cx, cy, r):
    return math.hypot(px - cx, py - cy) - r

def sd_rrect(px, py, cx, cy, hw, hh, rr):
    qx = abs(px - cx) - hw + rr; qy = abs(py - cy) - hh + rr
    ax = max(qx, 0.0); ay = max(qy, 0.0)
    return math.hypot(ax, ay) + min(max(qx, qy), 0.0) - rr

def seg_dist(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    L2 = abx * abx + aby * aby
    t = ((px - ax) * abx + (py - ay) * aby) / L2 if L2 > 0 else 0.0
    t = clamp01(t)
    return math.hypot(px - (ax + abx * t), py - (ay + aby * t))

# --- palette -----------------------------------------------------------
TABLE_A = (0.52, 0.38, 0.26); TABLE_B = (0.30, 0.20, 0.13)
BOWL_RIM = (0.15, 0.13, 0.14); BOWL_IN = (0.21, 0.18, 0.19)
BOWL_LIP = (0.32, 0.28, 0.29)
BROTH_A = (0.93, 0.66, 0.24); BROTH_B = (0.60, 0.32, 0.10)
BROTH_OIL = (1.00, 0.80, 0.34)
NOODLE_A = (0.97, 0.90, 0.66); NOODLE_B = (0.84, 0.70, 0.42)
EGG_W = (0.97, 0.95, 0.87); YOLK_OUT = (0.96, 0.58, 0.10); YOLK_IN = (1.00, 0.78, 0.20)
CHASHU = (0.72, 0.40, 0.26); CHASHU_EDGE = (0.52, 0.26, 0.16); CHASHU_FAT = (0.90, 0.78, 0.66)
NORI = (0.10, 0.13, 0.11); NORI_HI = (0.20, 0.26, 0.22)
ONION_G = (0.26, 0.62, 0.26); ONION_L = (0.55, 0.80, 0.40)

# --- deterministic hash rng -------------------------------------------
def rng(s):
    s = (s * 2654435761 + 0x9e3779b9) & 0xffffffff
    s ^= (s >> 13)
    s = (s * 1274126177) & 0xffffffff
    s ^= (s >> 16)
    return s / 4294967296.0

def render():
    cx = cy = 320.0
    R_bowl = 236.0
    R_broth = 200.0

    # precompute noodle strands: list of polylines (deterministic)
    strands = []
    for k in range(26):
        a0 = rng(k * 7 + 1) * 6.283185
        rr = 55 + 130 * rng(k * 11 + 5)
        pts = []
        x0 = cx + math.cos(a0) * rr
        y0 = cy + math.sin(a0) * rr
        for seg in range(9):
            a1 = a0 + 0.30 + 0.16 * math.sin(seg * 1.3 + k)
            step = 26 + 14 * rng(k * 31 + seg)
            x1 = x0 + math.cos(a1) * step
            y1 = y0 + math.sin(a1) * step
            pts.append((x0, y0, x1, y1))
            x0, y0 = x1, y1
        strands.append(pts)

    # scallion rings (green onions)
    onions = []
    for k in range(46):
        ox = cx + (rng(k * 13 + 3) - 0.5) * 360
        oy = cy + (rng(k * 17 + 9) - 0.5) * 360
        if sd_circle(ox, oy, cx, cy, R_broth) > -10:
            continue
        inner = 2.5 + 4.0 * rng(k * 19 + 4)
        outer = inner + 2.0 + 3.0 * rng(k * 23 + 6)
        tilt = 0.4 + 0.6 * rng(k * 29 + 8)
        onions.append((ox, oy, inner, outer, tilt))

    # oil droplets on broth
    oils = []
    for k in range(34):
        oa = rng(k * 37 + 2) * 6.283185
        orr = 30 + 155 * math.sqrt(rng(k * 41 + 6))
        ox = cx + math.cos(oa) * orr
        oy = cy + math.sin(oa) * orr
        oils.append((ox, oy, 3.0 + 7.0 * rng(k * 43 + 7)))

    rows = []
    for y in range(H):
        py = y + 0.5
        row = bytearray()
        for x in range(W):
            px = x + 0.5
            dcen = math.hypot(px - cx, py - cy)

            # --- wooden table background ---
            grain = math.sin((px * 0.6 + py * 1.7) * 0.03) * 0.5 + 0.5
            bg = mix(TABLE_A, TABLE_B, smooth(0.0, 460.0, dcen) * 0.75 + grain * 0.10)
            col = bg

            # --- bowl shadow on table ---
            dsh = sd_circle(px, py, cx + 6, cy + 9, R_bowl + 4)
            if dsh < 0 and dsh > -22:
                col = mix(col, (0.16, 0.10, 0.06), smooth(0.0, -22.0, dsh) * 0.5)

            dbowl = sd_circle(px, py, cx, cy, R_bowl)
            if dbowl < 0:
                dbroth = sd_circle(px, py, cx, cy, R_broth)
                if dbroth < 0:
                    # --- golden broth ---
                    t = smooth(0.0, R_broth, dcen)
                    col = mix(BROTH_A, BROTH_B, t * 0.85)
                    # soft highlight upper-left
                    hl = sd_circle(px, py, cx - 66, cy - 74, 74)
                    if hl < 0:
                        col = mix(col, (1.0, 0.92, 0.62), smooth(0.0, -74.0, hl) * 0.45)
                    # oil droplets
                    for ox, oy, orad in oils:
                        do = sd_circle(px, py, ox, oy, orad)
                        if do < 0:
                            col = mix(col, BROTH_OIL, smooth(0.0, -orad * 0.7, do) * 0.5)

                    # --- wavy noodles ---
                    for pts in strands:
                        dsum = 1e9
                        for (ax_, ay_, bx_, by_) in pts:
                            d = seg_dist(px, py, ax_, ay_, bx_, by_)
                            if d < dsum:
                                dsum = d
                                if dsum < 3.0:
                                    break
                        if dsum < 5.0:
                            shade = 0.5 + 0.5 * math.sin((px + py) * 0.08)
                            ncol = mix(NOODLE_A, NOODLE_B, shade * 0.5)
                            col = mix(col, ncol, smooth(5.0, 2.4, dsum))

                    # --- two soft-boiled eggs (halves, yolk center) ---
                    for ex, ey, er, rot in ((cx - 84, cy - 82, 50, 0.3), (cx + 78, cy - 62, 50, -0.4)):
                        ca, sa = math.cos(rot), math.sin(rot)
                        rx = (px - ex) * ca + (py - ey) * sa
                        ry = -(px - ex) * sa + (py - ey) * ca
                        dew = math.hypot(rx / 1.12, ry / 0.92) - er
                        if dew < 0:
                            col = mix(col, EGG_W, smooth(0.0, -6.0, dew))
                            dy = math.hypot(rx / 1.05, ry / 0.98) - (er * 0.46)
                            if dy < 0:
                                yin = smooth(-er * 0.30, 0.0, dy)
                                ycol = mix(YOLK_IN, YOLK_OUT, yin)
                                col = mix(col, ycol, smooth(0.0, -8.0, dy))
                                # glossy yolk highlight
                                dgy = math.hypot((rx + 9) / 1.1, (ry + 9) / 1.1) - er * 0.16
                                if dgy < 0:
                                    col = mix(col, (1.0, 0.92, 0.55), smooth(0.0, -6.0, dgy) * 0.6)

                    # --- chashu slices ---
                    for cxu, cyu, ang, hw2, hh2 in ((cx - 26, cy + 74, 0.45, 62, 30),
                                                    (cx + 84, cy + 66, -0.35, 58, 28),
                                                    (cx + 8, cy + 112, 0.15, 54, 26)):
                        c_, s_ = math.cos(ang), math.sin(ang)
                        rx = (px - cxu) * c_ + (py - cyu) * s_
                        ry = -(px - cxu) * s_ + (py - cyu) * c_
                        dc = sd_rrect(rx, ry, 0, 0, hw2, hh2, min(hw2, hh2) * 0.75)
                        if dc < 0:
                            col = mix(col, CHASHU, smooth(0.0, -7.0, dc))
                            # marbled fat streak
                            fat = math.sin(rx * 0.10 + ry * 0.05) + math.sin(ry * 0.14 - 1.1)
                            if fat > 0.85:
                                col = mix(col, CHASHU_FAT, smooth(0.85, 1.6, fat) * 0.55)
                            # darker seared edge
                            if dc > -6.0:
                                col = mix(col, CHASHU_EDGE, smooth(-1.0, -6.0, dc) * 0.55)

                    # --- chopped green onions (ring-shaped) ---
                    for ox, oy, inner, outer, tilt in onions:
                        d = sd_circle(px, py, ox, oy, outer)
                        if d < 0:
                            dcirc = math.hypot(px - ox, (py - oy) / tilt) - inner
                            if dcirc > 0:
                                ring_t = smooth(0.0, 2.5, d)
                                base = mix(ONION_L, ONION_G, rng(int(ox * 7 + oy * 11)) )
                                col = mix(col, base, ring_t * 0.95)

                    # --- nori sheet (standing at back) ---
                    dn = sd_rrect(px, py, cx + 66, cy - 92, 54, 40, 5)
                    if dn < 0:
                        ncol = mix(NORI, NORI_HI, smooth(-40.0, 40.0, (px - (cx + 66)) * 0.5 + (py - (cy - 92)) * 0.3))
                        col = mix(col, ncol, smooth(0.0, -4.0, dn))
                        # subtle nori texture lines
                        if math.sin((px - cx) * 0.5 + (py - cy) * 0.2) > 0.75:
                            col = mix(col, NORI_HI, 0.18)
                else:
                    # --- ceramic rim: dark, glossy lip ---
                    rim_t = smooth(-R_bowl, -R_broth, dbowl)
                    col = mix(BOWL_RIM, BOWL_IN, rim_t)
                    if dbowl > -16:
                        col = mix(col, BOWL_LIP, smooth(-16.0, 0.0, dbowl) * 0.8)
                    # rim specular arc (upper-left, matches broth highlight)
                    ang_p = math.atan2(py - cy, px - cx) % 6.283185
                    spec = smooth(3.55, 3.95, ang_p) * smooth(4.45, 4.05, ang_p)
                    if dbowl > -14 and spec > 0.05:
                        col = mix(col, (0.55, 0.50, 0.50), smooth(-14.0, 0.0, dbowl) * spec * 0.5)

            row += bytes((int(clamp01(col[0]) * 255 + 0.5),
                          int(clamp01(col[1]) * 255 + 0.5),
                          int(clamp01(col[2]) * 255 + 0.5)))
        rows.append(bytes(row))
    return rows

def chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

def write_png(path, rows):
    raw = b''.join(b'\x00' + r for r in rows)
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
           chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)

def main():
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, 'entry.png'), render())

if __name__ == '__main__':
    main()

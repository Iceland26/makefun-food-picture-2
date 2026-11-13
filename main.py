#!/usr/bin/env python3
"""food-picture-01: a warm bowl of ramen, rendered procedurally (stdlib only)."""
import os, zlib, struct, math

W = H = 640

def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)

def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

def smooth(lo, hi, x):
    t = (x - lo) / (hi - lo); t = clamp01(t); return t * t * (3 - 2 * t)

def sd_circle(px, py, cx, cy, r):
    return math.hypot(px - cx, py - cy) - r

def sd_rrect(px, py, cx, cy, hw, hh, rr):
    qx = abs(px - cx) - hw + rr; qy = abs(py - cy) - hh + rr
    ax = max(qx, 0.0); ay = max(qy, 0.0)
    return math.hypot(ax, ay) + min(max(qx, qy), 0.0) - rr

def seg_dist(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay; L2 = abx * abx + aby * aby
    t = ((px - ax) * abx + (py - ay) * aby) / L2 if L2 > 0 else 0.0
    t = clamp01(t)
    return math.hypot(px - (ax + abx * t), py - (ay + aby * t))

BG_A = (0.55, 0.42, 0.30); BG_B = (0.34, 0.24, 0.16)
BOWL_RIM = (0.16, 0.13, 0.12); BOWL_IN = (0.23, 0.19, 0.17)
BROTH_A = (0.87, 0.62, 0.28); BROTH_B = (0.65, 0.38, 0.14)
NOODLE = (0.93, 0.85, 0.60); EGG_W = (0.97, 0.95, 0.88); YOLK = (0.93, 0.50, 0.10)
CHASU = (0.62, 0.30, 0.16); CHASU_EDGE = (0.45, 0.20, 0.10)
NORI = (0.10, 0.14, 0.10); ONION = (0.24, 0.55, 0.22)

def render():
    rows = []; cx = cy = 320.0; R_bowl = 232.0; R_broth = 205.0
    rng = lambda s: (s * 2654435761 % 4294967296) / 4294967296
    for y in range(H):
        py = y + 0.5; row = bytearray()
        for x in range(W):
            px = x + 0.5
            dcen = math.hypot(px - cx, py - cy)
            bg = mix(BG_A, BG_B, smooth(0.0, 480.0, dcen))
            ring = 0.5 + 0.5 * math.sin(dcen * 0.045)
            bg = mix(bg, (bg[0] * 0.96, bg[1] * 0.96, bg[2] * 0.96), ring * 0.06)
            col = bg
            dbowl = sd_circle(px, py, cx, cy, R_bowl)
            if dbowl < 0:
                dbroth = sd_circle(px, py, cx, cy, R_broth)
                if dbroth < 0:
                    t = smooth(0.0, R_broth, math.hypot(px - cx, py - cy))
                    col = mix(BROTH_A, BROTH_B, t)
                    hl = sd_circle(px, py, cx - 70, cy - 70, 60)
                    if hl < 0:
                        col = mix(col, (1.0, 0.90, 0.66), smooth(0.0, -60.0, hl) * 0.55)
                    for k in range(16):
                        a0 = k * 0.39 + 0.1; rr = 40 + 150 * rng(k * 7 + 1)
                        nx0 = cx + math.cos(a0) * rr; ny0 = cy + math.sin(a0) * rr; dsum = 1e9
                        for seg in range(10):
                            a1 = a0 + 0.35 + 0.10 * math.sin(seg * 1.7)
                            nx1 = cx + math.cos(a1) * (rr + (30 if seg % 2 else -18))
                            ny1 = cy + math.sin(a1) * (rr + (26 if seg % 2 else -14))
                            dsum = min(dsum, seg_dist(px, py, nx0, ny0, nx1, ny1))
                            nx0, ny0 = nx1, ny1
                        if dsum < 5.5:
                            col = mix(col, NOODLE, smooth(5.5, 3.2, dsum))
                    for ex, ey in ((cx - 78, cy - 88), (cx + 82, cy - 70)):
                        dew = sd_circle(px, py, ex, ey, 47)
                        if dew < 0:
                            col = mix(col, EGG_W, smooth(0.0, -5.0, dew))
                            dy = sd_circle(px, py, ex, ey, 21)
                            if dy < 0:
                                col = mix(col, YOLK, smooth(0.0, -9.0, dy))
                    for k, (gx, gy, ang) in enumerate(((cx - 96, cy + 78, 0.5), (cx - 10, cy + 108, -0.3), (cx + 86, cy + 92, 0.7))):
                        ca, sa = math.cos(ang), math.sin(ang)
                        rx = (px - gx) * ca + (py - gy) * sa; ry2 = -(px - gx) * sa + (py - gy) * ca
                        dc = sd_rrect(rx, ry2, 0, 0, 58, 26, 11)
                        if dc < 0:
                            col = mix(col, CHASU, smooth(0.0, -6.0, dc))
                            dc2 = sd_rrect(rx, ry2, 0, 0, 58, 26, 10)
                            if dc2 > -5.0:
                                col = mix(col, CHASU_EDGE, smooth(-1.0, -6.0, dc2) * 0.4)
                    for k in range(40):
                        ox = cx + (rng(k * 13 + 3) - 0.5) * 340; oy = cy + (rng(k * 17 + 9) - 0.5) * 340
                        if sd_circle(ox, oy, cx, cy, R_broth) > -6: continue
                        ang = rng(k * 23 + 5) * 6.28; half = 5 + 6 * rng(k * 29 + 7)
                        d = seg_dist(px, py, ox, oy, ox + math.cos(ang) * half, oy + math.sin(ang) * half) - 2.0
                        if d < 0: col = mix(col, ONION, smooth(2.0, -1.0, d))
                    dn = sd_rrect(px, py, cx + 96, cy - 68, 52, 52, 4)
                    if dn < 0: col = mix(col, NORI, smooth(0.0, -4.0, dn))
                else:
                    rim_t = smooth(-R_bowl, -R_broth, dbowl)
                    col = mix(BOWL_RIM, BOWL_IN, rim_t)
                    if dbowl > -14: col = mix(col, (0.30, 0.25, 0.23), smooth(-14.0, 0.0, dbowl))
            dsh = sd_circle(px, py, cx + 8, cy + 10, R_bowl + 6)
            if dsh < 0 and dsh > -18: col = mix(col, (0.22, 0.15, 0.10), smooth(0.0, -18.0, dsh) * 0.45)
            row += bytes((int(clamp01(col[0]) * 255 + 0.5), int(clamp01(col[1]) * 255 + 0.5), int(clamp01(col[2]) * 255 + 0.5)))
        rows.append(bytes(row))
    return rows

def chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

def write_png(path, rows):
    raw = b''.join(b'\x00' + r for r in rows)
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    with open(path, 'wb') as f: f.write(png)

def main():
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, 'entry.png'), render())

if __name__ == '__main__':
    main()
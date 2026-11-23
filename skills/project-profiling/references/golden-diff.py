#!/usr/bin/env python3
"""Compare changed golden / snapshot images with their base version (COMPACT-13).

Usage (from the project root):
  python3 $TEAM_BIN/golden-diff.py --base <rev> [--out <dir>] [--expect-unchanged <glob>]... [--] [paths...]

Without paths, every changed *.png between <rev> and the working tree is compared. For each image it
prints the share of changed pixels, whether the size changed, and the bounding box of the change. Images
are grouped by screen (the file name without its size / theme / scale suffixes); each group gets one
contact sheet in <out> (default .ai-dev-team/workspace/qa-artifacts/golden-diff/) with one row per image:
old | new | changed pixels in red. The reviewer opens every sheet and the full-size pair of each image
the summary flags.

Flags in the summary:
  UNEXPECTED  an image matching --expect-unchanged changed (print layouts, other apps' screens)
  SIZE        the image size changed (layout moved, not only colour or shape)
  OUTLIER     its changed share is far above the median of its group (one state differs from its siblings)
  NEW / GONE  the image did not exist at <rev> / no longer exists

Uses Pillow when the machine has it (fast); otherwise the standard library only (zlib PNG reader and writer,
8-bit and 16-bit non-interlaced PNGs, about a second per phone-sized image).
Exit: 0 nothing flagged, 1 flags found, 64 usage error.
"""
import argparse
import fnmatch
import os
import re
import struct
import subprocess
import sys
import zlib

THUMB = 220
try:
    from PIL import Image, ImageChops
except ImportError:
    Image = None


def read_png(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    pos, idat, plte, trns = 8, [], None, None
    width = height = depth = ctype = interlace = None
    while pos < len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            width, height, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', chunk)
        elif kind == b'PLTE':
            plte = chunk
        elif kind == b'tRNS':
            trns = chunk
        elif kind == b'IDAT':
            idat.append(chunk)
        elif kind == b'IEND':
            break
    if interlace:
        raise ValueError('interlaced PNG')
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    if depth not in (8, 16) and not (ctype == 3 and depth == 8):
        raise ValueError(f'unsupported bit depth {depth}')
    bpp = channels * depth // 8
    stride = width * bpp
    raw = zlib.decompress(b''.join(idat))
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(height):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if f == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                left = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    step = depth // 8
    pixels = []
    for line in rows:
        out = []
        for x in range(width):
            px = [line[x * bpp + k * step] for k in range(channels)]
            if ctype == 0:
                px = [px[0], px[0], px[0], 255]
            elif ctype == 4:
                px = [px[0], px[0], px[0], px[1]]
            elif ctype == 2:
                px = px + [255]
            elif ctype == 3:
                idx = px[0]
                px = list(plte[idx * 3:idx * 3 + 3]) + [trns[idx] if trns and idx < len(trns) else 255]
            out.append(tuple(px))
        pixels.append(out)
    return width, height, pixels


def write_png(path, width, height, rows):
    raw = b''.join(b'\x00' + bytes(v for px in row for v in px) for row in rows)

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)

    with open(path, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                 + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def flatten(px):
    r, g, b, a = px
    return (r * a + 255 * (255 - a)) // 255, (g * a + 255 * (255 - a)) // 255, (b * a + 255 * (255 - a)) // 255


def thumb(img, size=THUMB):
    if img is None:
        return [[(235, 235, 235)] * size for _ in range(size)]
    w, h, px = img
    scale = max(w, h) / size
    out = []
    for y in range(size):
        sy = int(y * scale)
        row = []
        for x in range(size):
            sx = int(x * scale)
            row.append(flatten(px[sy][sx]) if sy < h and sx < w else (235, 235, 235))
        out.append(row)
    return out


def compare(old, new):
    if old is None or new is None:
        return 1.0, None, None
    ow, oh, op = old
    nw, nh, np_ = new
    w, h = max(ow, nw), max(oh, nh)
    changed, box, mask = 0, None, []
    for y in range(h):
        row = []
        for x in range(w):
            a = op[y][x] if y < oh and x < ow else None
            b = np_[y][x] if y < nh and x < nw else None
            diff = a != b
            row.append(diff)
            if diff:
                changed += 1
                box = (min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)) if box else (x, y, x, y)
        mask.append(row)
    return changed / float(w * h), box, (w, h, mask)


def mask_thumb(mask, size=THUMB):
    if mask is None:
        return [[(200, 0, 0)] * size for _ in range(size)]
    w, h, m = mask
    scale = max(w, h) / size
    out = []
    for y in range(size):
        y0, y1 = int(y * scale), max(int((y + 1) * scale), int(y * scale) + 1)
        row = []
        for x in range(size):
            x0, x1 = int(x * scale), max(int((x + 1) * scale), int(x * scale) + 1)
            hit = any(m[yy][xx] for yy in range(y0, min(y1, h)) for xx in range(x0, min(x1, w)))
            row.append((220, 30, 30) if hit else (250, 250, 250))
        out.append(row)
    return out


def pil_load(data):
    import io
    return Image.open(io.BytesIO(data)).convert('RGBA')


def pil_compare(old, new):
    if old is None or new is None:
        return 1.0, None, None
    w, h = max(old.width, new.width), max(old.height, new.height)
    a = Image.new('RGBA', (w, h), (0, 0, 0, 0)); a.paste(old, (0, 0))
    b = Image.new('RGBA', (w, h), (0, 0, 0, 0)); b.paste(new, (0, 0))
    diff = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v else 0)
    return diff.histogram()[255] / float(w * h), diff.getbbox(), diff


def pil_tile(img, mask=False):
    tile = Image.new('RGB', (THUMB, THUMB), (235, 235, 235) if not mask else (250, 250, 250))
    if img is None:
        return Image.new('RGB', (THUMB, THUMB), (200, 0, 0)) if mask else tile
    if mask:
        small = img.resize((max(1, img.width * THUMB // max(img.size)), max(1, img.height * THUMB // max(img.size))), Image.BOX)
        red = small.point(lambda v: 255 if v else 0)
        tile.paste((220, 30, 30), (0, 0), red)
        return tile
    flat = Image.new('RGB', img.size, (255, 255, 255)); flat.paste(img, (0, 0), img)
    flat.thumbnail((THUMB, THUMB))
    tile.paste(flat, (0, 0))
    return tile


def group_of(path):
    name = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r'([_.-](light|dark|\d+x\d+|\d{3,4}|x?\d(\.\d+)?x?|scale[\d.]+|ts[\d.]+|phone|tablet|desktop))+$', '', name, flags=re.I)
    return os.path.join(os.path.dirname(path), name)


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, check=False)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', default='.ai-dev-team/workspace/qa-artifacts/golden-diff')
    ap.add_argument('--expect-unchanged', action='append', default=[])
    ap.add_argument('paths', nargs='*')
    args = ap.parse_args()
    if git('rev-parse', '--verify', '--quiet', args.base).returncode:
        print(f'golden-diff: unknown base {args.base}', file=sys.stderr)
        return 64
    listed = git('diff', '--name-only', args.base, '--', *(args.paths or ['.'])).stdout.decode().split()
    untracked = git('ls-files', '--others', '--exclude-standard', '--', *(args.paths or ['.'])).stdout.decode().split()
    files = sorted({f for f in listed + untracked if f.lower().endswith('.png') and not f.startswith('.ai-dev-team/')})
    os.makedirs(args.out, exist_ok=True)
    results, flagged = {}, 0
    for f in files:
        blob = git('show', f'{args.base}:{f}')
        load = pil_load if Image else read_png
        try:
            old = load(blob.stdout) if blob.returncode == 0 else None
            new = load(open(f, 'rb').read()) if os.path.exists(f) else None
        except (ValueError, KeyError, OSError, zlib.error) as exc:
            print(f'SKIP {f}: {exc}')
            continue
        share, box, mask = (pil_compare if Image else compare)(old, new)
        dims = (lambda i: i.size) if Image else (lambda i: i[:2])
        size = old is not None and new is not None and dims(old) != dims(new)
        results.setdefault(group_of(f), []).append((f, old, new, share, box, mask, size))
    for group, items in sorted(results.items()):
        shares = sorted(i[3] for i in items)
        median = shares[len(shares) // 2]
        rows = []
        for f, old, new, share, box, mask, size in items:
            flags = []
            if old is None:
                flags.append('NEW')
            if new is None:
                flags.append('GONE')
            if any(fnmatch.fnmatch(f, p) for p in args.expect_unchanged):
                flags.append('UNEXPECTED')
            if size:
                flags.append('SIZE')
            if len(items) >= 3 and share > max(3 * median, median + 0.05):
                flags.append('OUTLIER')
            flagged += bool(flags)
            print(f'{share * 100:6.2f}%  {" ".join(flags) or "-":<18} {f}' + (f'  box={box}' if box else ''))
            if Image:
                rows.append([pil_tile(old), pil_tile(new), pil_tile(mask, mask=True)])
            else:
                line = [thumb(old), thumb(new), mask_thumb(mask)]
                for y in range(THUMB):
                    rows.append([px for part in line for px in part[y] + [(255, 255, 255)] * 6])
                rows.extend([[(255, 255, 255)] * (3 * (THUMB + 6))] * 6)
        sheet = os.path.join(args.out, re.sub(r'[^\w.-]+', '_', group.strip('/')) + '.png')
        if Image:
            img = Image.new('RGB', (3 * (THUMB + 6), len(rows) * (THUMB + 6)), (255, 255, 255))
            for r, tiles in enumerate(rows):
                for c, t in enumerate(tiles):
                    img.paste(t, (c * (THUMB + 6), r * (THUMB + 6)))
            img.save(sheet)
        else:
            write_png(sheet, 3 * (THUMB + 6), len(rows), rows)
        print(f'sheet {sheet} ({len(items)} images, median {median * 100:.2f}%)')
    print(f'summary: {sum(len(v) for v in results.values())} images, {len(results)} sheets, {flagged} flagged')
    return 1 if flagged else 0


if __name__ == '__main__':
    sys.exit(main())

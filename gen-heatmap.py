import glob
import os
import shutil
import subprocess
import xml.etree.ElementTree as et

HeatmapPath = 'heatmap'
shutil.rmtree(HeatmapPath, ignore_errors=True)
os.mkdir(HeatmapPath)

total_strokes = 0
errors = 0
keys = {} # [layer][row][col]
max_strokes = 0

def get_heatmap_path(name_):
    return os.path.join(HeatmapPath, name_)

def add(layer_id, row, col):
    global max_strokes
    try:
        layer = keys[layer_id]
    except KeyError:
        layer = keys[layer_id] = {}
    try:
        row_entry = layer[row]
    except KeyError:
        row_entry = layer[row] = {}
    try:
        row_entry[col] += 1
    except KeyError:
        row_entry[col] = 1

    if row_entry[col] > max_strokes:
        max_strokes = row_entry[col]

files = glob.glob('*_log.txt')
for file_ in files:
    with open(file_, 'rt') as f:
        for line in f:
            if not line.endswith('\n'):
                continue
            try:
                ts, marker, layer_id, col, row, pressed, keycode, time_ = line.rstrip().split(' ')
                assert marker == 'C:'
                if pressed == '1':
                    add(int(layer_id), int(row), int(col))
                    total_strokes += 1
            except ValueError:
                print("ERROR:", line)
                errors += 1

def get_svg_filename(layer_id):
    return f"heatmap_{layer_id}.svg"

for layer_id in sorted(keys):
    layer = keys[layer_id]
    et.register_namespace('', "http://www.w3.org/2000/svg")
    tree = et.parse('ergodox.svg')
    root = tree.getroot()

    for rect in root.findall(".//{http://www.w3.org/2000/svg}rect"):
        row = int(rect.attrib['data-row'])
        col = int(rect.attrib['data-col'])
        try:
            strokes = layer[row][col]
        except KeyError:
            strokes = 0
        hotness = strokes / max_strokes # [0..1]
        r = hotness * (217 - 65) + 65
        g = (1.0 - hotness) * (130 - 30) + 30
        b = (1.0 - hotness) * (215 - 24) + 24
        rgb = '#%s' % ''.join(f'{int(i):02x}' for i in [r, g, b])
        rect.attrib['fill'] = rgb

    with open(get_heatmap_path(get_svg_filename(layer_id)), 'wt') as f:
        print(et.tostring(root, encoding='utf8').decode('utf8'), file=f)

with open(get_heatmap_path('index.html'), 'wt') as f:
    print("""<html><head><title>ErgodoxEZ Heatmap</title>
<style>
table {
  border: 1px solid;
}
th {
  border-bottom: 1px solid;
}
</style>
</head>
<body>""", file=f)

    print(f"""<table>
    <tr>
        <th>Layer</th>
        <th>Keystrokes</th>
    </tr>
""", file=f)
    for layer_id in sorted(keys):
        layer = keys[layer_id]
        layer_strokes = sum([ sum(row.values()) for row in layer.values() ])
        print(f"""
        <tr>
            <td>{layer_id}</td>
            <td>{layer_strokes}</td>
        </tr>""", file=f)

    print(f"""
    <tr>
        <td>All</td>
        <td>{total_strokes}</td>
    </tr>
    <tr>
        <td>Errors</td>
        <td>{errors}</td>
    </tr>
</table>""", file=f)

    for layer_id in sorted(keys):
        print(f"""<h1>Layer {layer_id}</h1><img src="{get_svg_filename(layer_id)}"/>""", file=f)
    print("""</body>
</html>""", file=f)

import pathlib
path = pathlib.Path(__file__).parent.resolve()

subprocess.run([r'c:\Program Files\Mozilla Firefox\firefox.exe', 'file://%s/heatmap/index.html' % path])

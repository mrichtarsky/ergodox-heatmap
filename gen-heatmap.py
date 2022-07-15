from datetime import date, timedelta
import glob
import os
import platform
import shutil
import subprocess
import xml.etree.ElementTree as et

NUM_LAST_DAYS = None
WINDOWS_BROWSER = 'c:/Program Files/Mozilla Firefox/firefox.exe'
MACOS_BROWSER = 'Firefox'

LAYER_NAMES = (
    'Base',
    'LED',
    'Media',
    'SymbolsR',
    'SymbolsL',
    'Editing',
    'NumBlock',
    'VSCode',
    'Caps',
    'Umlaute',
    'QWERTY',
    'Fn Keys',
)

HeatmapPath = 'heatmap'
shutil.rmtree(HeatmapPath, ignore_errors=True)
os.mkdir(HeatmapPath)

Days = {}

total_strokes = 0
errors = 0
keys = {} # [layer][row][col]
max_strokes = 0

def get_heatmap_path(name_):
    return os.path.join(HeatmapPath, name_)

def add(layer_id, row, col, day):
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

    try:
        Days[day] += 1
    except:
        Days[day] = 1

files = glob.glob('logs/*_log.txt')
for file_ in files:
    with open(file_, 'rt') as f:
        for line in f:
            if not line.endswith('\n'):
                continue
            try:
                ts, marker, layer_id, col, row, pressed, keycode = line.rstrip().split(' ')[:7]
                assert marker == 'C:'
                day = date.fromtimestamp(float(ts))
                if NUM_LAST_DAYS is not None and date.today() - day > timedelta(days=NUM_LAST_DAYS):
                    continue
                if pressed == '1':
                    add(int(layer_id), int(row), int(col), day)
                    total_strokes += 1
            except ValueError:
                print("ERROR:", file_, line)
                errors += 1

def get_svg_filename(layer_id, type_):
    return f"heatmap_{layer_id}_{type_}.svg"

def gen_heatmap(layer, max_strokes, out_file):
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

    with open(get_heatmap_path(out_file), 'wt') as f:
        print(et.tostring(root, encoding='utf8').decode('utf8'), file=f)

for layer_id in sorted(keys):
    layer = keys[layer_id]
    gen_heatmap(layer, max_strokes, get_svg_filename(layer_id, 'global'))
    max_layer_strokes = max([ max(row.values()) for row in layer.values() ])
    gen_heatmap(layer, max_layer_strokes, get_svg_filename(layer_id, 'local'))

with open(get_heatmap_path('index.html'), 'wt') as f:
    print("""<html><head><title>ErgodoxEZ Heatmap</title>
<style>
table {
  border: 1px solid;
  padding: 2px;
  margin: 2px;
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
            <td>{layer_strokes:,}</td>
        </tr>""", file=f)

    print(f"""
    <tr>
        <td>All</td>
        <td>{total_strokes:,}</td>
    </tr>
    <tr>
        <td>Errors</td>
        <td>{errors}</td>
    </tr>
</table>""", file=f)

    print('<table><tr><th>Date</th><th>Keystrokes</th></tr>', file=f)
    for day in sorted(Days.keys(), reverse=True)[:7]:
        print(f"<tr><td>{day}</td><td>{Days[day]:,}</td></tr>", file=f)
    print('</table>', file=f)
    topDay = sorted(Days.items(), key=lambda elem: elem[1])[-1]
    print(f"Day with most key strokes: {topDay[0]} ({topDay[1]:,})<br/>", file=f)
    for layer_id in sorted(keys):
        print(f"""<h1>Layer {layer_id} - {LAYER_NAMES[layer_id]}</h1>
    <img src="{get_svg_filename(layer_id, 'global')}"/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    <img src="{get_svg_filename(layer_id, 'local')}"/>
""", file=f)
    print("""</div>
</body>
</html>""", file=f)

import pathlib
path = pathlib.Path(__file__).parent.resolve()

match platform.system():
    case 'Darwin':
        subprocess.run(['open', '-a', MACOS_BROWSER, 'heatmap/index.html'])
    case 'Windows':
        subprocess.run([WINDOWS_BROWSER, 'file://%s/heatmap/index.html' % path])

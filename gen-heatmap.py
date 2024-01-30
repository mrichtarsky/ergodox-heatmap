from datetime import date, timedelta
import glob
import os
import pickle
import platform
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as et

NUM_LAST_DAYS = None
WINDOWS_BROWSER = 'c:/Program Files/Mozilla Firefox/firefox.exe'
MACOS_BROWSER = 'Firefox'
SUMMARIZE_AFTER_NUM_DAYS = 30

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

HEATMAP_PATH = 'heatmap'
shutil.rmtree(HEATMAP_PATH, ignore_errors=True)
os.mkdir(HEATMAP_PATH)

def get_host(file_):
    return file_.split('/')[-1].split('_')[0]

class KeyData:
    def __init__(self, from_file=None):
        self.keys = {} # [layer][row][col]
        self.days = {}
        self.total_strokes = 0
        self.strokes_per_host = {}
        self.errors = 0
        self.max_strokes = 0
        self.strokes_per_host_today = {}

        if from_file is not None:
            with open(from_file, 'rb') as f:
                self.keys, self.days, self.total_strokes, self.errors, self.max_strokes = pickle.load(f)
                self.strokes_per_host[get_host(from_file)] = self.total_strokes

    def save(self, file_):
        data = self.keys, self.days, self.total_strokes, self.errors, self.max_strokes
        with open(file_, 'wb') as f:
            pickle.dump(data, f)

    def _calculate_max_strokes(self):
        max_strokes = 0
        for rows in self.keys.values():
            for cols in rows.values():
                for strokes in cols.values():
                    if strokes > max_strokes:
                        max_strokes = strokes
        return max_strokes

    def merge(self, other):
        for other_layer, other_rows in other.keys.items():
            try:
                rows = self.keys[other_layer]
            except KeyError:
                self.keys[other_layer] = other_rows
                continue
            for other_row, other_cols in other_rows.items():
                try:
                    cols = rows[other_row]
                except KeyError:
                    rows[other_row] = other_cols
                    continue
                for other_col, other_value in other_cols.items():
                    try:
                        cols[other_col] += other_value
                    except KeyError:
                        cols[other_col] = other_value
        for other_day, other_strokes in other.days.items():
            try:
                self.days[other_day] += other_strokes
            except KeyError:
                self.days[other_day] = other_strokes
        self.total_strokes += other.total_strokes
        for otherHost, otherStrokes in other.strokes_per_host.items():
            try:
                self.strokes_per_host[otherHost] += otherStrokes
            except KeyError:
                self.strokes_per_host[otherHost] = otherStrokes
        for otherHost, otherStrokesToday in other.strokes_per_host_today.items():
            try:
                self.strokes_per_host_today[otherHost] += otherStrokesToday
            except KeyError:
                self.strokes_per_host_today[otherHost] = otherStrokesToday

        self.errors += other.errors
        self.max_strokes = self._calculate_max_strokes()

class KeylogParser:
    def __init__(self, file_, num_last_days=None):
        self.file_ = file_
        self.num_last_days = num_last_days
        self.key_data = KeyData()
        self._read()

    def _add(self, host, layer_id, row, col, day):
        layer = self.key_data.keys.setdefault(layer_id, {})
        row_entry = layer.setdefault(row, {})
        try:
            row_entry[col] += 1
        except KeyError:
            row_entry[col] = 1

        if row_entry[col] > self.key_data.max_strokes:
            self.key_data.max_strokes = row_entry[col]

        try:
            self.key_data.days[day] += 1
        except:
            self.key_data.days[day] = 1

        self.key_data.total_strokes += 1
        try:
            self.key_data.strokes_per_host[host] += 1
        except KeyError:
            self.key_data.strokes_per_host[host] = 1

        if day == date.today():
            try:
                self.key_data.strokes_per_host_today[host] += 1
            except:
                self.key_data.strokes_per_host_today[host] = 1

    def _read(self):
        host = get_host(self.file_)
        with open(self.file_, 'rt') as f:
            prevSig = None
            for line in f:
                if not line.endswith('\n'):
                    continue
                try:
                    ts, marker, layer_id, col, row, pressed, keycode = line.rstrip().split(' ')[:7]
                    # Dedup duplicate lines on macOS, maybe due to Karabiner
                    sig = (layer_id, col, row, pressed, keycode)
                    if sig == prevSig:
                        continue
                    else:
                        prevSig = sig
                    assert marker == 'C:', (line, self.file_)
                    day = date.fromtimestamp(float(ts))
                    if self.num_last_days is not None and date.today() - day > timedelta(days=self.num_last_days):
                        continue
                    if pressed == '1':
                        self._add(host, int(layer_id), int(row), int(col), day)
                except ValueError:
                    print("ERROR:", self.file_, line)
                    self.key_data.errors += 1

    def writeSummary(self, file_):
        self.key_data.save(file_)

def get_heatmap_path(name_):
    return os.path.join(HEATMAP_PATH, name_)

def read_data():
    all_data = KeyData()

    archived_files = glob.glob('logs/*_log_*.txt')
    for archived_file in archived_files:
        timestamp = re.search(r'''_log_(\d+).txt''', archived_file).group(1)
        kp = KeylogParser(archived_file)
        if time.time() - float(timestamp) > SUMMARIZE_AFTER_NUM_DAYS*60*60*24:
            print('Summarizing', archived_file)
            kp.writeSummary(archived_file + '.summary')
            os.unlink(archived_file)
        else:
            print('Adding', archived_file)
            all_data.merge(kp.key_data)

    summaries = glob.glob('logs/*.summary')
    for summary in summaries:
        print('Adding', summary)
        summary_kd = KeyData(summary)
        all_data.merge(summary_kd)

    files = glob.glob('logs/*_log.txt')
    for file_ in files:
        print('Adding', file_)
        kp = KeylogParser(file_)
        all_data.merge(kp.key_data)

    return all_data

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

def get_charts():
    if platform.system() == 'Darwin':
        return '', ''

    import pandas as pd
    import plotly.graph_objs as go
    all_data_days_sorted = sorted(all_data.days.items(), key=lambda item: item[0])
    days_sorted, strokes_sorted = zip(*all_data_days_sorted)

    df = pd.DataFrame(data={'days': days_sorted,
                            'strokes': strokes_sorted})
    df['MA_mean'] = df['strokes'].rolling(7).mean()
    df['MA_max'] = df['strokes'].rolling(30).max()
    df.dropna(inplace=True)

    def get_chart(title, xvalues, yvalues):
        data = (go.Scatter(
            x=xvalues,
            y=yvalues,
        ))

        layout = go.Layout(
            yaxis={ 'title': 'Strokes', },
            title=title
        )

        fig = go.Figure(data=data, layout=layout)
        chart_html = fig.to_html(include_plotlyjs=True, default_width=600, default_height=300)
        return chart_html

    mean_over_days_chart = get_chart('Keystrokes per day (7 days rolling mean)', df['days'], df['MA_mean'])
    max_over_days_chart = get_chart('Max keystrokes per day (30 days rolling max)', df['days'], df['MA_max'])

    return mean_over_days_chart, max_over_days_chart

def write_heatmaps(all_data):
    for layer_id in sorted(all_data.keys):
        layer = all_data.keys[layer_id]
        gen_heatmap(layer, all_data.max_strokes, get_svg_filename(layer_id, 'global'))
        max_layer_strokes = max([ max(row.values()) for row in layer.values() ])
        gen_heatmap(layer, max_layer_strokes, get_svg_filename(layer_id, 'local'))

def write_html(all_data, mean_over_days_chart, max_over_days_chart):
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

        print("""<table>
        <tr>
            <th>Layer</th>
            <th>Keystrokes</th>
        </tr>
    """, file=f)
        for layer_id in sorted(all_data.keys):
            layer = all_data.keys[layer_id]
            layer_strokes = sum([ sum(row.values()) for row in layer.values() ])
            print(f"""
            <tr>
                <td>{layer_id}</td>
                <td>{layer_strokes:,}</td>
            </tr>""", file=f)

        print(f"""
        <tr>
            <td>All</td>
            <td>{all_data.total_strokes:,}</td>
        </tr>
        <tr>
            <td>Errors</td>
            <td>{all_data.errors}</td>
        </tr>
    </table>""", file=f)

        print('<table><tr><th>Date</th><th>Keystrokes</th></tr>', file=f)
        for day in sorted(all_data.days.keys(), reverse=True)[:7]:
            print(f"<tr><td>{day}</td><td>{all_data.days[day]:,}</td></tr>", file=f)
        print('</table>', file=f)

        print('<table><tr><th>Date</th><th>Keystrokes Today</th></tr>', file=f)
        for host in all_data.strokes_per_host_today.keys():
            print(f"<tr><td>{host}</td><td>{all_data.strokes_per_host_today[host]:,}</td></tr>", file=f)
        print('</table>', file=f)

        print('<table><tr><th>Host</th><th>Keystrokes</th></tr>', file=f)
        for host, strokes in all_data.strokes_per_host.items():
            print(f"<tr><td>{host}</td><td>{strokes:,}</td></tr>", file=f)
        print('</table>', file=f)

        topDay = sorted(all_data.days.items(), key=lambda elem: elem[1])[-1]
        print(f"Day with most key strokes: {topDay[0]} ({topDay[1]:,})<br/>", file=f)

        print(mean_over_days_chart, file=f)
        print(max_over_days_chart, file=f)

        for layer_id in sorted(all_data.keys):
            print(f"""<h1>Layer {layer_id} - {LAYER_NAMES[layer_id]}</h1>
        <img src="{get_svg_filename(layer_id, 'global')}"/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        <img src="{get_svg_filename(layer_id, 'local')}"/>
    """, file=f)
        print("""</div>
    </body>
    </html>""", file=f)

def show_in_browser():
    import pathlib
    path = pathlib.Path(__file__).parent.resolve()

    system = platform.system()
    if system == 'Darwin':
        subprocess.run(['open', '-a', MACOS_BROWSER, 'heatmap/index.html'])
    elif system == 'Windows':
        subprocess.run([WINDOWS_BROWSER, 'file://%s/heatmap/index.html' % path])
    else:
        raise Exception("Unsupported platform")


all_data = read_data()
mean_over_days_chart, max_over_days_chart = get_charts()
write_heatmaps(all_data )
write_html(all_data, mean_over_days_chart, max_over_days_chart)
show_in_browser()

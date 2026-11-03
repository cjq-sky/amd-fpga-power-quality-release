"""Pillow 1280x720 renderer for immutable 14 UI snapshots; no hardware access."""
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache
from pathlib import Path
import math
import numpy as np
from display_snapshot import finite

PAGES = ('overview', 'waveform', 'events', 'harmonics')
TITLES = ('监测总览', '双通道波形', '事件记录', '谐波与模型')
MODEL_TITLES = ('低目标谐波', '三次谐波主导', '五次谐波主导', '混合奇次谐波')
EVENTS = dict(DISABLED='未启用', WARMUP='预热', NORMAL='正常', SAG='暂降', SWELL='暂升',
              INTERRUPTION='短时中断', ERROR='停止：数据无效', STALE='数据陈旧')
VOLTS_PER_CODE = 10 / 32768


def harmonic_values(state, channel):
    metrics = state.get('metrics', {}) if state.get('status') == 'LIVE' else {}
    h1 = metrics.get(channel + '_H1')
    values = []
    for n in (3, 5, 7, 9):
        hn = metrics.get(channel + '_H' + str(n))
        values.append(hn / h1 * 100 if finite(hn) and finite(h1) and h1 > 0 else None)
    return values + [metrics.get(channel + '_THD_ODD_3_5_7_9'), metrics.get(channel + '_CREST')]


class Renderer:
    def __init__(self, font_path, latin_font_path=None):
        if latin_font_path is None:
            installed = Path('/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf')
            latin_font_path = installed if installed.is_file() else font_path
        self.font_path, self.latin_font_path = str(font_path), str(latin_font_path)
        self.fonts = {n: ImageFont.truetype(str(font_path), n) for n in (17, 19, 21, 24, 28, 34, 40)}
        self.latin_fonts = {n: ImageFont.truetype(str(latin_font_path), n) for n in self.fonts}

    def runs(self, value, size):
        value = value.replace('—', '--').replace('–', '-')
        runs = []
        for char in value:
            font = self.latin_fonts[size] if ord(char) < 256 else self.fonts[size]
            if runs and runs[-1][1] is font:
                runs[-1] = (runs[-1][0] + char, font)
            else:
                runs.append((char, font))
        return runs

    @lru_cache(maxsize=512)
    def text_width(self, value, size):
        return sum(font.getlength(run) for run, font in self.runs(value, size))

    @lru_cache(maxsize=512)
    def text_tile(self, value, size, color):
        baseline = self.fonts[size].getmetrics()[0]
        positioned = []
        cursor = 0
        for run, font in self.runs(value, size):
            box = font.getbbox(run, anchor='ls')
            positioned.append((run, font, cursor, (cursor+box[0], baseline+box[1], cursor+box[2], baseline+box[3])))
            cursor += font.getlength(run)
        if not positioned:
            return Image.new('RGBA', (1,1)), 0, 0
        left = math.floor(min(p[3][0] for p in positioned))
        top = math.floor(min(p[3][1] for p in positioned))
        right = math.ceil(max(p[3][2] for p in positioned))
        bottom = math.ceil(max(p[3][3] for p in positioned))
        tile = Image.new('RGBA', (max(1,right-left), max(1,bottom-top)))
        draw = ImageDraw.Draw(tile)
        for run, font, x, box in positioned:
            draw.text((x-left, baseline-top), run, font=font, fill=color, anchor='ls')
        return tile, left, top

    def render(self, snapshot, page, *, now=None):
        if page not in PAGES:
            raise ValueError('Unknown view')
        s = snapshot.view(now=now)
        im = Image.new('RGB', (1280, 720), '#edf3f8')
        d = ImageDraw.Draw(im)
        ink, blue, muted = '#1f3553', '#1768b3', '#5d7187'
        def text(x, y, value, size=24, color=ink):
            tile, dx, dy = self.text_tile(str(value), size, color)
            im.paste(tile, (x + dx, y + dy), tile)
        def wrap(x, y, value, width, size=21, lines=3, color=ink):
            current, used = '', 0
            for ch in str(value):
                if self.text_width(current + ch, size) > width:
                    text(x, y + used * (size + 8), current, size, color)
                    used += 1; current = ''
                    if used >= lines:
                        return
                current += ch
            if current:
                text(x, y + used * (size + 8), current, size, color)
        def card(x, y, right, bottom):
            d.rounded_rectangle((x, y, right, bottom), radius=15, fill='white', outline='#cbdbea', width=2)
        def number(value, decimals=3):
            return f'{value:.{decimals}f}' if finite(value) else '—'
        text(28, 19, '电能质量监测', 34, blue)
        text(330, 28, TITLES[PAGES.index(page)], 24)
        source_label = s['snapshot_source_note'].replace(' · 手动更新', '')
        text(790, 27, source_label, 21, blue)
        text(30, 67, 'ADC 输入端电压 · ±10 V 名义量程 · 未校准', 19, muted)
        archived = '存档' in s['snapshot_source_note'] or '静态' in s['snapshot_source_note']
        status_label = '存档静态验证' if archived else str(s.get('status', 'WAITING'))
        text(940, 67, '快照状态：' + status_label, 19, muted)
        wave_identity = s.get('waveform') or {}
        text(30, 96, 'Feature F' + str(s.get('frame_id', '—')) + ' / Raw F'
             + str(wave_identity.get('frame_id', '—')) + ' · '
             + ('MATCHED' if wave_identity.get('association') == 'MATCHED' else 'UNMATCHED')
             + ' · 快照 ' + str(s.get('shared_snapshot_id', '—')), 17, muted)
        metrics = s.get('metrics', {}) if s.get('status') == 'LIVE' else {}
        event = s.get('event') or {}
        if page == 'overview':
            for i, ch in enumerate(('CH1', 'CH2')):
                x = 28 + i * 626
                card(x, 120, x + 598, 524)
                text(x + 22, 138, ch + ' 监测指标', 28, blue)
                for j, (field, label, unit) in enumerate((('RMS', '有效电压', 'V'), ('PEAK', '峰值电压', 'V'),
                        ('FREQUENCY_MHZ', '频率', 'Hz'), ('THD_ODD_3_5_7_9', '奇次谐波 THD', '%'), ('CREST', '波峰因数', ''))):
                    value = metrics.get(ch + '_' + field)
                    if ch == 'CH2' and field == 'FREQUENCY_MHZ':
                        value = None
                    if finite(value) and field in ('RMS', 'PEAK'):
                        value *= VOLTS_PER_CODE
                    y = 202 + j * 59
                    text(x + 22, y, label, 24)
                    text(x + 295, y - 4, number(value), 34, blue)
                    text(x + 520, y + 8, unit, 19, muted)
            card(28, 542, 1252, 610)
            text(48, 561, 'CH1事件：' + EVENTS.get(event.get('status'), '未知'), 21)
            ch2 = (event.get('channels') or {}).get('CH2') or {}
            text(345, 561, 'CH2事件：' + EVENTS.get(ch2.get('status'), '未知'), 21)
            model = (s.get('harmonic') or {}).get('physical_model') or {}
            label = MODEL_TITLES[model['class_id']] if s['model_display_valid'] else '—'
            text(670, 561, 'CH1候选分类：' + label, 21, blue)
        elif page == 'waveform':
            wave = s.get('waveform') or {}
            association = wave.get('association', 'UNKNOWN')
            text(30, 112, 'Raw / Feature：' + ('同帧匹配' if association == 'MATCHED' else '未匹配，各自独立显示'), 19, muted)
            for i, ch in enumerate(('CH1', 'CH2')):
                top = 145 + i * 232
                card(28, top, 1252, top + 218)
                values = wave.get(ch)
                usable = (wave.get('status') == 'LIVE' and isinstance(values, list) and len(values) == 2048
                          and all(type(v) is int and -32768 <= v <= 32767 for v in values))
                text(48, top + 10, ch + ' · 输入电压波形', 24, blue)
                if not usable:
                    text(60, top + 85, 'Raw 无效或陈旧，不显示旧波形', 24, muted)
                    continue
                lo, hi = min(values), max(values)
                text(435, top + 15, number(lo * VOLTS_PER_CODE) + ' ～ ' + number(hi * VOLTS_PER_CODE) + ' V · 独立纵轴', 19, muted)
                x0, x1, y0, y1 = 65, 1220, top + 55, top + 174
                for j in range(5):
                    y = y0 + (y1 - y0) * j / 4
                    d.line((x0, y, x1, y), fill='#e1ebf3')
                span = hi - lo
                points = [(x0 + k * (x1 - x0) / 2047,
                           (y0 + y1) / 2 if span == 0 else y1 - (v - lo) * (y1 - y0) / span)
                          for k, v in enumerate(values)]
                d.line(points, fill=blue if i == 0 else '#8b66bf', width=2)
                fs = wave.get('fs_nominal_hz')
                duration = 2047 / fs * 1000 if finite(fs) and fs > 0 else None
                text(65, top + 183, '0 ms', 17, muted)
                text(1050, top + 183, number(duration, 1) + ' ms', 17, muted)
        elif page == 'events':
            for i, ch in enumerate(('CH1', 'CH2')):
                e = event if i == 0 else (event.get('channels') or {}).get('CH2') or {}
                x = 28 + i * 626
                card(x, 120, x + 598, 610)
                text(x + 22, 137, ch + ' 独立事件检测', 28, blue)
                text(x + 22, 190, EVENTS.get(e.get('status'), '未知'), 34, blue)
                usable = e.get('status') in ('WARMUP', 'NORMAL', 'SAG', 'SWELL', 'INTERRUPTION')
                text(x + 22, 245, '当前有效值：' + number(e.get('rms_pu') if usable else None) + ' pu', 24)
                base = e.get('nominal_rms_code')
                text(x + 22, 285, '参考电压：' + number(base * VOLTS_PER_CODE if finite(base) else None) + ' V', 21, muted)
                active = e.get('active') if usable else None
                wrap(x + 22, 327, '活动事件：' + (' → '.join(active.get('states', [])) if active else '无可显示的活动事件'), 552, lines=2)
                records = [v for v in e.get('records', []) if v.get('record') == 'event'][-3:]
                if not records:
                    text(x + 22, 415, '暂无已结束事件', 24, muted)
                for j, rec in enumerate(records):
                    label = EVENTS.get(rec.get('type'), rec.get('type', '未知'))
                    wrap(x + 22, 408 + j * 52, label + ' · ' + ('完整' if rec.get('complete') else '不完整')
                         + ' · ' + number(rec.get('duration')) + ' s · ' + ('来源有效' if rec.get('source_valid') else '来源无效'), 552, size=19, lines=2)
                wrap(x + 22, 568, e.get('reason') or '', 552, size=17, lines=1, color=muted)
        else:
            h = s.get('harmonic') or {}; m = h.get('physical_model') or {}
            card(28, 120, 626, 610); card(650, 120, 1252, 610)
            for i, ch in enumerate(('CH1', 'CH2')):
                top = 140 + i * 215
                text(50, top, ch + ' · 谐波结果', 28, blue)
                values = harmonic_values(s, ch)
                for j, label in enumerate(('H3/H1', 'H5/H1', 'H7/H1', 'H9/H1', '奇次THD', '峰值因数')):
                    x = 50 + (j % 2) * 280
                    y = top + 55 + (j // 2) * 44
                    text(x, y, label, 21)
                    text(x + 110, y, number(values[j]), 24, blue)
                    text(x + 225, y + 3, '' if j == 5 else '%', 17, muted)
            text(50, 577, '比值由有效Feature派生；无效基波显示 —', 17, muted)
            text(672, 140, 'CH1 · 模型识别', 28, blue)
            algorithm = {'logistic_regression': '逻辑回归（LR）', 'random_forest': '随机森林（RF）'}.get(m.get('algorithm'), '—')
            text(672, 194, '算法：' + algorithm, 24)
            valid = s['model_display_valid']
            text(672, 246, MODEL_TITLES[m['class_id']] if valid else '候选分类 —', 34, blue)
            text(672, 309, '模型概率（未校准）', 21, muted)
            for j, label in enumerate(MODEL_TITLES):
                y = 350 + j * 43
                value = m['probabilities'][j] * 100 if valid else None
                text(672, y, label, 21)
                text(1080, y, number(value, 2) + ' %', 21, blue)
            text(672, 548, '候选模型 · TRAINING_ONLY', 21, muted)
            text(672, 580, '仅供工程验证，不用于正式告警', 19, muted)
        for i, title in enumerate(TITLES):
            x = 28 + i * 313
            d.rounded_rectangle((x, 638, x + 285, 703), radius=13,
                                fill=blue if PAGES[i] == page else 'white', outline='#cbdbea', width=2)
            text(x + 36, 655, title, 24, 'white' if PAGES[i] == page else ink)
        return im

    def bgr(self, snapshot, page, *, now=None):
        return np.asarray(self.render(snapshot, page, now=now), dtype='u1')[:, :, ::-1].copy()

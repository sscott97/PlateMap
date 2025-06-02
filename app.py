# Flask application to generate formatted sample IDs and plate layouts
from flask import Flask, render_template, request
import os

app = Flask(__name__)

def format_id(entry, prefix, suffix='', id_length=0, pad_char='0'):
    entry = entry.strip()
    if not entry:
        return None
    if entry.startswith('!'):
        return entry[1:]  # Raw ID, skip formatting

    # Pad only the numeric part of the ID if id_length is set
    if id_length > 0:
        entry = entry.zfill(id_length) if pad_char == '0' else entry.rjust(id_length, pad_char)
    return f"{prefix}{entry}{suffix}"



def build_grid(sample_ids, replicate_count, layout_mode,
               pos_label='PosCtrl', neg_label='NegCtrl', ctrl3_label='Ctrl3',
               include_pos=True, include_neg=True, include_ctrl3=True):
    grid = [["" for _ in range(12)] for _ in range(8)]

    if layout_mode == 'vertical':
        fill_positions = []
        control_labels = []
        if include_pos:
            control_labels += [pos_label] * replicate_count
        if include_neg:
            control_labels += [neg_label] * replicate_count
        if include_ctrl3:
            control_labels += [ctrl3_label] * replicate_count

        # Place controls in leftmost columns, wrapping down rows
        control_col = 0
        control_row = 0
        for label in control_labels:
            if control_row >= 8:
                control_row = 0
                control_col += 1
                if control_col >= 12:
                    break  # no more room
            grid[control_row][control_col] = label
            control_row += 1

        # Prepare list of empty cells to place samples (skip occupied ones)
        for col in range(12):
            for row in range(8):
                if grid[row][col] == "":
                    fill_positions.append((row, col))

        # Fill sample replicates
        idx = 0
        for sid in sample_ids:
            for _ in range(replicate_count):
                if idx >= len(fill_positions):
                    break
                r, c = fill_positions[idx]
                grid[r][c] = sid
                idx += 1


    elif layout_mode == 'horizontal':
        current_row = 0
        col = 0

        if include_pos:
            for rep in range(replicate_count):
                grid[current_row][col + rep] = pos_label
            current_row += 1
        if include_neg:
            for rep in range(replicate_count):
                grid[current_row][col + rep] = neg_label
            current_row += 1
        if include_ctrl3:
            for rep in range(replicate_count):
                grid[current_row][col + rep] = ctrl3_label
            current_row += 1

        sample_idx = 0
        while sample_idx < len(sample_ids):
            if current_row >= 8:
                current_row = 0
                col += replicate_count
                if col + replicate_count > 12:
                    break

            for rep in range(replicate_count):
                if col + rep < 12:
                    grid[current_row][col + rep] = sample_ids[sample_idx]
            current_row += 1
            sample_idx += 1

    return grid

@app.route('/', methods=['GET', 'POST'])
def index():
    default_prefix = '837S'
    default_suffix = ''
    default_pos = 'KIOVIG'
    default_neg = 'Negative'
    default_ctrl3 = ''

    if request.method == 'POST':
        prefix = request.form.get('prefix', default_prefix).strip()
        suffix = request.form.get('suffix', default_suffix).strip()
        pos_label = request.form.get('pos_label', '').strip()
        neg_label = request.form.get('neg_label', '').strip()
        ctrl3_label = request.form.get('ctrl3_label', '').strip()

        if not pos_label:
            pos_label = "Control 1"
        if not neg_label:
            neg_label = "Control 2"
        if not ctrl3_label:
            ctrl3_label = "Control 3"


        include_pos = 'include_pos' in request.form
        include_neg = 'include_neg' in request.form
        include_ctrl3 = 'include_ctrl3' in request.form

        try:
            replicate_count = int(request.form.get('replicate_count', 2))
        except ValueError:
            replicate_count = 2

        try:
            id_length = int(request.form.get('id_length', 0))
        except ValueError:
            id_length = 0
        pad_char = request.form.get('pad_char', '0')[:1] or '0'

        layout_mode = request.form.get('layout_mode', 'vertical')

        try:
            plate_count = int(request.form.get('plate_count', 1))
        except ValueError:
            plate_count = 1

        plates = []
        for i in range(1, plate_count + 1):
            raw = request.form.get(f'plate_{i}', '')
            nums = [s.strip() for s in raw.replace(';', ',').split(',') if s.strip()]
            formatted = [
                format_id(n, prefix, suffix, id_length, pad_char)
                for n in nums
                if format_id(n, prefix, suffix, id_length, pad_char)
            ]

            plates.append(build_grid(
                formatted, replicate_count, layout_mode,
                pos_label, neg_label, ctrl3_label,
                include_pos, include_neg, include_ctrl3
            ))

        return render_template('results.html', plates=plates)

    return render_template('index.html', prefix=default_prefix, suffix=default_suffix,
                           pos_label=default_pos, neg_label=default_neg, ctrl3_label=default_ctrl3)

@app.route('/settings', methods=['GET'])
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
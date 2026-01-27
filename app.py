from flask import Flask, render_template, request, jsonify
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Database connection
def get_db_connection():
    """Get database connection using DATABASE_URL from environment"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Render provides postgres:// but psycopg2 needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return psycopg2.connect(database_url)
    return None

def init_db():
    """Initialize database table if it doesn't exist"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS presets (
                    name TEXT PRIMARY KEY,
                    settings JSONB NOT NULL
                )
            ''')
            conn.commit()
            cur.close()
            conn.close()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
            if conn:
                conn.close()

# Initialize database when module loads
init_db()

# -----------------------
# Preset storage helpers
# -----------------------
def load_presets():
    """Load all presets from database"""
    conn = get_db_connection()
    if not conn:
        print("No database connection available")
        return {}
    
    try:
        # Try to initialize the table first if it doesn't exist
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS presets (
                name TEXT PRIMARY KEY,
                settings JSONB NOT NULL
            )
        ''')
        conn.commit()
        cur.close()
        
        # Now load the presets
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT name, settings FROM presets')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to dict format
        presets = {}
        for row in rows:
            presets[row['name']] = row['settings']
        return presets
    except Exception as e:
        print(f"Error loading presets: {e}")
        if conn:
            conn.close()
        return {}

def save_preset(name, settings):
    """Save or update a preset in database"""
    conn = get_db_connection()
    if not conn:
        print("No database connection available")
        return False
    
    try:
        cur = conn.cursor()
        # Ensure table exists
        cur.execute('''
            CREATE TABLE IF NOT EXISTS presets (
                name TEXT PRIMARY KEY,
                settings JSONB NOT NULL
            )
        ''')
        conn.commit()
        
        # Insert or update preset
        cur.execute('''
            INSERT INTO presets (name, settings)
            VALUES (%s, %s)
            ON CONFLICT (name) 
            DO UPDATE SET settings = EXCLUDED.settings
        ''', (name, json.dumps(settings)))
        conn.commit()
        cur.close()
        conn.close()
        print(f"Preset '{name}' saved successfully")
        return True
    except Exception as e:
        print(f"Error saving preset: {e}")
        if conn:
            conn.close()
        return False

def delete_preset(name):
    """Delete a preset from database"""
    conn = get_db_connection()
    if not conn:
        print("No database connection available")
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM presets WHERE name = %s', (name,))
        deleted = cur.rowcount > 0
        conn.commit()
        cur.close()
        conn.close()
        print(f"Preset '{name}' deleted: {deleted}")
        return deleted
    except Exception as e:
        print(f"Error deleting preset: {e}")
        if conn:
            conn.close()
        return False


# -----------------------
# Plate building helpers
# -----------------------
def format_id(entry, prefix, suffix='', id_length=0, pad_char='0'):
    # Don't strip entry — allow spaces as valid input
    if not entry or entry.strip() == "":
        return None  # handle completely empty strings
    
    # Check if entry starts with '!' - if so, bypass all formatting
    if entry.startswith('!'):
        return entry[1:]  # Return the entry without the '!' and without any formatting
    
    # Apply zero-padding (or other padding)
    if id_length > 0:
        entry = entry.zfill(id_length) if pad_char == '0' else entry.rjust(id_length, pad_char)

    # Keep spaces in prefix and suffix as typed
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
        control_col = 0
        control_row = 0
        for label in control_labels:
            if control_row >= 8:
                control_row = 0
                control_col += 1
                if control_col >= 12:
                    break
            grid[control_row][control_col] = label
            control_row += 1
        for col in range(12):
            for row in range(8):
                if grid[row][col] == "":
                    fill_positions.append((row, col))
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


# -----------------------
# Flask routes
# -----------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    default_prefix = ''
    default_suffix = ''
    default_pos = ''
    default_neg = ''
    default_ctrl3 = ''
    if request.method == 'POST':
        prefix = request.form.get('prefix', default_prefix)
        suffix = request.form.get('suffix', default_suffix)
        pos_label = request.form.get('pos_label', '').strip() or "Control 1"
        neg_label = request.form.get('neg_label', '').strip() or "Control 2"
        ctrl3_label = request.form.get('ctrl3_label', '').strip() or "Control 3"
        include_pos = 'include_pos' in request.form
        include_neg = 'include_neg' in request.form
        include_ctrl3 = 'include_ctrl3' in request.form
        replicate_count = int(request.form.get('replicate_count', 2))
        id_length = int(request.form.get('id_length', 0))
        pad_char = request.form.get('pad_char', '0')[:1] or '0'
        layout_mode = request.form.get('layout_mode', 'vertical')
        plate_count = int(request.form.get('plate_count', 1))
        plate_labels = []
        for i in range(1, plate_count + 1):
            label = request.form.get(f'plate_label_{i}', '').strip()
            if not label:
                label = f"Plate {i}"
            plate_labels.append(label)
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
        return render_template('results.html', plates=plates, plate_labels=plate_labels)
    return render_template('index.html', prefix=default_prefix, suffix=default_suffix,
                           pos_label=default_pos, neg_label=default_neg, ctrl3_label=default_ctrl3)


@app.route('/settings')
def settings():
    return render_template('settings.html')


# -----------------------
# API endpoints for presets
# -----------------------
@app.route('/api/presets', methods=['GET'])
def api_get_presets():
    return jsonify(load_presets())

@app.route('/api/presets', methods=['POST'])
def api_save_preset():
    data = request.json
    if not data or "name" not in data or "settings" not in data:
        return jsonify({"error": "Invalid data"}), 400
    
    if save_preset(data["name"], data["settings"]):
        return jsonify({"message": f'Preset "{data["name"]}" saved.'})
    else:
        return jsonify({"error": "Failed to save preset"}), 500

@app.route('/api/presets/<name>', methods=['DELETE'])
def api_delete_preset(name):
    if delete_preset(name):
        return jsonify({"message": f'Preset "{name}" deleted.'})
    return jsonify({"error": "Preset not found"}), 404


# -----------------------
# Main
# -----------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
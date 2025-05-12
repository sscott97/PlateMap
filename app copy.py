# Procfile (root)
web: gunicorn app:app

# app.py
from flask import Flask, render_template, request
PREFIX = "837S"

app = Flask(__name__)

# Utility to format IDs
def format_id(num):
    try:
        n = int(num)
    except ValueError:
        return None
    return f"{PREFIX}{n:04d}"

# Build an 8x12 grid for one plate
def build_grid(sample_ids):
    grid = [["" for _ in range(12)] for _ in range(8)]
    # Column 0 controls + first samples
    grid[0][0] = grid[1][0] = "PosCtrl"
    grid[2][0] = grid[3][0] = "NegCtrl"
    if len(sample_ids) > 0:
        grid[4][0] = grid[5][0] = sample_ids[0]
    if len(sample_ids) > 1:
        grid[6][0] = grid[7][0] = sample_ids[1]
    # Remaining samples
    for col in range(1, 12):
        for i in range(4):
            idx = 2 + (col-1)*4 + i
            if idx < len(sample_ids):
                sid = sample_ids[idx]
                r = i * 2
                grid[r][col] = grid[r+1][col] = sid
    return grid

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Number of plates
        try:
            plate_count = int(request.form.get('plate_count', 1))
        except ValueError:
            plate_count = 1
        plates = []
        # Process each plate's input
        for i in range(1, plate_count+1):
            raw = request.form.get(f'plate_{i}', '')
            nums = [s.strip() for s in raw.replace(';',',').split(',') if s.strip()]
            formatted = [format_id(n) for n in nums if format_id(n)]
            plates.append(build_grid(formatted))
        return render_template('results.html', plates=plates)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

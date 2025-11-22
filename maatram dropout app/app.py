
from flask import Flask, render_template, request, redirect, url_for, jsonify
import csv
import os
from datetime import datetime

app = Flask(__name__)
DATA_FILE = os.path.join('data', 'students.csv')

# Ensure data folder and file exist
os.makedirs('data', exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id','name','academic','parent_income','family_size','motivation','behavior','score','risk','reason','created_at'])

# --- Scoring logic (simple, explainable) ---
# Weights: academic 30%, socio-economic 30%, motivation 20%, behavior 20%
def compute_score_and_reason(record):
    # Inputs expected as numbers or categories mapped to numbers
    # record: dict with keys: academic, parent_income, family_size, motivation, behavior
    # academic: percentage 0-100
    # parent_income: integer monthly income in INR (lower income increases deservingness but may increase dropout risk due to finances)
    # family_size: integer
    # motivation: 1-5 (1 low - 5 high)
    # behavior: 1-3 (1 weak, 2 average, 3 good)

    # Convert inputs safely
    try:
        academic = float(record.get('academic', 0))
    except:
        academic = 0.0
    try:
        parent_income = float(record.get('parent_income', 0))
    except:
        parent_income = 0.0
    try:
        family_size = int(record.get('family_size', 1))
    except:
        family_size = 1
    try:
        motivation = float(record.get('motivation', 3))
    except:
        motivation = 3.0
    try:
        behavior = float(record.get('behavior', 2))
    except:
        behavior = 2.0

    # Normalize socio-economic: construct socio_score where lower income and larger family means more need but also potential risk.
    # We'll create two subcomponents: need_score (higher is more deserving) and stability_score (higher is more stable)
    # need_score (0-100): lower income & larger family -> higher need_score
    # simple formula:
    income_cap = max(parent_income, 1)
    need_score = max(0, 100 - (income_cap / 20000.0) * 100)  # income 20k -> need_score 0; income 0 -> 100
    # adjust for family size
    need_score = min(100, need_score + (family_size - 1) * 5)

    # stability_score (0-100): higher income and smaller family -> higher stability
    stability_score = min(100, (income_cap / 20000.0) * 100)
    stability_score = max(0, stability_score - (family_size - 1) * 3)

    # Now compute weighted components
    academic_comp = max(0, min(100, academic))  # 0-100
    socio_comp = (need_score * 0.6 + stability_score * 0.4)  # keep 0-100
    motivation_comp = max(0, min(100, (motivation / 5.0) * 100))
    behavior_comp = max(0, min(100, (behavior / 3.0) * 100))

    # Weights
    w_academic = 0.30
    w_socio = 0.30
    w_motivation = 0.20
    w_behavior = 0.20

    # Retention/Deservingness score (0-100). Higher = more deserving & higher likelihood to retain
    score = (academic_comp * w_academic +
             socio_comp * w_socio +
             motivation_comp * w_motivation +
             behavior_comp * w_behavior)

    # Determine risk buckets from score (simple thresholds)
    if score >= 70:
        risk = 'Low Risk'
    elif score >= 45:
        risk = 'Medium Risk'
    else:
        risk = 'High Risk'

    # Build explainable reason string: list top contributors to risk (low/high)
    reasons = []
    if academic_comp < 50:
        reasons.append('Weak academic performance')
    if motivation_comp < 50:
        reasons.append('Low motivation')
    if behavior_comp < 50:
        reasons.append('Behavior concerns')
    # socio: if stability low, mark financial instability that increases dropout risk
    if stability_score < 30:
        reasons.append('Financial instability')
    # if need_score high but stability low, suggest deserving but at risk
    if need_score > 70 and stability_score < 40:
        reasons.append('High financial need (deserving) but unstable resources')

    if not reasons:
        reasons = ['No major concerns found']

    reason_text = ' + '.join(reasons)
    return round(score, 2), risk, reason_text

# --- CSV helpers ---
def append_student_to_csv(row):
    # row is a dict containing keys matching header
    with open(DATA_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            row.get('id'),
            row.get('name'),
            row.get('academic'),
            row.get('parent_income'),
            row.get('family_size'),
            row.get('motivation'),
            row.get('behavior'),
            row.get('score'),
            row.get('risk'),
            row.get('reason'),
            row.get('created_at')
        ])

def read_all_students():
    students = []
    with open(DATA_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            students.append(r)
    return students

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    # Get form data
    name = request.form.get('name', 'Unknown')
    academic = request.form.get('academic', '0')
    parent_income = request.form.get('parent_income', '0')
    family_size = request.form.get('family_size', '1')
    motivation = request.form.get('motivation', '3')
    behavior = request.form.get('behavior', '2')

    record = {
        'academic': academic,
        'parent_income': parent_income,
        'family_size': family_size,
        'motivation': motivation,
        'behavior': behavior
    }
    score, risk, reason = compute_score_and_reason(record)

    # Prepare row and append to CSV
    student_id = int(datetime.utcnow().timestamp())  # simple unique id
    row = {
        'id': student_id,
        'name': name,
        'academic': academic,
        'parent_income': parent_income,
        'family_size': family_size,
        'motivation': motivation,
        'behavior': behavior,
        'score': score,
        'risk': risk,
        'reason': reason,
        'created_at': datetime.utcnow().isoformat()
    }
    append_student_to_csv(row)
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# API endpoint to fetch students as JSON for dashboard
@app.route('/api/students')
def api_students():
    students = read_all_students()
    # Convert numeric fields to numbers for client
    for s in students:
        try:
            s['score'] = float(s.get('score', 0))
        except:
            s['score'] = 0.0
    return jsonify(students)

if __name__ == '__main__':
    app.run(debug=True)

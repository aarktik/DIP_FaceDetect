import os
import sqlite3
import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from core import process_image

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'history.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_filename TEXT,
            processed_filename TEXT,
            total_faces INTEGER,
            male_count INTEGER,
            female_count INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Prevent collisions
        base, ext = os.path.splitext(filename)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        safe_filename = f"{base}_{timestamp_str}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(filepath)

        try:
            # Process via core.py
            processed_filename, count, male_count, female_count = process_image(filepath, app.config['UPLOAD_FOLDER'])
            
            # Save to history
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                INSERT INTO usage_history (original_filename, processed_filename, total_faces, male_count, female_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (safe_filename, processed_filename, count, male_count, female_count))
            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'original_image': f'/uploads/{safe_filename}',
                'processed_image': f'/uploads/{processed_filename}',
                'total_faces': count,
                'male_count': male_count,
                'female_count': female_count
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM usage_history ORDER BY timestamp DESC LIMIT 50')
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'id': row['id'],
            'original_image': f"/uploads/{row['original_filename']}",
            'processed_image': f"/uploads/{row['processed_filename']}",
            'total_faces': row['total_faces'],
            'male_count': row['male_count'],
            'female_count': row['female_count'],
            'timestamp': row['timestamp']
        })
    return jsonify(history)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/history/<int:item_id>', methods=['DELETE'])
def delete_history(item_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM usage_history WHERE id = ?', (item_id,))
        conn.commit()
        
        changes = conn.total_changes
        conn.close()
        
        if changes > 0:
            return jsonify({'success': True, 'message': 'ลบข้อมูลสำเร็จ'})
        else:
            return jsonify({'success': False, 'error': 'ไม่พบประวัติที่ต้องการลบ'}), 404
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Listen on all generic interfaces to allow LAN connections
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=True, port=port)

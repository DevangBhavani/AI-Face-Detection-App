import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from models import db, DetectionLog

# 1. Setup Flask App
# The frontend static files are located in the folder parallel to backend
frontend_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
app = Flask(__name__, static_folder=frontend_folder, static_url_path='')
CORS(app)

# 2. Database Configuration
# Using SQLite for a beginner-friendly setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///detections.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create the database and tables if they don't exist
with app.app_context():
    db.create_all()

# 3. Load Haar Cascade
# This model file is used by OpenCV to detect frontal human faces
cascade_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cascades', 'haarcascade_frontalface_default.xml')
# If the file doesn't exist, this will fail or raise a warning, ensure it's downloaded
face_cascade = cv2.CascadeClassifier(cascade_path)

# 4. Routes for Serving Frontend File
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# 5. API Endpoint for Webcam Frame Processing
@app.route('/api/detect_frame', methods=['POST'])
def detect_frame():
    """
    Receives a single frame from the webcam via JS as a Base64 string.
    Returns the bounding box coordinates of any detected faces.
    """
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400
    
    # Process Base64 image
    image_data = data['image']
    try:
        header, encoded = image_data.split(",", 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'error': 'Invalid image data'}), 400

    if img is None:
        return jsonify({'error': 'Failed to decode image'}), 400

    # Convert to grayscale for Haar Cascade
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    # scaleFactor=1.1, minNeighbors=5, minSize=(30, 30) are standard values
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    boxes = []
    for (x, y, w, h) in faces:
        boxes.append({'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)})

    return jsonify({'faces': boxes, 'count': len(faces)})

# 6. API Endpoint for Image Upload Processing
@app.route('/api/detect_upload', methods=['POST'])
def detect_upload():
    """
    Receives an uploaded image file.
    Draws bounding boxes around detected faces on the backend.
    Returns the marked image as a Base64 string.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image file uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'error': 'Invalid image file'}), 400

    if img is None:
        return jsonify({'error': 'Failed to decode image file'}), 400

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Draw rectangles on the original image
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 3)

    # Encode the processed image back to base64 to send to frontend
    success, buffer = cv2.imencode('.jpg', img)
    if not success:
        return jsonify({'error': 'Failed to encode processed image'}), 500
        
    encoded_img = base64.b64encode(buffer).decode('utf-8')

    # Log to Database
    log = DetectionLog(source_type='upload', faces_detected=len(faces))
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'image': f'data:image/jpeg;base64,{encoded_img}',
        'count': len(faces)
    })

# 7. API Endpoint to fetch detection logs
@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Returns the last 50 detection logs from the database."""
    logs = DetectionLog.query.order_by(DetectionLog.timestamp.desc()).limit(50).all()
    return jsonify([log.to_dict() for log in logs])

if __name__ == '__main__':
    # Run the server
    app.run(host='0.0.0.0', port=5000, debug=True)

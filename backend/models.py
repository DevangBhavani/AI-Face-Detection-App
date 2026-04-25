from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class DetectionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(50), nullable=False) # 'webcam' or 'upload'
    faces_detected = db.Column(db.Integer, nullable=False, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'source_type': self.source_type,
            'faces_detected': self.faces_detected,
            'timestamp': self.timestamp.isoformat()
        }

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    sr_id = db.Column(db.String(20), unique=True, nullable=False) # SR00001 형식
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    requester = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected
    created_at = db.Column(db.DateTime, default=datetime.now)
    approved_at = db.Column(db.DateTime)
    approver = db.Column(db.String(100))
    evidence_log = db.Column(db.Text)

    @staticmethod
    def generate_sr_id():
        """SRxxxxx 형식의 자동 번호 생성"""
        last_sr = ServiceRequest.query.order_by(ServiceRequest.id.desc()).first()
        if not last_sr:
            return 'SR00001'
        
        # 마지막 ID에서 숫자 추출 후 1 증가
        try:
            last_number = int(last_sr.sr_id[2:])
            new_number = last_number + 1
            return f'SR{new_number:05d}'
        except (ValueError, IndexError):
            return 'SR00001'

    def to_dict(self):
        return {
            'sr_id': self.sr_id,
            'title': self.title,
            'requester': self.requester,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

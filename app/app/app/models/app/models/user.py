from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum
import secrets

class Role(enum.Enum):
    ADMIN = 'admin'
    AGENT = 'agent'
    CLIENT = 'client'
    DEVELOPER = 'developer'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.Enum(Role), default=Role.CLIENT)
    is_active = db.Column(db.Boolean, default=True)
    api_token = db.Column(db.String(64), unique=True)
    sms_limit = db.Column(db.Integer, default=100)
    sms_used = db.Column(db.Integer, default=0)
    payout = db.Column(db.Float, default=0.0)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    phone = db.Column(db.String(20))
    company = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    clients = db.relationship('User', backref=db.backref('agent', remote_side=[id]), lazy='dynamic')
    sms_numbers = db.relationship('SMSNumber', backref='assigned_to', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def generate_api_token(self):
        self.api_token = secrets.token_urlsafe(32)
        db.session.commit()
        return self.api_token
        
    def is_admin(self):
        return self.role == Role.ADMIN
        
    def is_agent(self):
        return self.role == Role.AGENT
        
    def is_client(self):
        return self.role == Role.CLIENT
        
    def is_developer(self):
        return self.role == Role.DEVELOPER
        
    def has_permission(self, required_role):
        hierarchy = {Role.ADMIN: 4, Role.AGENT: 3, Role.CLIENT: 2, Role.DEVELOPER: 1}
        return hierarchy.get(self.role, 0) >= hierarchy.get(required_role, 0)
        
    def get_sms_stats(self):
        from app.models.sms import SMSCDR
        total_sent = SMSCDR.query.filter_by(user_id=self.id).count()
        total_delivered = SMSCDR.query.filter_by(user_id=self.id, status='delivered').count()
        return {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'limit': self.sms_limit,
            'remaining': max(0, self.sms_limit - self.sms_used)
        }
        
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'is_active': self.is_active,
            'sms_limit': self.sms_limit,
            'sms_used': self.sms_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

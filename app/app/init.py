from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.session_protection = "strong"

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login_manager.init_app(app)
    
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.developer import developer_bp
    from app.routes.sms_monitor import monitor_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(developer_bp, url_prefix='/developer')
    app.register_blueprint(monitor_bp, url_prefix='/monitor')
    
    register_error_handlers(app)
    
    with app.app_context():
        db.create_all()
        create_default_data()
        
    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return db.session.get(User, int(user_id))

def create_default_data():
    from app.models.user import User, Role
    from app.models.sms import SMSRange, SMSNumber
    from app.models.activity import News
    
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@alrosy.com', role=Role.ADMIN, is_active=True)
        admin.set_password('admin123')
        db.session.add(admin)
        
        agent = User(username='agent1', email='agent1@alrosy.com', role=Role.AGENT, is_active=True)
        agent.set_password('agent123')
        db.session.add(agent)
        
        client = User(username='client1', email='client1@alrosy.com', role=Role.CLIENT, is_active=True)
        client.set_password('client123')
        db.session.add(client)
        
        db.session.commit()
    
    if not SMSRange.query.first():
        ranges = [
            SMSRange(name='USA Local', country='United States', prefix='+1', total_numbers=1000, price=0.05),
            SMSRange(name='UK Mobile', country='United Kingdom', prefix='+44', total_numbers=500, price=0.08),
            SMSRange(name='UAE Premium', country='UAE', prefix='+971', total_numbers=300, price=0.10),
            SMSRange(name='KSA VIP', country='Saudi Arabia', prefix='+966', total_numbers=200, price=0.12),
        ]
        for r in ranges:
            db.session.add(r)
        db.session.commit()
    
    if not News.query.first():
        news = News(title='Welcome to ALROSY SMS Panel', content='System is now live and operational.', is_published=True)
        db.session.add(news)
        db.session.commit()

def register_error_handlers(app):
    from flask import render_template
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

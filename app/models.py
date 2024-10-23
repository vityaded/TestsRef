from . import db
from flask_login import UserMixin
from datetime import datetime, timezone
from sqlalchemy.dialects.sqlite import JSON  # Use JSON type for SQLite

class User(UserMixin, db.Model):
    __tablename__ = 'user'  # Explicitly specify table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    test_results = db.relationship('TestResult', backref='user', lazy=True, cascade='all, delete-orphan')
    tests_created = db.relationship('Test', backref='creator', lazy=True, cascade='all, delete-orphan')
    vocabulary = db.relationship('Vocabulary', backref='user', lazy=True, cascade='all, delete-orphan')
    learn_test_results = db.relationship('LearnTestResult', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)

class Book(db.Model):
    __tablename__ = 'book'  # Explicitly specify table name
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    tests = db.relationship(
        'Test',
        backref='book',
        lazy=True,
        cascade='all, delete-orphan'
    )

class Test(db.Model):
    __tablename__ = 'test'  # Explicitly specify table name
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    time_limit = db.Column(db.Integer, nullable=True)  # Time limit in minutes
    shuffle_sentences = db.Column(db.Boolean, default=False)
    shuffle_paragraphs = db.Column(db.Boolean, default=False)
    test_results = db.relationship('TestResult', backref='test', lazy=True, cascade='all, delete-orphan')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_results = db.relationship(
        'TestResult',
        backref='test',
        lazy=True,
        cascade='all, delete-orphan'
    )
    learn_test_results = db.relationship(
        'LearnTestResult',
        backref='test',
        lazy=True,
        cascade='all, delete-orphan'
    )

class TestResult(db.Model):
    __tablename__ = 'test_result'  # Explicitly specify table name
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)

class Vocabulary(db.Model):
    __tablename__ = 'vocabulary'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(150), nullable=False)
    translation = db.Column(db.String(150), nullable=False)
    pronunciation_url = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    next_review = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    interval = db.Column(db.Float, nullable=False, default=0)  # Interval in days
    ease_factor = db.Column(db.Float, nullable=False, default=2.5)  # Default ease factor
    learning_stage = db.Column(db.Integer, nullable=False, default=0)  # 0: New, 1: First Step, etc.

class LearnTestResult(db.Model):
    __tablename__ = 'learn_test_result'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class LearnTestProgress(db.Model):
    __tablename__ = 'learn_test_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    answers = db.Column(db.PickleType, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('learn_progress', lazy='dynamic'))
    test = db.relationship('Test', backref=db.backref('learn_progress', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'test_id', name='_user_test_uc'),)
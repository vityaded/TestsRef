from . import db
from flask_login import UserMixin
from datetime import datetime, timezone
import hashlib
import hmac
# Import JSON type based on your database (using SQLite's here)
from sqlalchemy.dialects.sqlite import JSON
# Or use db.JSON if using PostgreSQL/MySQL:
# from sqlalchemy import JSON as db_JSON

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
    # Relationship added in previous step, ensure cascade is correct if User deleted
    # reading_progress is defined via backref in UserReadingProgress

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash, generate_password_hash

        stored_password = self.password or ""

        if stored_password.startswith('sha256$'):
            try:
                _, salt, hashval = stored_password.split('$', 2)
            except ValueError:
                return False

            calculated_hash = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

            if hmac.compare_digest(calculated_hash, hashval):
                try:
                    self.password = generate_password_hash(password, method="pbkdf2:sha256")
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                return True
            return False

        return check_password_hash(stored_password, password)

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
    # learn_progress defined via backref in LearnTestProgress

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
    # Consider using JSON if PickleType causes issues or for better database portability
    answers = db.Column(db.PickleType, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('learn_progress', lazy='dynamic', cascade='all, delete-orphan'))
    test = db.relationship('Test', backref=db.backref('learn_progress', lazy='dynamic', cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint('user_id', 'test_id', name='_user_test_uc'),)

class ReadingActivity(db.Model):
    __tablename__ = 'reading_activity' # Add this line for clarity
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    pages = db.relationship('ReadingPage', backref='activity', lazy=True, cascade='all, delete-orphan')
    # user_progress defined via backref in UserReadingProgress

class ReadingPage(db.Model):
    __tablename__ = 'reading_page' # Add this line for clarity
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    page_number = db.Column(db.Integer)
    activity_id = db.Column(db.Integer, db.ForeignKey('reading_activity.id'), nullable=False)

# --- MODIFIED CLASS ---
class UserReadingProgress(db.Model):
    __tablename__ = 'user_reading_progress' # Explicitly specify table name
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('reading_activity.id'), nullable=False)
    # Use JSON type to store the list of unlocked page numbers
    unlocked_pages = db.Column(JSON, default=[1]) # Changed from PickleType, ensures default is a list

    # Define relationships with backrefs and cascades
    user = db.relationship('User', backref=db.backref('reading_progress', lazy='dynamic', cascade='all, delete-orphan'))
    activity = db.relationship('ReadingActivity', backref=db.backref('user_progress', cascade='all, delete-orphan'))

    # Add a unique constraint: a user should only have one progress record per activity
    __table_args__ = (db.UniqueConstraint('user_id', 'activity_id', name='_user_activity_uc'),)
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User
from ..forms import SignupForm, LoginForm
from .. import db, login_manager

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Flask-Login's user loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User signup route
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    # Redirect to home if the user is already authenticated
    if current_user.is_authenticated:
        flash('You are already signed in.', 'info')
        return redirect(url_for('main.index'))

    form = SignupForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken. Please choose a different one.', 'danger')
            return render_template('auth/signup.html', form=form)

        # Create new user
        new_user = User(
            username=username,
            password=generate_password_hash(password, method='sha256')
        )

        # Add new user to the database
        db.session.add(new_user)
        db.session.commit()

        # Log in the new user
        login_user(new_user)
        flash(f'Welcome, {new_user.username}! You have successfully signed up and logged in.', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/signup.html', form=form)

# User login route
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)  # Pass the remember value
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html', form=form)

# User logout route
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


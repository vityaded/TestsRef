from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

import unicodedata
import re

def normalize_text(text):
    if not text:
        return ''
    # Normalize unicode characters (e.g., é to e)
    text = unicodedata.normalize('NFKD', text)
    # Remove diacritics (accents)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation (except apostrophes if needed)
    text = re.sub(r'[^\w\s]', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text


from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from ..models import Vocabulary
from ..forms import EditWordForm
from .. import db
from datetime import datetime, timedelta
import random
from ..utils import normalize_text

vocab_bp = Blueprint('vocab', __name__, url_prefix='/vocabulary')

@vocab_bp.route('/')
@login_required
def my_vocabulary():
    vocab_words = Vocabulary.query.filter_by(user_id=current_user.id).all()
    return render_template('vocabulary/vocabulary.html', vocab_words=vocab_words)

@vocab_bp.route('/add', methods=['POST'])
@login_required
def add_to_vocabulary():
    data = request.get_json()
    word = data.get('word')
    translation = data.get('translation')

    # Ensure that word and translation are not None or empty
    if not word or not translation:
        return jsonify({'success': False, 'error': 'Invalid data: word or translation is missing'}), 400

    try:
        # Check if the word already exists in the user's vocabulary
        existing_word = Vocabulary.query.filter_by(user_id=current_user.id, word=word).first()
        if existing_word:
            return jsonify({'success': False, 'error': 'Word already exists in your vocabulary'}), 400

        # Add word to user's vocabulary
        new_vocab = Vocabulary(
            word=word,
            translation=translation,
            user_id=current_user.id,
            next_review=datetime.utcnow(),
            interval=0,
            ease_factor=2.5,
            learning_stage=0
        )
        db.session.add(new_vocab)
        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@vocab_bp.route('/edit/<int:word_id>', methods=['GET', 'POST'])
@login_required
def edit_word(word_id):
    word = Vocabulary.query.get_or_404(word_id)
    if word.user_id != current_user.id:
        flash('You are not authorized to edit this word.', 'danger')
        return redirect(url_for('vocab.my_vocabulary'))

    form = EditWordForm(obj=word)
    if form.validate_on_submit():
        word.word = form.word.data
        word.translation = form.translation.data
        db.session.commit()
        flash('Word updated successfully.', 'success')
        return redirect(url_for('vocab.my_vocabulary'))

    return render_template('vocabulary/edit_word.html', form=form)

@vocab_bp.route('/delete/<int:word_id>', methods=['POST'])
@login_required
def delete_word(word_id):
    word = Vocabulary.query.get_or_404(word_id)
    if word.user_id != current_user.id:
        flash('You are not authorized to delete this word.', 'danger')
        return redirect(url_for('vocab.my_vocabulary'))

    db.session.delete(word)
    db.session.commit()
    flash('Word deleted successfully.', 'success')
    return redirect(url_for('vocab.my_vocabulary'))

@vocab_bp.route('/review', methods=['GET', 'POST'])
@login_required
def review():
    # Fetch due words
    today = datetime.utcnow()
    due_words = Vocabulary.query.filter(
        Vocabulary.user_id == current_user.id,
        Vocabulary.next_review <= today
    ).all()

    if not due_words:
        flash('No words due for review today!', 'info')
        return redirect(url_for('vocab.my_vocabulary'))

    # Get the current word index from the session
    current_word_index = session.get('current_word_index', 0)
    total_words = len(due_words)

    # Retrieve the current word
    if current_word_index < total_words:
        word = due_words[current_word_index]
    else:
        # All words reviewed
        flash('Review session completed!', 'success')
        session.pop('current_word_index', None)
        return redirect(url_for('vocab.my_vocabulary'))

    # Determine the review stage
    review_stage = word.learning_stage

    if request.method == 'POST':
        user_answer = request.form.get('answer', '').strip()
        correct_answer = word.word.strip() if review_stage % 2 == 0 else word.translation.strip()

        # Normalize the text for comparison
        normalized_user_answer = normalize_text(user_answer)
        normalized_correct_answer = normalize_text(correct_answer)

        if normalized_user_answer == normalized_correct_answer:
            # Correct answer
            word.learning_stage += 1
            word.ease_factor = max(1.3, word.ease_factor - 0.2)  # Decrease ease factor for correct answers
            word.interval = get_next_interval(word.learning_stage, word.ease_factor)
            word.next_review = datetime.utcnow() + timedelta(days=word.interval)
            db.session.commit()
            flash('Correct!', 'success')
        else:
            # Incorrect answer
            word.learning_stage = max(0, word.learning_stage - 1)
            word.ease_factor = min(2.5, word.ease_factor + 0.2)  # Increase ease factor for incorrect answers
            word.interval = get_next_interval(word.learning_stage, word.ease_factor)
            word.next_review = datetime.utcnow() + timedelta(days=word.interval)
            db.session.commit()
            flash(f'Incorrect! The correct answer was "{correct_answer}".', 'danger')

        # Move to the next word
        session['current_word_index'] = current_word_index + 1
        return redirect(url_for('vocab.review'))

    # Prepare the question and options based on the review stage
    if review_stage == 0:
        # First review: Multiple choice translation
        question = word.translation
        options = get_options(word.word)
        template = 'vocabulary/first_review.html'
    elif review_stage == 1:
        # Second review: Multiple choice original word
        question = word.word
        options = get_options(word.translation)
        template = 'vocabulary/second_review.html'
    elif review_stage == 2:
        # Third review: Unscramble the word
        question = word.translation
        scrambled_word = ''.join(random.sample(word.word, len(word.word)))
        session['scrambled_word'] = scrambled_word
        template = 'vocabulary/third_review.html'
    elif review_stage >= 3:
        # Fourth and subsequent reviews: Type the word
        question = word.translation if review_stage % 2 == 0 else word.word
        template = 'vocabulary/fourth_review.html'
    else:
        flash('Invalid review stage.', 'danger')
        return redirect(url_for('vocab.my_vocabulary'))

    return render_template(
        template,
        question=question,
        options=options if 'options' in locals() else None,
        scrambled_word=session.get('scrambled_word', None),
        review_stage=review_stage,
        current_word_number=current_word_index + 1,
        total_words=total_words
    )

def get_options(correct_answer):
    # Generate a list of options including the correct answer
    options = [correct_answer]
    vocab_words = Vocabulary.query.filter(Vocabulary.user_id == current_user.id).all()
    all_words = [word.word for word in vocab_words if word.word != correct_answer]
    if len(all_words) >= 3:
        options.extend(random.sample(all_words, 3))
    else:
        options.extend(all_words)
    random.shuffle(options)
    return options

def get_next_interval(learning_stage, ease_factor):
    # Simple spaced repetition algorithm
    if learning_stage == 0:
        return 1  # 1 day
    elif learning_stage == 1:
        return 3  # 3 days
    else:
        return learning_stage * ease_factor

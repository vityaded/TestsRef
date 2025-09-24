from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_login import login_required, current_user
from ..models import Vocabulary
from ..forms import EditWordForm
from .. import db
from datetime import datetime, timedelta
import random
from ..utils import normalize_text

vocab_bp = Blueprint('vocab', __name__, url_prefix='/vocabulary')

# Display all vocabulary words
@vocab_bp.route('/')
@login_required
def my_vocabulary():
    vocab_words = Vocabulary.query.filter_by(user_id=current_user.id).all()
    return render_template('vocabulary/vocabulary.html', vocab_words=vocab_words)

# Add a new word to the vocabulary
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

# Edit an existing word in the vocabulary
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

# Delete a word from the vocabulary
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

# Review vocabulary words
@vocab_bp.route('/review', methods=['GET', 'POST'])
@login_required
def review():
    today = datetime.utcnow()
    due_words = Vocabulary.query.filter(
        Vocabulary.user_id == current_user.id,
        Vocabulary.next_review <= today
    ).all()

    if not due_words:
        flash('No more words due for review!', 'info')
        return redirect(url_for('vocab.my_vocabulary'))

    if request.method == 'POST':
        word_id = request.form.get('word_id')
        if not word_id:
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('vocab.review'))
        word = Vocabulary.query.get(word_id)
        if not word or word.user_id != current_user.id:
            flash('Invalid word. Please try again.', 'danger')
            return redirect(url_for('vocab.review'))

        user_answer = request.form.get('answer', '').strip()
        review_stage = word.learning_stage

        # Ensure that 'correct_answer' is defined appropriately
        if review_stage == 0:
            correct_answer = word.word.strip()
        elif review_stage == 1:
            correct_answer = word.translation.strip()
        elif review_stage == 2:
            correct_answer = word.word.strip()
        elif review_stage >= 3:
            if review_stage % 2 == 0:
                correct_answer = word.word.strip()
            else:
                correct_answer = word.translation.strip()
        else:
            correct_answer = ''

        # Normalize the text for comparison
        normalized_user_answer = normalize_text(user_answer)
        normalized_correct_answer = normalize_text(correct_answer)

        # Debugging statements
        current_app.logger.debug(
            "vocabulary.review: review_stage=%s question='%s'",
            review_stage,
            word.translation if review_stage % 2 == 0 else word.word,
        )
        current_app.logger.debug(
            "vocabulary.review: user_answer='%s' correct_answer='%s'",
            user_answer,
            correct_answer,
        )
        current_app.logger.debug(
            "vocabulary.review: normalized_user_answer='%s' normalized_correct_answer='%s'",
            normalized_user_answer,
            normalized_correct_answer,
        )

        if normalized_user_answer == normalized_correct_answer:
            # Correct answer: increase the learning stage
            word.learning_stage += 1
            word.ease_factor = max(1.3, word.ease_factor - 0.2)
            word.interval = get_next_interval(word.learning_stage, word.ease_factor)
            word.next_review = datetime.utcnow() + timedelta(
                minutes=word.interval if word.learning_stage < 3 else word.interval * 24 * 60)
            db.session.commit()
            flash('Correct!', 'success')
        else:
            # Incorrect answer: reset learning stage to 0 and ease factor to default
            word.learning_stage = 0
            word.ease_factor = 2.5
            word.interval = get_next_interval(word.learning_stage, word.ease_factor)
            word.next_review = datetime.utcnow() + timedelta(minutes=1)
            db.session.commit()
            flash(f'Incorrect! The correct answer was "{correct_answer}". The word has been reset.', 'danger')

        return redirect(url_for('vocab.review'))

    else:
        # GET request
        # Get the current word index from the session
        current_word_index = session.get('current_word_index', 0)

        # Reset the current_word_index if it is out of range
        if current_word_index >= len(due_words):
            current_word_index = 0
            session['current_word_index'] = current_word_index

        # Retrieve the current word
        word = due_words[current_word_index]

        # Determine the review stage
        review_stage = word.learning_stage

        # Prepare the question and options based on the review stage
        if review_stage == 0:
            # First review: Multiple choice for the original word
            question = word.translation
            options = get_options(correct_answer=word.word, field='word')
            template = 'vocabulary/first_review.html'
        elif review_stage == 1:
            # Second review: Multiple choice for the translation
            question = word.word
            options = get_options(correct_answer=word.translation, field='translation')
            template = 'vocabulary/second_review.html'
        elif review_stage == 2:
            # Third review: Unscramble the word
            question = word.translation
            scrambled_word = ''.join(random.sample(word.word, len(word.word)))
            session['scrambled_word'] = scrambled_word
            template = 'vocabulary/third_review.html'
        elif review_stage >= 3:
            # Fourth and subsequent reviews: Type the word or translation
            if review_stage % 2 == 0:
                question = word.translation
                # The user must type the original word
            else:
                question = word.word
                # The user must type the translation
            template = 'vocabulary/fourth_review.html'
        else:
            flash('Invalid review stage.', 'danger')
            return redirect(url_for('vocab.my_vocabulary'))

        # Move to the next word index for the next GET request
        session['current_word_index'] = (current_word_index + 1) % len(due_words)

        return render_template(
            template,
            question=question,
            options=options if 'options' in locals() else None,
            scrambled_word=session.get('scrambled_word', None),
            review_stage=review_stage,
            current_word_number=current_word_index + 1,
            total_words=len(due_words),
            word=word  # Pass the word object to the template
        )
        
# Utility functions
def get_options(correct_answer, field='word'):
    # Generate a list of options including the correct answer
    options = [correct_answer]
    vocab_words = Vocabulary.query.filter(Vocabulary.user_id == current_user.id).all()

    if field == 'word':
        all_options = [word.word for word in vocab_words if word.word != correct_answer]
    elif field == 'translation':
        all_options = [word.translation for word in vocab_words if word.translation != correct_answer]
    else:
        all_options = []

    # Remove duplicates and ensure unique options
    all_options = list(set(all_options))

    # Ensure that there are enough options
    if len(all_options) >= 3:
        options.extend(random.sample(all_options, 3))
    else:
        options.extend(all_options)
    random.shuffle(options)
    return options

def get_next_interval(learning_stage, ease_factor):
    # Learning stage: 1-minute interval
    if learning_stage < 3:
        return 1 / 60  # 1 minute in days format
    # Long-term review: starts at 1 day, increases by ease_factor
    else:
        return 1 * (ease_factor ** (learning_stage - 3))

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    TextAreaField,
    IntegerField,
    BooleanField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')  # Add this line
    submit = SubmitField('Login')

class AddTestForm(FlaskForm):
    book_title = StringField('Book Title', validators=[DataRequired(), Length(min=1, max=150)])
    name = StringField('Test Name', validators=[DataRequired(), Length(min=1, max=150)])
    time_limit = IntegerField('Time Limit (minutes)', validators=[Optional(), NumberRange(min=1)])
    content = TextAreaField('Test Content', validators=[DataRequired()])
    shuffle_sentences = BooleanField('Shuffle Sentences')
    shuffle_paragraphs = BooleanField('Shuffle Paragraphs')
    submit = SubmitField('Add Test')

class AddGameForm(FlaskForm):
    name = StringField('Game Name', validators=[DataRequired(), Length(min=1, max=150)])
    content = TextAreaField('Game HTML', validators=[DataRequired()])
    submit = SubmitField('Save Game')

class EditGameForm(FlaskForm):
    name = StringField('Game Name', validators=[DataRequired(), Length(min=1, max=150)])
    content = TextAreaField('Game HTML', validators=[DataRequired()])
    submit = SubmitField('Update Game')

class EditTestForm(FlaskForm):
    name = StringField('Test Name', validators=[DataRequired(), Length(min=1, max=150)])
    time_limit = IntegerField('Time Limit (minutes)', validators=[Optional(), NumberRange(min=1)])
    content = TextAreaField('Test Content', validators=[DataRequired()])
    shuffle_sentences = BooleanField('Shuffle Sentences')
    shuffle_paragraphs = BooleanField('Shuffle Paragraphs')
    submit = SubmitField('Update Test')

class EditWordForm(FlaskForm):
    word = StringField('Word', validators=[DataRequired(), Length(min=1, max=150)])
    translation = StringField('Translation', validators=[DataRequired(), Length(min=1, max=150)])
    submit = SubmitField('Update Word')

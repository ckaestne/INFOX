# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from wtforms import (StringField, SubmitField, TextAreaField,
                     BooleanField, SelectField, ValidationError)
from wtforms.validators import Length

class AddProjectForm(FlaskForm):
    project_name = StringField('Input the full name of the project (author_repo)', validators = [Length(0, 30)])
    submit = SubmitField('Add')

class SearchProjectForm(FlaskForm):
    project_name = StringField('Project Name', validators = [Length(0, 30)])
    submit = SubmitField('Search')
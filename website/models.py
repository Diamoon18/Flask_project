#/*******************************************************************************
# * Autorskie Prawa Majątkowe - Moose spółka z ograniczoną odpowiedzialnością
# *
# * Copyright 2021 Moose spółka z ograniczoną odpowiedzialnością
# ******************************************************************************/
from datetime import datetime

from . import db
from flask_login import UserMixin


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    charts = db.relationship('Chart')


class Chart(db.Model):
    id_chart = db.Column(db.Integer, primary_key=True)
    sensor_name = db.Column(db.String(150))
    method = db.Column(db.String(150))
    params = db.relationship('Parameter')
    csv_file = db.Column(db.String(150))
    date = db.Column(db.String(150))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Parameter(db.Model):
    id_param = db.Column(db.Integer, primary_key=True)
    lower_limit = db.Column(db.Integer)
    upper_limit = db.Column(db.Integer)
    measurement_frequency = db.Column(db.Integer)
    default_measurement_value = db.Column(db.Integer)
    default_measurement_time = db.Column(db.Integer)
    chart_id = db.Column(db.Integer, db.ForeignKey('chart.id_chart'))

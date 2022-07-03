#/*******************************************************************************
# * Autorskie Prawa Majątkowe - Moose spółka z ograniczoną odpowiedzialnością
# *
# * Copyright 2021 Moose spółka z ograniczoną odpowiedzialnością
# ******************************************************************************/
import json
import os
from datetime import datetime

import paho.mqtt.client as mqtt
import time

import numpy as np
import csv

from flask import Blueprint, render_template, request, redirect, jsonify, flash
from . import db
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from website.models import Chart, Parameter

views = Blueprint('views', __name__)

ALLOWED_EXTENSIONS = {'csv'}
upload_dest = os.path.join(os.getcwd(), 'website/uploads')


@views.route('/', methods=['GET'])
def home():
    return render_template("base.html", user=current_user)


@views.route('/generate', methods=['GET', 'POST'])
@login_required
def dist():
    names, methods = sensors_names()
    history = '0'
    if request.method == 'POST':
        sensor_name = request.form.get('sensor_1')
        id = names[sensor_name]
        choice = request.form.get('chose')
        id_choice = methods[choice]
        return redirect(f"/generate/{history}/{id}/{id_choice}")
    return render_template("start.html", names=names, methods=methods, user=current_user)


@views.route('/history', methods=['GET'])
@login_required
def hist():
    return render_template("history.html", user=current_user)


@views.route('/history/<id>', methods=['GET'])
def hist_gen(id):
    history = id
    params, id_sensor, id_method = base_params(id)
    return redirect(f'/generate/{history}/{id_sensor}/{id_method}')


@views.route('/generate/<history>/<id>/<id_choice>', methods=['GET', 'POST'])
def dist_param(history, id, id_choice):
    global sensor_name, choice, params

    min_max = sensor_min_max(id)
    if history == '0':
        params = sensor_params(id)
    else:
        par = base_params(history)
        params = par[0]

    names, methods = sensors_names()
    for key, value in names.items():
        if value == id:
            sensor_name = key
    for key, value in methods.items():
        if value == id_choice:
            choice = key

    if request.method == 'POST' and request.form.get("button_identifier") == "mqtt":
        send_to_mqtt()
        return '', 204

    if id_choice == "1":  # form
        if request.method == 'POST':
            if id == "1":
                timeInMins = int(request.form.get('params5'))
                lower_limit = float(request.form.get('params1'))
                upper_limit = float(request.form.get('params2'))
                frequency_per_minute = float(request.form.get('params3'))
                start_value = float(request.form.get('params4'))

                ### add new Chart to db ###
                if history == '0':
                    new_chart = Chart(sensor_name=sensor_name, method=choice, csv_file="", date=datetime.now(),
                                      user_id=current_user.id)
                    db.session.add(new_chart)
                    db.session.commit()
                    params_chart = Parameter(lower_limit=lower_limit, upper_limit=upper_limit,
                                             measurement_frequency=frequency_per_minute,
                                             default_measurement_value=start_value,
                                             default_measurement_time=timeInMins, chart_id=new_chart.id_chart)

                    db.session.add(params_chart)
                    db.session.commit()
                else:
                    pass
                ### chart ###
                tick = round((1 / frequency_per_minute), 4)
                data = [[], []]
                frequency = timeInMins * frequency_per_minute
                if len(data[0]) == 0:
                    data[0].append(tick)
                    gain = np.random.uniform(-10.2, 10.2)
                    data[1].append(start_value + gain)
                    for i in range(1, int(frequency)):
                        data[0].append(data[0][-1] + tick)
                        gain = np.random.uniform(-10.2, 10.2)
                        data[1].append(start_value + gain)
                return render_template("chart.html", data=data, min=lower_limit, max=upper_limit, chartType=1)

            elif id == "2":
                timeInMins = int(request.form.get('params4'))
                lower_limit = float(request.form.get('params1'))
                upper_limit = float(request.form.get('params2'))
                frequency_per_minute = float(request.form.get('params3'))

                ### add new Chart to db ###
                if history == '0':
                    new_chart = Chart(sensor_name=sensor_name, method=choice, csv_file="", date=datetime.now(), user_id=current_user.id)
                    db.session.add(new_chart)
                    db.session.commit()
                    params_chart = Parameter(lower_limit=lower_limit, upper_limit=upper_limit,
                                             measurement_frequency=frequency_per_minute,
                                             default_measurement_value="",
                                             default_measurement_time=timeInMins, chart_id=new_chart.id_chart)

                    db.session.add(params_chart)
                    db.session.commit()
                else:
                    pass
                ### chart ###

                tick = round((1 / frequency_per_minute), 4)
                data = [[], []]
                frequency = timeInMins * frequency_per_minute
                if len(data[0]) == 0:
                    data[0].append(tick)
                    gain = np.random.uniform(-0.4, 0.4)
                    data[1].append(30 + gain)
                    for i in range(1, int(frequency)):
                        data[0].append(data[0][-1] + tick)
                        gain = np.random.uniform(-0.4, 0.4)
                        data[1].append(data[1][-1] + gain)

                return render_template("chart.html", data=data, min=lower_limit, max=upper_limit, chartType=2)
            else:
                pass
        if id == "1" or id == "2":
            return render_template("form.html", params=params, min_max=min_max, id=id, user=current_user)
        else:
            flash('We are sorry..This sensor is not available yet!', category='error')
            return redirect("/generate")
    elif id_choice == "2" and (id == "1" or id == "2"):  # .csv button
        return redirect(f"/generate/{id}/upload")
    else:
        flash('We are sorry..This sensor is not available yet!', category='error')
        return redirect("/generate")


@views.route('/generate/<id>/upload', methods=['GET', 'POST'])
def upload_csv(id):
    choice = "Load data from .csv file"
    global sensor_name
    names, methods = sensors_names()
    for key, value in names.items():
        if value == id:
            sensor_name = key

    if request.method == 'POST' and request.form.get("button_identifier") == "mqtt":
        send_to_mqtt()
        return '', 204
    if request.method == 'POST':
        if 'file' not in request.files:
            print('No found, try again.')
            return redirect(request.url)
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(upload_dest, filename))

            ### add new Chart to db ###

            new_chart = Chart(sensor_name=sensor_name, method=choice, csv_file=os.path.join(upload_dest, filename),
                              date=datetime.now(), user_id=current_user.id)
            db.session.add(new_chart)
            db.session.commit()

            name = open('website/uploads/' + filename)
            dialect = csv.Sniffer().sniff(name.read(), delimiters=';,-\t')
            name.seek(0)
            file = csv.DictReader(name, dialect=dialect)

            times = []
            values = []
            data = [times, values]
            if file.fieldnames[1] == "Distance":
                for col in file:
                    times.append(float(col['Time']))
                    values.append(float(col['Distance']))
                chartType = 1
            elif file.fieldnames[1] == "Temperature":
                for col in file:
                    times.append(float(col['Time']))
                    values.append(float(col['Temperature']))
                chartType = 2
            return render_template("chart.html", data=data, min=min(values), max=max(values), chartType=chartType)
        else:
            print("Error!")
    return render_template("button.html", user=current_user)


############### HELP FUNCTIONS ################
def send_to_mqtt():
    test = request.form['hidden']
    topic = request.form.get('topic')
    client = mqtt.Client()
    client.connect("localhost", 1883, 60)
    test2 = test[1:-1]
    test3 = test2.split(', ')
    for i in range(0, len(test3)):
        client.publish(topic, '{"values":' + str(test3[i]) + '}')
        time.sleep(1)
    client.disconnect()


def base_params(id):
    global sensor_name, choise, id_sensor, id_method, path_csv
    names, methods = sensors_names()
    list_values = list()

    for chart in current_user.charts:
        if chart.id_chart == int(id):
            sensor_name = chart.sensor_name
            choise = chart.method
            break

    for key, value in names.items():
        if sensor_name == key:
            id_sensor = value
            break

    for key, value in methods.items():
        if choise == key:
            id_method = value
            break

    if id_method == '1':
        par = sensor_params(id_sensor)
        keys = list(par.keys())

        for chart in current_user.charts:
            if chart.id_chart == int(id):
                for param in chart.params:
                    list_values.append(param.lower_limit)
                    list_values.append(param.upper_limit)
                    list_values.append(param.measurement_frequency)
                    list_values.append(param.default_measurement_value)
                    list_values.append(param.default_measurement_time)
                break

        while "" in list_values:
            list_values.remove("")

        params = dict(zip(keys, list_values))
        return params, id_sensor, id_method

    elif id_method == '2':
        for chart in current_user.charts:
            if chart.id_chart == int(id):
                path_csv = chart.csv_file
        return path_csv, id_sensor, id_method


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def sensor_min_max(id):
    with open("website/static/device_config.json") as jsonFile:
        jsonObject = json.load(jsonFile)
        jsonFile.close()

    products = jsonObject['devices']
    min_max = list()
    for product in products:
        if product['id'] == id:
            min_max.append(product['min_value'])
            min_max.append(product['max_value'])
            break
    return min_max


def sensor_params(id):
    with open("website/static/device_config.json") as jsonFile:
        jsonObject = json.load(jsonFile)
        jsonFile.close()

    products = jsonObject['devices']
    dict_param = dict()
    for product in products:
        if product['id'] == id:
            dict_param = product['params']

    list_names = []
    list_values = []
    for names, values in dict_param.items():
        list_names.append((names.capitalize()).replace("_", " "))
        list_values.append(values)
    dict_data = dict(zip(list_names, list_values))
    return dict_data


def sensors_names():
    with open("website/static/device_config.json") as jsonFile:
        jsonObject = json.load(jsonFile)
        jsonFile.close()

    sensors = jsonObject['devices']
    methods = jsonObject['methods']

    list_names = []
    list_id = []
    for sensor in sensors:
        list_names.append(sensor['type'] + " - " + sensor['name'])
        list_id.append(sensor['id'])
    dict_data = dict(zip(list_names, list_id))

    list_method = []
    list_id_m = []
    for method in methods:
        list_method.append(method['name'])
        list_id_m.append(method['id'])
    dict_method = dict(zip(list_method, list_id_m))
    return dict_data, dict_method

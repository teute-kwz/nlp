
#!/usr/local/bin/python3
import configparser
import os
import sqlite3
import numpy as np
import pickle

import asana
from datetime import datetime, timedelta
from dash import Dash, callback_context, dcc, html, no_update
from dash.exceptions import PreventUpdate
from flask import Response, request
from flask_jwt_extended import (JWTManager, create_access_token,
                                create_refresh_token, get_jwt,
                                get_jwt_identity, jwt_required)
from flask_restful import Api, Resource, reqparse
from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy import JSON, Table, cast, create_engine, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy_json import mutable_json_type
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint, create_engine, func, text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


from preprocessing import translate
# from dbgen import messages

def classifier(message):
    conn = sqlite3.connect('db0.sqlite3')
    cursor = conn.execute('select * from models')
    name, pickled_clf = cursor.fetchone()
    transformer_model = pickle.loads(pickled_clf)
    encoded_message = np.array([transformer_model.encode(message)])

    
    pca = pickle.load(open("saved_model/pca.pkl",'rb'))
    reduced_message = pca.transform(encoded_message)

    chains = pickle.load(open("saved_model/chains.pkl",'rb'))

    Y_pred_chains = np.array([chain.predict(reduced_message) for chain in chains])
    Y_pred_ensemble = Y_pred_chains.mean(axis=0)
    Y_pred_ensemble = (Y_pred_ensemble>=0.5).astype(int)

    list_of_labels = ['Operations', 'Service', 'Business', 'Software', 'Electrical', 'Mechanical', 'Data Analytics']
    list_of_names = [kwz_dima, kwz_heitor, kwz_jonas, kwz_eirini, kwz_artur, kwz_aleks, kwz_alex]

    labels = []
    names = []
    for j in range(len(Y_pred_ensemble[0])):
        if Y_pred_ensemble[0][j]==1:
            labels.append(list_of_labels[j])
            names.append(list_of_names[j])
            
    if len(labels)==0:
        labels.append("General message")
        names.append(kwz_alim)

    return labels, names

def match(list_of_departments):
    list_of_names = []
    for i in list_of_departments:
        if i == 'Operations':
            list_of_names.append('Dmitry Chokovski')
        elif i == 'Service':
            list_of_names.append('Heitor Gartner')
        elif i == 'Business':
            list_of_names.append('Jonas Lerchenmueller')
        elif i == 'Software':
            list_of_names.append('Eirini Psallida')
        elif i == 'Electrical':
            list_of_names.append('Artur Nuritdinov')
        elif i == 'Mechanical':
            list_of_names.append('Aleks')
        elif i == 'Data Analytics':
            list_of_names.append('Alexander Liu Cheng')
        elif i == 'General message':
            list_of_names.append('Alimzhan Rakhmatulin')
    return list_of_names

DBURI = os.getenv('DBURI')
tbl1 = "messages"
tbl2 = "training"
database_name = "nlp_db0"
input_base = declarative_base()
input_engine = create_engine(DBURI+database_name)


class  messages(input_base):
    __tablename__ = tbl1
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, unique=True)
    sms_id = Column(SQLAlchemy().String(), unique=True)
    from_number = Column(SQLAlchemy().String())
    profile_name = Column(SQLAlchemy().String())
    body = Column(SQLAlchemy().String())
    assigned_department = Column(SQLAlchemy().String())
    assigned_people = Column(SQLAlchemy().String())
    __table_args__ = (UniqueConstraint("sms_id"),)
    

class training(input_base):
    __tablename__ = tbl2
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, unique=True)
    sms_id = Column(SQLAlchemy().String(), unique=True)
    body = Column(SQLAlchemy().String())
    assigned_people = Column(SQLAlchemy().String())
    __table_args__ = (UniqueConstraint("sms_id"),)


def respond(message):
    print('>', message, type(message))
    response = MessagingResponse()
    response.message(message)
    return str(response)

app = Dash(
    __name__,
)

server = app.server

server.config.update(
    SECRET_KEY=os.urandom(12),
    SQLALCHEMY_DATABASE_URI=DBURI+database_name, 
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    JWT_SECRET_KEY=os.urandom(12), ##api
    JWT_BLACKLIST_ENABLED=True,  ##api
    JWT_BLACKLIST_TOKEN_CHECKS=['access', 'refresh'],  ##api
)

personal_access_token_asana = os.getenv('ASANAPAT')
account_sid = os.getenv('TWIL_ACCNT_SID')
auth_token = os.getenv('TWIL_AUTH_TOKEN')

client = asana.Client.access_token(personal_access_token_asana)
client.LOG_ASANA_CHANGE_WARNINGS = False

kwz_dima = '641548626378173'
kwz_alex = '1165456504250587'
kwz_aleks = '834132227637161'
kwz_heitor = '1142230793157948'
kwz_jonas = '1174024411413512'
kwz_artur = '1136531459865872'
kwz_eirini = '116216123886766'
kwz_teute = '1202376371849303'
kwz_alim = '116216123886754'

project_id = '1202245000194289'

target = 'https://c5b12089bda9.eu.ngrok.io/wasana'

@server.route('/wasana', methods=['POST'])
def reply():
    print('-----------------')
    print(request.headers['User-Agent'])

    if request.headers['User-Agent'] == 'Asana' and 'X-Hook-Secret' in request.headers:    
        print('Handshake from Asana', request.headers['X-Hook-Secret'])
        secret = request.headers['X-Hook-Secret']
        reply = Response('200')
        reply.headers['X-Hook-Secret'] = secret

        return reply

    if request.headers['User-Agent'] == 'TwilioProxy/1.1':
        print('Message from Twilio')
        msg_id = request.form.get('MessageSid')
        sender = request.form.get('From')
        sender_name = request.form.get('ProfileName')
        message = request.form.get('Body')

        if message is not None:
            print('>>>>>>>>>>>>>>>>>', request.form)

            translated_message = translate(message)
            labels, names = classifier(translated_message)

            Session = sessionmaker(input_engine)
            row = messages(
                        timestamp = datetime.now(),
                        sms_id = msg_id,
                        from_number = sender,
                        profile_name = sender_name,
                        body = message,
                        assigned_department = ', '.join(str(x) for x in labels),
                        assigned_people = ', '.join(str(x) for x in match(labels))
                        
                    )
            with Session() as session:
                session.add(row)
                session.commit()
                # print("committed!")
                session.close()

            in_twentyfour = datetime.now() + timedelta(hours=24)

            if message.lower() == translated_message.lower():
                newtask = client.tasks.create_task(
                    {
                        "due_at": in_twentyfour.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "projects":["1202245000194289"], ## WhatsApp project
                        "followers":[kwz_teute], 
                        "assignee":kwz_teute,
                        "name": 'Message from ' + sender_name ,
                        "html_notes": "<body>" + sender + '\n'  +"<b>ID: </b>" + msg_id + '\n'  + "<b>Message: </b>" + message + '\n'  +  "<b>Assigned to departments: </b>" + ', '.join(str(x) for x in labels) + '\n'  + "<b>People assigned: </b>" + ', '.join(str(x) for x in match(labels)) +"</body>"
                    } 
                )
            else:
                newtask = client.tasks.create_task(
                    {
                        "due_at": in_twentyfour.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "projects":["1202245000194289"], ## WhatsApp project
                        "followers":[kwz_teute], 
                        "assignee":kwz_teute,
                        "name": 'Message from ' + sender_name,
                        "html_notes": "<body>" + sender + '\n'  + "<b>ID: </b>" + msg_id + '\n'  + "<b>Message: </b>" + message + '\n'  + "<b>Translated message: </b>" + translated_message + '\n'  +  "<b>Assigned to departments: </b>" + ', '.join(str(x) for x in labels) + '\n'  + "<b>People assigned: </b>" + ', '.join(str(x) for x in names) +"</body>"
                    } 
                )
            
        
            ## create webhook with new task's gid
            req = {
                "resource": newtask['gid'], 
                "target": target 
            }

            res = client.webhooks.create(req)
            print(res)

            return respond('Thank you for contacting KEWAZO! We have received your message and a technician and will respond within 24hrs.')  #twiML getting sent as Content-Type: text/html; charset=utf-8

        else:
            return respond("Empty message")
    elif request.headers['User-Agent'] == 'Asana':
        print('Normal message from Asana ----------->')
        print('>>>', request.json['events'])

        comment_id = ''

        if request.json['events']:
           
            comment_id = request.json['events'][-1]['resource']['gid'] 
            origin_id = request.json['events'][0]['resource']['gid']

            # print('---------compare:', origin_id, comment_id)
            # print('---------comment_id:', comment_id)

            comment = client.stories.get_story(comment_id, opt_pretty=True)
            project_tasks = client.tasks.find_by_project(project_id, {"opt_fields":"this.notes"},  iterator_type=None)
            id = 0
            for i in range(len(project_tasks)):
                if project_tasks[i]['gid']==origin_id:
                    id = i
   
            msg_id = ''
            message = ''
            phone_number = ''

            for item in project_tasks[id]['notes'].split("\n"):
                if "ID" in item:
                    msg_id = item.replace('ID: ', '')
                if 'Message' in item:
                    message = item.replace('Message: ', '')
                if 'whatsapp' in item:
                    phone_number = item

            completed_by = client.tasks.find_by_project(project_id, {"opt_expand":"assignee"},  iterator_type=None)[id]['assignee']['name']

            #for some reason this is returned multiple times and the client keeps getting the sme messga eover and over            
            if '<REPLY!:>' in comment['text']:
                Session = sessionmaker(input_engine)
                                # session = Session()
                row = training(
                            timestamp = datetime.now(),
                            sms_id = msg_id,
                            body = message,
                            assigned_people = completed_by
                        )
                with Session() as session:
                    session.add(row)
                    session.commit()
                    # print("committed!")


                print('Sending back to client:', comment['text'])
                Client(account_sid, auth_token).messages.create(
                    from_='whatsapp:+3197010253713',  
                    body= comment['text'].replace('<REPLY!:>', ''),      
                    to=phone_number
                )
                responded = comment['creted_by']['name']
            
            return Response('200')
        else:
            print('request.json["events"] is empty')
            return Response('200')
   
    else:
        comment = client.stories.get_story('1202286200716234', opt_pretty=True)
        project_tasks = client.tasks.find_by_project(project_id, {"opt_fields":"this.notes"},  iterator_type=None)
        for item in project_tasks[id]['notes'].split("\n"):
                if "ID" in item:
                    msg_id = item.replace('ID: ', '')
                if 'Message' in item:
                    message = item.replace('Message: ', '')
                if 'whatsapp' in item:
                    phone_number = item

        Client(account_sid, auth_token).messages.create(
            from_='whatsapp:+3197010253713',  
            body=comment['text'],      
            to=phone_number

        )
        
        return Response('200')












app.layout = html.Div(
    id='main_container',
    
)







if __name__ == '__main__':        
    app.run_server(host='0.0.0.0', debug=True)

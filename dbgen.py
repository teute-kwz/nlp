from sqlalchemy import (Column, DateTime, Float, Integer, UniqueConstraint,
                        create_engine, func)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

project_name = "nlp_db0"
tbl1 = "messages"
tbl2 = "training"

DBURI = os.getenv('DBURI')

engine = create_engine(DBURI)
conn = engine.connect()
conn.execute("commit")
conn.execute("create database " + project_name)
conn.close()



db_string = DBURI + project_name

db = create_engine(db_string)  
# db = SQLAlchemy()
base = declarative_base()

# ('SmsMessageSid', 'SMf29d91c8e9d86ba69f2671da6e2e678b'), ('NumMedia', '0'), ('ProfileName', 'Teute Drini'), ('SmsSid', 'SMf29d91c8e9d86ba69f2671da6e2e678b'), ('WaId', '37745832069'), ('SmsStatus', 'received'), ('Body', 'How much did we lift yesterday'), ('To', 'whatsapp:+3197010253713'), ('NumSegments', '1'), ('ReferralNumMedia', '0'), ('MessageSid', 'SMf29d91c8e9d86ba69f2671da6e2e678b'), ('AccountSid', 'AC72edff6111ea7fde1809ac64a3a7d3f7'), ('From', 'whatsapp:+37745832069'), ('ApiVersion', '2010-04-01')

class  messages(base):
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
    

class training(base):
    __tablename__ = tbl2
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, unique=True)
    sms_id = Column(SQLAlchemy().String(), unique=True)
    body = Column(SQLAlchemy().String())
    assigned_people = Column(SQLAlchemy().String())
    __table_args__ = (UniqueConstraint("sms_id"),)


Session = sessionmaker(db)  
session = Session()

base.metadata.create_all(db)

import uuid

from flask_serialize import FlaskSerializeMixin
from geoalchemy2 import Geometry
from shapely.wkb import loads
from sqlalchemy.dialects.postgresql import UUID, HSTORE
from sqlalchemy.event import listens_for
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import backref

from .extensions import db

FlaskSerializeMixin.db = db

PRAYERS = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha', 'jumuah', 'janazah', 'taraweeh']
NUMS = [0, 1, 2, 3, 4, 5, 6, 7]


# TODO: test cascades
class User(db.Model, FlaskSerializeMixin):
    __tablename__ = 'users'

    id = db.Column(db.String(), primary_key=True)
    full_name = db.Column(db.Unicode())
    email = db.Column(db.String(), unique=True)
    gender = db.Column(db.String(length=1))
    prayers_made = db.relationship("Prayer", backref=backref("user_inviter"))
    participations = db.relationship('Participations', back_populates="user", cascade='all, delete')
    filter_preferences = db.relationship("FilterPreference", cascade='all,delete-orphan', single_parent=True, backref=backref("user", cascade="all"), uselist=False)
    device_token = db.Column(db.String(), nullable=True)
    black_list = db.Column(MutableDict.as_mutable(HSTORE), default={})
    location = db.Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    locale = db.Column(db.String(), default="en")

    def __init__(self, id, full_name, email, gender):
        self.id = id
        self.full_name = full_name
        self.email = email
        self.gender = gender

    def __repr__(self):
        return '<id {}>'.format(self.id)

    def public_info(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'gender': self.gender
        }

    def private_info(self):
        location = loads(bytes(self.location.data)) if self.location else None
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'gender': self.gender,
            'location': {
                "lat": location.y if location else None,
                "lng": location.x if location else None
            },
            'locale': self.locale,
            'device_token': self.device_token,
        }


class Prayer(db.Model, FlaskSerializeMixin):
    __tablename__ = 'prayers'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prayer = db.Column(db.String())
    location = db.Column(Geometry(geometry_type='POINT', srid=4326))
    inviter = db.Column(db.String(), db.ForeignKey('users.id'))
    participants = db.relationship('Participations', back_populates="prayer", cascade='all, delete')
    participant_count = db.Column(db.Integer, default=0)
    guests_male = db.Column(db.Integer, default=0)
    guests_female = db.Column(db.Integer, default=0)
    schedule_time = db.Column(db.DateTime(timezone=True))
    description = db.Column(db.String())

    def __init__(self, prayer, inviter, location, guests_male, guests_female, description, schedule_time):
        self.prayer = prayer
        self.inviter = inviter
        self.participant_count = guests_female + guests_male
        self.location = location
        self.guests_male = guests_male
        self.guests_female = guests_female
        self.description = description
        self.schedule_time = schedule_time

    def serialize(self):
        location = loads(bytes(self.location.data))
        return {
            'id': self.id,
            'prayer': PRAYERS[int(self.prayer)],
            "location": {
                "lat": location.y,
                "lng": location.x
            },
            "inviter": User.query.get(self.inviter).public_info(),
            "participants": [u.serialize() for u in self.participants],
            "guests_female": self.guests_female,
            "guests_male": self.guests_male,
            "schedule_time": self.schedule_time,
            "description": self.description
        }


class Participations(db.Model, FlaskSerializeMixin):
    __tablename__ = 'participations'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    user_id = db.Column(db.String(), db.ForeignKey('users.id'))
    user_full_name = db.Column(db.Unicode())
    user_gender = db.Column(db.String(length=1))
    prayer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('prayers.id'))
    user = db.relationship(User, back_populates="participations")
    prayer = db.relationship(Prayer, back_populates="participants")

    def __init__(self, user, prayer):
        self.id = uuid.uuid4()
        self.user_id = user.id
        self.user_full_name = user.full_name
        self.user_gender = user.gender
        self.user = user
        self.prayer = prayer
        self.prayer_id = prayer.id
        self.prayer.participant_count += 1
    
    def serialize(self):
        return {
            'id': self.user_id,
            'full_name': self.user_full_name,
            'gender': self.user_gender
        }


class FilterPreference(db.Model, FlaskSerializeMixin):
    __tablename__ = 'filter_preferences'

    user_id = db.Column(db.String(), db.ForeignKey('users.id'), primary_key=True)
    selected_prayers = db.Column(db.String(), default='01234567')
    distance = db.Column(db.Integer, default=3)
    minimum_participants = db.Column(db.Integer, default=0)
    same_gender = db.Column(db.Boolean, default=False)

    def __init__(self, user_id):
        self.user_id = user_id
    
    def serialize(self):
      return {
        'minimum_participants': self.minimum_participants,
        'same_gender': self.same_gender,
        'selected_prayers': [PRAYERS[int(i)] for i in list(self.selected_prayers)]
      }


@listens_for(FilterPreference, 'before_insert')
def alter_min(mapper, connection, target):
    if target.same_gender:
        target.minimum_participants = max(2, target.minimum_participants)


@listens_for(Participations, 'before_delete')
def reduce_count(mapper, connection, target):
    target.prayer.participant_count -= 1

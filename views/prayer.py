import os
import requests
import json
from dateutil.parser import parse

from flask import Blueprint
from flask import request, jsonify
from sqlalchemy import func

from app.extensions import db, UUIDEncoder
from app.firebase_data import login_required
from app import models

file = open(os.path.dirname(__file__) + "/../i18n.json", "r", encoding="utf-8")
translations = json.loads(file.read())

prayer_view = Blueprint('prayer_view', __name__)

@prayer_view.route('/prayer', methods=['GET', 'POST', 'DELETE'])
def prayer():
    if request.method == 'GET':
        prayer_id = request.args.get('id')
        prayer_data = db.session.query(models.Prayer).get(prayer_id)
        
        if not prayer_data:
            return {'status': 'failure', 'error': 'prayer not found.'}, 404
        return jsonify({'status': 'success', 'data': prayer_data.serialize()}), 200

    elif request.method == 'POST':
        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        inviter = db.session.query(models.User).get(logged)
        data = request.get_json()
        prayer = None
        try:
            prayer = models.NUMS[models.PRAYERS.index(data['selected_prayer'])]
        except ValueError:
            pass
        if not data['description']:
            return {}, 400
        time = parse(data['schedule_time'])
        guests = data.get('guests') or {}
        print('1')
        try:
            p = models.Prayer(prayer=prayer,
                              location=func.ST_PointFromText('POINT({} {})'.format(data['lng'], data['lat']), 4326),
                              inviter=logged,
                              description=data['description'],
                              schedule_time=time, guests_male=guests.get('male'), guests_female=guests.get('female'))
        except KeyError:
            return jsonify({'status': 'failure', 'error': 'Supply all necessary info.'}), 400
        db.session.add(p)
        print('2')
        try:
            db.session.commit()
        except Exception as e:
            print(e)
            return jsonify({'status': 'failure', 'error': 'Data format is incorrect.'}), 400

        # Query necessary data for sending notifications
        # If the prayer is Janazah, set a larger notification range
        km = 30 if data['selected_prayer'] == 'janazah' else 3
        distance = km * 0.014472
        point = func.ST_PointFromText('POINT({} {})'.format(data['lng'], data['lat']), 4326)
        nearbyUsers = db.session.query(models.User).filter(func.ST_DFullyWithin(models.User.location, point, distance))
        if inviter.gender == 'M':
            nearbyUsers = nearbyUsers.join(models.FilterPreference).filter(models.FilterPreference.same_gender==False).all()
        else:
            nearbyUsers = nearbyUsers.filter(models.User.gender=='F').all()
        # Notify nearby users by sending request to the Expo server
        try:
            payloads = []

            for nearbyUser in filter(lambda u: u.device_token is not None and u.id is not inviter.id, nearbyUsers):
              payloads.append({
                  "to": nearbyUser.device_token,
                  "title": translations[nearbyUser.locale]['NEW_PRAYER_TITLE'],
                  "body": translations[nearbyUser.locale]['NEW_PRAYER'].format(user=inviter.full_name, prayer=translations[nearbyUser.locale]['PRAYERS'][data['selected_prayer']]),
                  "data": json.dumps({
                    "id": p.id,
                  }, cls=UUIDEncoder)
              })

            requests.post("https://exp.host/--/api/v2/push/send", json=payloads)
        except:
            pass

        user_data = db.session.query(models.User).get(logged).public_info()

        # Send prayer info to Slack
        try:
            payload = {
                "blocks": [{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Prayer Invitation\n>*Prayer ID*\n>{prayer_id}\n>\n>*Inviter ID*\n>{inviter_id}\n>\n>*Inviter Name*\n>{inviter_name}\n>\n>*Prayer*\n>{prayer}\n>\n>*Schedule Time*\n>{schedule_time}\n>\n>*Description*\n>{description}\n>\n>*Location*\n>https://www.google.com/maps/@{latitude},{longitude}".format(
                            prayer_id=p.id, inviter_id=logged, inviter_name=user_data['full_name'], prayer=prayer,
                            schedule_time=time, description=data['description'], latitude=data['lat'],
                            longitude=data['lng'])
                    }
                }]
            }

            # Do not wait for response
            requests.post(os.environ.get('SLACK_NEW_PRAYER_CHANNEL'), json=payload, timeout=0.1)

        except:
            pass

        return jsonify({'status': 'success', 'data': p.id}), 201

    else:
        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        pid = request.args.get('id')
        prayer = db.session.query(models.Prayer).get(pid)
        if logged == prayer.inviter:
            db.session.delete(prayer)
            db.session.commit()
            
            return {}, 200
        return {}, 403


@prayer_view.route('/prayer/feed', methods=['GET'])
def filter_feed():
    logged = None

    if request.headers.get('Authorization'):
        logged = login_required(request.headers.get('Authorization').split()[1])


    data = request.args
    filter_pref = None

    if logged:
        filter_pref = db.session.query(models.FilterPreference).get(logged)

    distance = 30 * 0.014472

    point = func.ST_PointFromText('POINT({} {})'.format(data['lng'], data['lat']), 4326)
    result = db.session.query(models.Prayer).filter(func.ST_DFullyWithin(models.Prayer.location, point, distance))

    if logged:
        # apply filters from user's preference
        result = result.filter(models.Prayer.prayer.in_(filter_pref.selected_prayers))

    result = result.filter(models.Prayer.schedule_time >= data['timestamp'])

    if logged:
        u = db.session.query(models.User).get(logged)
        if u.gender == 'F':
            if filter_pref.same_gender:
                result = result.join(models.User).filter(models.User.gender=="F")
            if filter_pref.minimum_participants:
                result = result.filter(models.Prayer.participant_count >= filter_pref.minimum_participants)
        else:
            result = result.join(models.User).filter(models.User.gender=="M")
    else:
        # only display invitations by male users if user is not logged
        result = result.join(models.User).filter(models.User.gender=="M")

    if data.get('sortBy') == 'distance':
        result = result.order_by(func.ST_Distance(models.Prayer.location, point))
    elif data.get('sortBy') == 'count':
        result = result.order_by(models.Prayer.participant_count.desc())
    else:
        result = result.order_by(models.Prayer.schedule_time.asc())

    PAGE_SIZE = 5
    result = result.limit(PAGE_SIZE).offset(int(data['pageNumber']) * PAGE_SIZE)

    data = [i.serialize() for i in result.all()]

    return jsonify({'status': 'success', 'data': data}), 200


@prayer_view.route('/prayer/map', methods=['GET'])
def filter_map():
    logged = None

    if request.headers.get('Authorization'):
        logged = login_required(request.headers.get('Authorization').split()[1])


    data = request.args
    filter_pref = None

    if logged:
        filter_pref = db.session.query(models.FilterPreference).get(logged)

    distance = 3 * 0.014472  # filter_pref.distance * 0.014472

    point = func.ST_PointFromText('POINT({} {})'.format(data['lng'], data['lat']), 4326)
    result = db.session.query(models.Prayer).filter(func.ST_DFullyWithin(models.Prayer.location, point, distance))

    if logged:
        u = db.session.query(models.User).get(logged)
        if u.gender == 'F':
            if filter_pref.same_gender:
                result = result.join(models.User).filter(models.User.gender=="F")
            if filter_pref.minimum_participants:
                result = result.filter(models.Prayer.participant_count >= filter_pref.minimum_participants)
        else:
            result = result.join(models.User).filter(models.User.gender=="M")
    else:
        # only display invitations by male users if user is not logged
        result = result.join(models.User).filter(models.User.gender=="M")

    return jsonify({'status': 'success', 'data': [i.serialize() for i in result.all()]}), 200


@prayer_view.route('/prayer/invitations', methods=['GET'])
def invitations():
    logged = login_required(request.headers.get('Authorization').split()[1])
    if not logged:
        return {}, 401
    
    PAGE_SIZE = 5
    result = models.Prayer.query.filter_by(inviter=request.args.get('user_id')).limit(PAGE_SIZE).offset(int(request.args.get('pageNumber')) * PAGE_SIZE)

    data = [i.serialize() for i in result.all()]

    return {"status": "success", "data": data}


@prayer_view.route('/prayer/invitations/amount', methods=['GET'])
def invitation_amount():
    logged = login_required(request.headers.get('Authorization').split()[1])
    if not logged:
        return {}, 401

    amount = models.Prayer.query.filter_by(inviter=request.args.get('user_id')).count()

    return {"status": "success", "data": {"amount": amount }}


@prayer_view.route('/prayer/participated', methods=['GET'])
def participated():
    logged = login_required(request.headers.get('Authorization').split()[1])
    if not logged:
        return {}, 401

    PAGE_SIZE = 5
    result = models.Participations.query.filter_by(user_id=request.args.get('user_id')).limit(PAGE_SIZE).offset(int(request.args.get('pageNumber')) * PAGE_SIZE)

    data = [i.prayer.serialize() for i in result.all()]

    return {"status": "success", "data": data}


@prayer_view.route('/prayer/participated/amount', methods=['GET'])
def participation_amount():
    logged = login_required(request.headers.get('Authorization').split()[1])
    if not logged:
        return {}, 401

    amount = models.Participations.query.filter_by(user_id=request.args.get('user_id')).count()

    return {"status": "success", "data": {"amount": amount}}


@prayer_view.route('/prayer/join', methods=['GET'])
def join():
    logged = login_required(request.headers.get('Authorization').split()[1])
    if not logged:
        return {}, 401
    if not request.args.get('id'):
        return {}, 400
    prayer = models.Prayer.query.get(request.args.get('id'))
    exists = models.Participations.query.filter_by(user_id=logged, prayer_id=prayer.id).first()
    if exists:
        db.session.delete(exists)
    else:
        new = models.Participations(user=models.User.query.get(logged),
                                    prayer=prayer)
        db.session.add(new)

        # Send notification to the inviter
        participant = db.session.query(models.User).get(logged)
        inviter = db.session.query(models.User).get(prayer.inviter)

        try :
            payload = {
              "to": inviter.device_token,
              "title": translations[inviter.locale]['NEW_PARTICIPANT'],
              "body": translations[inviter.locale]['JOIN_PRAYER'].format(user=participant.full_name, prayer=translations[inviter.locale]['PRAYERS'][models.PRAYERS[int(prayer.prayer)]]),
              "data": json.dumps({
                "id": prayer.id,
              }, cls=UUIDEncoder)
            }

            requests.post("https://exp.host/--/api/v2/push/send", json=payload)
        except:
            pass
    db.session.commit()
    
    return {}, 200

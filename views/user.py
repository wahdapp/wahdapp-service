import os
import requests
from flask import Blueprint
from flask import request, jsonify
from sqlalchemy import func

from validate_email import validate_email

from app.extensions import db
from app.firebase_data import login_required
from app import models

user_view = Blueprint('user_view', __name__)

@user_view.route('/user', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def user():
    if request.method == 'POST':
        data = request.get_json()
        try:
            u = models.User(id=data['uid'], full_name=data['full_name'], email=data['email'], gender=data.get('gender'))
        except KeyError:
            return jsonify({'status': 'failure', 'error': 'Supply all necessary info.'}), 400
        db.session.add(u)
        db.session.add(models.FilterPreference(user_id=u.id))
        try:
            assert data['gender'] in ('M', 'F')
            assert validate_email(data['email'])
            assert len(data['full_name']) < 30
            assert len(data['full_name']) > 0
            assert len(data['uid']) > 0
            db.session.commit()
        except Exception:
            return jsonify({'status': 'failure', 'error': 'Data format is incorrect.'}), 400

        try:
            # Send user info to Slack channel
            payload = {
                "blocks": [{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "New User\n>*User ID*\n>{user_id}\n>\n>*Full Name*\n>{full_name}\n>\n>*Email Address*\n>{email}\n>\n>*Gender*\n>{gender}".format(
                            user_id=data['uid'], full_name=data['full_name'], email=data['email'],
                            gender=data['gender'])
                    }
                }]
            }

            # Do not wait for response
            requests.post(os.environ.get('SLACK_NEW_USER_CHANNEL'), json=payload, timeout=0.1)
        except:
            pass      

        return jsonify({'status': 'success'}), 201

    elif request.method == 'GET':
        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        user_id = request.args.get('user_id')
        user_data = models.User.query.get(user_id)
        data = user_data.private_info()

        
        if not user_data:
            return {'status': 'failure', 'error': 'user not found.'}, 404
        return jsonify({'status': 'success', 'data': data}), 200

    elif request.method == 'PATCH':
        new_name = request.args.get('full_name')
        try:
            assert new_name and len(new_name) > 2
        except AssertionError:
            return {'status': 'failure', 'error': 'name format is incorrect'}, 400

        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        u = models.User.query.get(logged)
        print(u, u.full_name)
        u.full_name = new_name
        print(u, u.full_name)
        db.session.commit()
        

        return {'status': 'success'}, 200

    elif request.method == 'DELETE':
        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        db.session.delete(models.User.query.get(logged))
        
        return {'status': 'success'}, 200


@user_view.route('/user/locale', methods=['PATCH'])
def user_locale():
    if (request.method == 'PATCH'):
        locale = request.args.get('locale')
        try:
            assert locale and len(locale) > 0
        except AssertionError:
            return {'status': 'failure', 'error': 'missing locale'}, 400

        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        
        user = models.User.query.get(logged)
        user.locale = locale

        db.session.commit()

        return {'status': 'success'}, 200


@user_view.route('/user/location', methods=['POST'])
def user_location():
    if (request.method == 'POST'):
        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        
        data = request.get_json()
        user = models.User.query.get(logged)

        try :
            user.location = func.ST_PointFromText('POINT({} {})'.format(data['lng'], data['lat']), 4326)
        except KeyError:
            return {"status": "failure", "error": "Error while saving location"}
        
        db.session.commit()

        return {'status': 'success'}, 200


@user_view.route('/user/filter', methods=['GET', 'PATCH'])
def user_filter():
    if request.method == 'GET':
        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401

        filter_pref = models.FilterPreference.query.get(logged)
        data = filter_pref.serialize()
        

        if not filter_pref:
            return {'status': 'failure', 'error': 'No filter data not found.'}, 404

        return jsonify({'status': 'success', 'data': data}), 200

    else:
        logged = login_required(request.headers.get('Authorization').split()[1])
        if not logged:
            return {}, 401
        u = models.User.query.get(logged)
        data = request.get_json()
        pref = models.FilterPreference.query.get(u.id)
        try:
            pref.selected_prayers = data['selected_prayers']
            pref.minimum_participants = data['minimum_participants']
            pref.same_gender = data['same_gender']
            db.session.commit()
            
        except Exception:
            return {'status': 'failure', 'error': 'data format is incorrect'}, 400
        return {'status': 'success'}, 200


@user_view.route('/report', methods=['POST'])
def report():
    logged = login_required(request.headers.get('Authorization').split()[1])
    if not logged:
        return {}, 401

    data = request.get_json()

    if 'prayer_id' not in data or 'category' not in data:
        return jsonify({'status': 'failure', 'error': 'Supply all necessary info.'}), 400

    user_data = models.User.query.get(logged).public_info()

    payload = {
        "blocks": [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Prayer Report\n>*Prayer ID*\n>{prayer_id}\n>\n>*Reporter ID*\n>{user_id}\n>\n>*Full Name*\n>{full_name}\n>\n>*Email Address*\n>{email}\n>\n>*Category*\n>{category}\n>\n>*Description*\n>{description}".format(
                    prayer_id=data['prayer_id'], user_id=logged, full_name=user_data['full_name'],
                    email=user_data['email'], category=data['category'], description=data['description'])
            }
        }]
    }

    # Send report to slack
    r = requests.post(os.environ.get('SLACK_REPORT_CHANNEL'), json=payload)

    return {}, r.status_code


@user_view.route('/device-token', methods=['POST', 'DELETE'])
def user_device_token():
    logged = login_required(request.headers.get('Authorization').split()[1])
    if request.method == 'POST':
      if not logged:
          return {}, 401

      data = request.get_json()
      u = models.User.query.get(logged)
      u.device_token = data['token']
      db.session.commit()
      
      return {'status': 'success'}, 200
    
    else:
        user = models.User.query.get(logged)
        user.device_token = None
        db.session.commit()
        
        return {'status': 'success'}, 200
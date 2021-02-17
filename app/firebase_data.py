from firebase_admin import credentials, initialize_app
from firebase_admin import auth
from firebase_admin.auth import InvalidIdTokenError
import os
import json

certificate = {
  "type": os.environ.get('FIREBASE_TYPE'),
  "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
  "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
  "private_key": os.environ.get('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
  "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
  "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
  "auth_uri": os.environ.get('FIREBASE_AUTH_URI'),
  "token_uri": os.environ.get('FIREBASE_TOKEN_URI'),
  "auth_provider_x509_cert_url": os.environ.get('FIREBASE_AUTH_PROVIDER_URL'),
  "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_CERT_URL'),
}

with open("wahdapp-firebase.json", "w") as f:
    f.write(json.dumps(certificate))

cred = credentials.Certificate("wahdapp-firebase.json")
firebase_app = initialize_app(cred)

def login_required(token):
    """ Returns UID from Firebase response """
    try:
        return auth.verify_id_token(token, firebase_app)['uid']
    except InvalidIdTokenError:
        return False

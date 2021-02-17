from flask import Flask
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
import os
from os.path import join, dirname
from dotenv import load_dotenv
from uuid import UUID

from .extensions import db

dotenv_path = join(dirname(dirname(__file__)), '.env') # 2 dirnames to go to parent directory
load_dotenv(dotenv_path)

def register_extensions(app):
    db.init_app(app)
    ma = Marshmallow(app)
    migrate = Migrate(app, db)

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')
    register_extensions(app)

    return app

app = create_app()

from views.prayer import prayer_view
from views.user import user_view

app.register_blueprint(prayer_view)
app.register_blueprint(user_view)

if __name__ == '__main__':
    app.run()

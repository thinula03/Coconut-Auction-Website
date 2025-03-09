from flask import Flask
from config import Config
from database import init_db, db
from flask_login import LoginManager
from routes.auth import auth
from routes.auction import auction

app = Flask(__name__)
app.config.from_object(Config)

init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Register Blueprints
app.register_blueprint(auth)
app.register_blueprint(auction)

if __name__ == "__main__":
    app.run(debug=True)

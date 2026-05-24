from api.app_factory import create_app
from config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT


app = create_app()
socketio = app.config["socketio"]


if __name__ == "__main__":
    socketio.run(app, host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, allow_unsafe_werkzeug=True)

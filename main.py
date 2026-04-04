from api.app_factory import create_app
from config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT


app = create_app()


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)

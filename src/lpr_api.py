import os
import cv2
import json
import requests

from functools import wraps

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from lpr import do_detect


app = Flask(__name__)

# TODO: Be aware of this. Worked when dev. Make it suitable for prod
# VALIDATE_TOKEN_URL = 'http://192.168.195.225:8001/api/validate-token/'
VALIDATE_TOKEN_URL = 'https://ai.tucanoar.com/api/validate-token/'
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif']


class AuthException(Exception):
    status_code = 401
    message = 'Authorization failed'

    def __init__(self, message=None, status_code=None, payload=None):
        Exception.__init__(self)
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(AuthException)
def handle_auth_exception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def validate_token(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'Authorization' not in request.headers:
            raise AuthException('Authorization header not provided')

        try:
            response = requests.request(
                url=VALIDATE_TOKEN_URL,
                method='get',
                headers={'Authorization': request.headers['Authorization']}
            )
        except requests.exceptions.ConnectionError:
            raise AuthException('Authentication server is unreachable')

        if response.status_code != 200:
            raise AuthException(response.json()['detail'])

        return func(*args, **kwargs)
    return wrapper


def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def is_busy():
    with open('src/database.json', 'r') as json_file:
        data = json.load(json_file)
    if(data['flag_occupied'] == "BUSY"):
        return True
    else:
        with open('src/database.json', 'w') as json_file:
            data['flag_occupied'] = "BUSY"
            json.dump(data, json_file)
        return False


def not_busy():
    with open('src/database.json', 'r') as json_file:
        data = json.load(json_file)

    with open('src/database.json', 'w') as json_file:
        data['flag_occupied'] = "NOT BUSY"
        json.dump(data, json_file)

    print("NOT BUSY", flush=True)


@app.route('/detect/', methods=['POST'])
@validate_token
def upload_file():
    if is_busy():
        resp = jsonify({'message': 'Service is being used'})
        resp.status_code = 400
        return resp

    if 'file' not in request.files:
        resp = jsonify({'message': 'No file part in the request'})
        resp.status_code = 400
        not_busy()
        return resp

    file_1 = request.files['file']

    if file_1.filename == '':
        resp = jsonify({'message': 'No file selected for uploading'})
        resp.status_code = 400
        not_busy()
        return resp

    if file_1 and allowed_file(file_1.filename):
        filename = secure_filename(file_1.filename)

        file_1.save(os.path.join("./", filename))
        img = cv2.imread(f"./{filename}")

        detections = do_detect(img)
        print("\ndetections", flush=True)
        print(detections, flush=True)
        resp = jsonify({'message': detections})
        resp.status_code = 201
        not_busy()
        return resp

    else:
        resp = jsonify({
            'message': f'Allowed file types are {ALLOWED_EXTENSIONS}'})
        resp.status_code = 400
        not_busy()
        return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='5000')

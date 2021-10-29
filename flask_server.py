from flask import Flask, json, request
from flask_cors import CORS, cross_origin
from flask import send_file
from werkzeug.utils import secure_filename
import os
import main
import config
import glob
import uuid

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
#CORS(app, max_age=3600, resources={r"*": {"origins": ["*","https://ban-sc.idc.tarento.com"]}})

subtitle_dir = config.SUBTITLE_DIR
speaker_diarization_dir = config.SPEAKER_DIARIZATION_DIR

app.config['UPLOAD_PATH'] = config.UPLOAD_DIR
if not os.path.isdir(app.config['UPLOAD_PATH']):
    os.mkdir(app.config['UPLOAD_PATH'])

@app.route('/gen_srt_from_youtube_url',methods=['POST'])
@cross_origin()
def gen_srt_from_youtube_url():
    body = request.get_json()
    input = body["url"]
    language = body["language"]
    result = main.flaskresponse(input,language,input_format='url',output_format='srt')
    if(result):
        tmp = json.dumps(result)
        #tmp.headers.add('Access-Control-Allow-Origin', 'https://ban-sc.idc.tarento.com')
        return tmp
    else:
        return json.dumps({'gen_srt_from_youtube_url':'false'})

@app.route('/gen_srt_from_file',methods=['POST'])
@cross_origin()
def gen_srt_from_file():
    body = request.get_json()
    input_ =body["file_name"]
    input='uploads/'+input_
    language = body["language"]
    result = main.flaskresponse(input,language,input_format='file',output_format='srt')
    if(result):
        tmp = json.dumps(result)
        #tmp.headers.add('Access-Control-Allow-Origin', 'https://ban-sc.idc.tarento.com')
        return tmp
    else:
        return json.dumps({'gen_srt_from_file':'false'})

@app.route('/gen_speaker_diarization_from_file',methods=['POST'])
@cross_origin()
def gen_speaker_diarization_from_file():
    body = request.get_json()
    input_ = body["file_name"]
    input='uploads/'+input_
    language = body["language"]
    result = main.flaskresponse(input,language,input_format='file',output_format='diarization')
    if(result):
        tmp = json.dumps(result)
        #tmp.headers.add('Access-Control-Allow-Origin', 'https://ban-sc.idc.tarento.com')
        return tmp
    else:
        return json.dumps({'gen_speaker_diarization_from_file':'false'})

@app.route('/get_srt/<filename>',methods=['GET'])
@cross_origin()
def get_srt(filename):
    try:
        return send_file(subtitle_dir+str(filename), as_attachment=True)
    except:
       return json.dumps({'get_srt':'false'})

@app.route('/get_speaker_diarization/<filename>',methods=['GET'])
@cross_origin()
def get_speaker_diarization(filename):
    try:
        return send_file(speaker_diarization_dir+str(filename), as_attachment=True)
    except:
        return json.dumps({'get_speaker_diarization':'false'})

@app.route('/upload',methods=['POST'])
@cross_origin()
def upload():
    try:
        if not os.path.isdir(app.config['UPLOAD_PATH']):
            os.mkdir(app.config['UPLOAD_PATH'])
        uploaded_file = request.files['file']
        filename = secure_filename(uploaded_file.filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
        return_path = str(os.path.join(app.config['UPLOAD_PATH'], filename))
        file_unique=str(uuid.uuid1())+'.wav'
        new_path = str(os.path.join(app.config['UPLOAD_PATH'],file_unique))
        os.rename(return_path, new_path)
        return json.dumps({'uploaded_file , please make sure copy this file name  for further operations ': file_unique })

    except:
        return json.dumps({'upload':'false'})

if __name__ == '__main__':
    app.run(host = "0.0.0.0", port=5001, debug=True)

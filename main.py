import grpc
from stub.speech_recognition_open_api_pb2_grpc import SpeechRecognizerStub
from stub.speech_recognition_open_api_pb2 import Language, RecognitionConfig, RecognitionAudio, \
    SpeechRecognitionRequest
import wave
from grpc_interceptor import ClientCallDetails, ClientInterceptor
import uuid
import pafy
import time
from pydub import AudioSegment
from pydub.silence import split_on_silence
import os
import subprocess
import generate_chunks 
import youtube_dl
import requests
import config
import json
import time
from pathlib import Path
from argparse import ArgumentParser


class GrpcAuth(grpc.AuthMetadataPlugin):
    def __init__(self, key):
        self._key = key

    def __call__(self, context, callback):
        callback((('rpc-auth-header', self._key),), None)


class MetadataClientInterceptor(ClientInterceptor):

    def __init__(self, key):
        self._key = key

    def intercept(
            self,
            method,
            request_or_iterator,
            call_details: grpc.ClientCallDetails,
    ):
        new_details = ClientCallDetails(
            call_details.method,
            call_details.timeout,
            [("authorization", "Bearer " + self._key)],
            call_details.credentials,
            call_details.wait_for_ready,
            call_details.compression,
        )

        return method(request_or_iterator, new_details)

def get_auth_token():
    try:
        res  = requests.post(config.LOGIN,json={"userName": config.USER,"password":config.PASS})
        auth_token = res.json()['data']['token']
        print(" Authentication successful \n")
        return auth_token
        
    except Exception as e:
        print('Error in authentication {}'.format(e),exc_info=True )
        return None

def get_model_id(token, src_lang_code,tgt_lang_code):
    headers = {
    'auth-token': token
            }
    response = requests.get(config.FETCH_MODEL, headers=headers)
    response = json.loads(response.content)['data']
    for entry in response:
        if entry['target_language_code'] == tgt_lang_code and\
            entry['source_language_code'] == src_lang_code and\
            entry['status'] == 'ACTIVE' and\
            'AAI4B' in entry['description']:
#             print(json.dumps(entry, indent =2))
            return entry['model_id']

def get_translation( token, model_id, src_lang_code, tgt_lang_code, text):
    # token = get_auth_token()
    headers = {
        'auth-token': token,
        'Content-Type': 'application/json',
    }
    # model_id = get_model_id(token, src_lang_code, tgt_lang_code)
    data = { "model_id":model_id, "source_language_code":src_lang_code, "target_language_code":tgt_lang_code, "src_list":[ { "src":text } ] }

    response = requests.post(config.TRANSLATE_SEN, headers=headers, data=json.dumps(data))
    return json.loads(response.content)['data'][0]['tgt']

def read_audio():
    with wave.open('saved_audio_new.wav', 'rb') as f:
        return f.readframes(f.getnframes())


def transcribe_audio_bytes(stub):
    language = "hi"
    audio_bytes = read_audio()
    lang = Language(value=language, name='Hindi')
    config = RecognitionConfig(language=lang, audioFormat='MP3', transcriptionFormat='TRANSCRIPT',
                               enableAutomaticPunctuation=1)
    audio = RecognitionAudio(audioContent=audio_bytes)
    request = SpeechRecognitionRequest(audio=audio, config=config)

    # creds = grpc.metadata_call_credentials(
    #     metadata_plugin=GrpcAuth('access_key')
    # )
    try:
        response = stub.recognize(request)

        print(response.transcript)
    except grpc.RpcError as e:
        e.details()
        status_code = e.code()
        print(status_code.name)
        print(status_code.value)


def transcribe_audio_url(stub):
    language = "hi"
    url = "https://codmento.com/ekstep/test/changed.wav"
    lang = Language(value=language, name='Hindi')
    config = RecognitionConfig(language=lang, audioFormat='WAV', enableAutomaticPunctuation=True)
    audio = RecognitionAudio(audioUri=url)
    request = SpeechRecognitionRequest(audio=audio, config=config)

    response = stub.recognize(request)

    print(response.transcript)


def get_srt_audio_bytes(stub):
    language = "hi"
    audio_bytes = read_audio()
    lang = Language(value=language, name='Hindi')
    config = RecognitionConfig(language=lang, audioFormat='WAV', transcriptionFormat='SRT',
                               enableInverseTextNormalization=False)
    audio = RecognitionAudio(audioContent=audio_bytes)
    request = SpeechRecognitionRequest(audio=audio, config=config)

    # creds = grpc.metadata_call_credentials(
    #     metadata_plugin=GrpcAuth('access_key')
    # )
    response = stub.recognize(request)

    print(response.srt)




def get_srt_audio_url(stub):
    language = "hi"
    url = "https://codmento.com/ekstep/test/changed.wav"
    lang = Language(value=language, name='Hindi')
    config = RecognitionConfig(language=lang, audioFormat='WAV', transcriptionFormat='SRT')
    audio = RecognitionAudio(audioUri=url)
    request = SpeechRecognitionRequest(audio=audio, config=config)

    response = stub.recognize(request)

    print(response.srt)




def read_given_audio(single_chunk):
    with wave.open(single_chunk, 'rb') as f:
        return f.readframes(f.getnframes())

def convert(seconds):
    try:
        milli=str(seconds).split('.')[-1][:2]
    except:
        milli='00'
    return time.strftime(f"%H:%M:%S,{milli}", time.gmtime(seconds))


def get_text_from_wavfile_any_length(stub,audio_file,lang, translation):

    langfull={"hi":"Hindi","mr":"Marathi","en":"English","gu":"Gujarati"}

    output_file_path,start_time_stamp,end_time_stamp=generate_chunks.split_and_store(audio_file)
    result = ''
    token = get_auth_token()
    model_id = get_model_id(token, lang, "en")
    for j in range(len(start_time_stamp)):
        single_chunk=os.path.join(output_file_path ,f'chunk{j}.wav')
        audio_bytes = read_given_audio(single_chunk)
        lang1 = Language(value=lang, name=langfull[lang])
        config = RecognitionConfig(language=lang1, audioFormat='MP3', transcriptionFormat='TRANSCRIPT',
                                enableAutomaticPunctuation=1)
        audio = RecognitionAudio(audioContent=audio_bytes)
        request = SpeechRecognitionRequest(audio=audio, config=config)

        # creds = grpc.metadata_call_credentials(
        #     metadata_plugin=GrpcAuth('access_key')
        # )
        try:
            response = stub.recognize(request)
            print(j+1)
            result+=(str(j+1))
            result+='\n'
            print(convert(start_time_stamp[j]),end=' --> ')
            result+=convert(start_time_stamp[j])
            result+=' --> '
            print(convert(end_time_stamp[j] ))
            result+=convert(end_time_stamp[j])
            result+='\n'
            print(response.transcript)
            if(translation == True):
                translated_result = get_translation(token, model_id, lang,"en",response.transcript)
                print(translated_result)
                result+=translated_result
            else:
                result+=response.transcript
            print()
            result+='\n\n'

        except grpc.RpcError as e:
            e.details()
            status_code = e.code()
            print(status_code.name)
            print(status_code.value)
    
    with open("subtitle.srt", "w") as text_file:
        text_file.write(result)


def download_youtubeaudio(url, output_file='saved_audio.wav'):
    try:
        filepath = str(uuid.uuid4())+".wav"
        ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': filepath,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
            
        }]
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        subprocess.call(["ffmpeg -i {} -ar {} -ac {} -bits_per_raw_sample {} -vn {}".format(filepath, 16000, 1, 16, output_file)], shell=True)
        os.remove(filepath)
        return output_file
    except Exception as e:
        print(e)


if __name__ == '__main__':


    parser = ArgumentParser()

    parser.add_argument("--url",help="youtub video  url",type=str,required=True)
    parser.add_argument("--lang_code",help="language of video",type=str,required=True,)
    parser.add_argument("--trans_eng",help=" eng Translate ",type=str,)
    args = parser.parse_args()

    translate_eng=False
    try:
        trans_eng=(args.trans_eng).lower()
        if (trans_eng)=='true' or  (trans_eng)=='yes':
            translate_eng=True
    except:
        pass
    print(translate_eng)





    url =args.url 
    subprocess.call(['youtube-dl {}'.format(url)], shell=True)
    audio_file = download_youtubeaudio(url)

    key = "mysecrettoken"
    interceptors = [MetadataClientInterceptor(key)]
    with grpc.insecure_channel('52.12.126.83:50051') as channel:
        channel = grpc.intercept_channel(channel, *interceptors)
        stub = SpeechRecognizerStub(channel)
        # transcribe_audio_url(stub)
        # transcribe_audio_bytes(stub)
        # get_srt_audio_url(stub)
        # get_srt_audio_bytes(stub)
        get_text_from_wavfile_any_length(stub,audio_file,lang=args.lang_code, translation=translate_eng)

import wave
import uuid
import time
import os
import subprocess
import youtube_dl
import requests
import config
import json
from pydub import AudioSegment
from pydub.utils import make_chunks
import pysrt
import re
import os

def read_given_audio(audio_file):
    with wave.open(audio_file, 'rb') as f:
        return f.readframes(f.getnframes())

def convert(seconds):
    try:
        milli=str(seconds).split('.')[-1][:2]
    except:
        milli='00'
    return time.strftime(f"%H:%M:%S,{milli}", time.gmtime(seconds))

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
        subprocess.call(["ffmpeg -y -i {} -ar {} -ac {} -bits_per_raw_sample {} -vn {}".format(filepath, 16000, 1, 16, output_file)], shell=True)
        os.remove(filepath)
        return output_file
    except Exception as e:
        print(e)

def chunk_audio(wav_file,output_dir):
    '''
    creates 5 min chunks of the given wav_file and saves them
    '''
    audio = AudioSegment.from_file(wav_file , "wav") 
    chunk_length_ms = 300000
    chunks = make_chunks(audio, chunk_length_ms)
    chunk_paths = []
    for i, chunk in enumerate(chunks):
        chunk_path = os.path.join(output_dir,"chunk{0}.wav".format(i))
        chunk.export(chunk_path, format="wav")
        chunk_paths.append(chunk_path)

    return chunk_paths
    
def merge_srt_files(srt_files,final_file="subtitle.srt"):
    
    for i in range(1,len(srt_files)):
        subs = pysrt.open(srt_files[i])
        min_to_offset = 5 * i
        subs.shift(minutes=min_to_offset)
        subs.save(srt_files[i], encoding='utf-8')

    if os.path.exists('subtitles'):
        pass
    else:
        os.makedirs('subtitles')

    with open('subtitles/'+final_file,"wb") as output_file:
        for f in srt_files:
            with open(f, "rb") as infile:
                output_file.write(infile.read())
    outputdict={}
    filename='subtitles/'+final_file
    with open(filename) as f:
        lines = f.readlines()
    one_line=''
    for lin in lines:
        one_line=one_line+''+lin
    outputdict['srt']=one_line
    outputdict['filename']=final_file
    return(filename,outputdict)


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

def translate_srt_file(srt_file,src_lang):
    token = get_auth_token()
    model_id = get_model_id(token, src_lang, "en")
    subs = pysrt.open(srt_file)
    for i in range(len(subs)):
        print("Translating {} out of {}".format(i,len(subs)))
        subs[i].text = get_translation(token, model_id, src_lang,"en",subs[i].text)

    subs.save(srt_file, encoding='utf-8')


def store_str_into_file(srt_response,output_file_path):

    list1=[]
    list2=[]
    list3=[]
    list4=[]
    list5=[]

    list1=(re.split('(\d+\s\d\d:\d\d:\d\d,[\d]+\s-->\s\d\d:\d\d:\d\d,[\d]+)', srt_response))
    list2=list1[1: :2]
    list3=[]
    for li in list2:
        list3.extend(li.split(' ',1))
        
    list4=list1[2::2]
    list4=[li.strip() for li in list4]
    count=0
    count1=0
    list5=[]
    while count<len(list4):
        
        list5.append(list3[count1])
        count1=count1+1
        list5.append(list3[count1])
        count1=count1+1
        list5.append(list4[count])
        count=count+1
        list5.append('\n')


    with open(output_file_path, 'w') as file_handler:
        for item in list5:
            if item!='\n':
                file_handler.write("{}\n".format(item))
            else:
                file_handler.write("{}".format(item))
                
    

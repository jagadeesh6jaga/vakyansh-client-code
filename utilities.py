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
import shutil
from datetime import datetime, timedelta

def read_given_audio(audio_file):
    with wave.open(audio_file, 'rb') as f:
        return f.readframes(f.getnframes())

def convert(seconds):
    try:
        milli=str(seconds).split('.')[-1][:2]
    except:
        milli='00'
    return time.strftime(f"%H:%M:%S,{milli}", time.gmtime(seconds))


def download_youtubeaudio(url):
    try:
        filepath = str(uuid.uuid4())+".wav"
        output_file=str(uuid.uuid1())+".wav"
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

def translate_to_english(user_translation_choice):
    translate_to_en=False
    try:
        trans_eng=(user_translation_choice).lower()
        if (trans_eng)=='true' or  (trans_eng)=='yes':
            translate_to_en=True
    except:
        pass
    return translate_to_en

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

def modify_srt_for_long_sen(file_name_srt , num_words_div):

    file_name=file_name_srt 

    # num_words_div  value  is an integer , it represents  each sentence should  have the number of words less than  num_words_div  
    num_words_divide=num_words_div

    final_start_timmings=[]
    final_end_timmings=[]


    all_sentences = pysrt.open(file_name)

    for  subs in all_sentences:
        first_sub = subs    
        if len(first_sub.text.split())> num_words_divide:
            percentage=[]
            loops=int(len(first_sub.text.split())/num_words_divide)
            
            each_part=100/len(first_sub.text.split())
            for loop in range(loops):
                percentage.append(each_part*num_words_divide)
            #percentage.append(each_part*(len(first_sub.text.split())%num_words_divide))

            time_resp_per=[]
            seconds_only=first_sub.duration.minutes *60 +first_sub.duration.seconds
            full_seconds=str(seconds_only)+'.'+str(first_sub.duration.milliseconds)
            time_sec_mill=float(full_seconds)
            for i in percentage:

                time_resp_per.append(i*time_sec_mill/100)
            time_resp_per=[round(time_round,3)  for time_round in time_resp_per]
            start_timmings=[]
            start_timmings.append("%02d" % int(first_sub.start.hours)+':'+"%02d" % int(first_sub.start.minutes)+':'+"%02d" % int(first_sub.start.seconds)+','+"%02d" % int(first_sub.start.milliseconds))
            for j in range(len(time_resp_per)):
                first_sub.shift(seconds=time_resp_per[j]) 
                start_timmings.append("%02d" % int(first_sub.start.hours)+':'+"%02d" % int(first_sub.start.minutes)+':'+"%02d" % int(first_sub.start.seconds)+','+"%02d" % int(first_sub.start.milliseconds))

            #start_timmings[1]='00:01:18,00'

            final_start_timmings.append(start_timmings)

    inx=0
    all_sentences = pysrt.open(file_name)
    for  subs in all_sentences:
        first_sub =subs
        if len(first_sub.text.split())> num_words_divide:
            
            end_time=first_sub.end
            end_timmings=[]
            for timmings in final_start_timmings[inx][1:]:
                if timmings.split(',')[1]=='00' or timmings.split(',')[1]=='000' or timmings.split(',')[1]=='001' or timmings.split(',')[1]=='01' or timmings.split(',')[1]=='002' or timmings.split(',')[1]=='02':
                    changing_minut=timmings.split(':')[2]
                    changing_minut=changing_minut.split(',')
                    milli_sec=timmings.split(':')[0]+':'+timmings.split(':')[1]+':'+'%02d'%(int(changing_minut[0]))+','+str('00')
                else:
                    milli_change=int(timmings.split(',')[1])
                    milli_change=milli_change-5               
                    milli_sec=timmings.split(',')[0]+','+str(abs(milli_change))


                end_timmings.append(milli_sec)


            end_timmings.append("%02d" % int(end_time.hours)+':'+"%02d" % int(end_time.minutes)+':'+"%02d" % int(end_time.seconds)+','+"%02d" % int(end_time.milliseconds))

            final_end_timmings.append(end_timmings)
            inx=inx+1



    all_sentences = pysrt.open(file_name)

    global_count=1

    inx1=0

    os.remove(file_name)
    for  subs in all_sentences:
        first_sub = subs
        if len(first_sub.text.split())> num_words_divide:
            with open(file_name,'a') as file_handler:
                
                subtext=[]
                
                count_sub_text=len(final_start_timmings[inx1])
                
                sub_text_list=first_sub.text.split()
                for index in range(count_sub_text): 
                    count=index+1
                    count1=index*num_words_divide
                    count2=count*num_words_divide
                    if index==(count_sub_text-1):
                        subtext.append(' '.join(sub_text_list[count1:]))
                    else:    
                        subtext.append(' '.join(sub_text_list[count1:count2]))

                
                for index in range(len(subtext)):
                    
                    file_handler.write('{}\n'.format(global_count))
                    global_count=global_count+1
                
                    file_handler.write("{} --> {}\n".format(final_start_timmings[inx1][index],final_end_timmings[inx1][index]))
                    
                    file_handler.write("{}\n\n".format(subtext[index]))
                inx1=inx1+1
        else:
            with open(file_name,'a') as file_handler:
                end_time=first_sub.end
                start=("%02d" % int(first_sub.start.hours)+':'+"%02d" % int(first_sub.start.minutes)+':'+"%02d" % int(first_sub.start.seconds)+','+"%02d" % int(first_sub.start.milliseconds))
                end=("%02d" % int(end_time.hours)+':'+"%02d" % int(end_time.minutes)+':'+"%02d" % int(end_time.seconds)+','+"%02d" % int(end_time.milliseconds))
                
                file_handler.write('{}\n'.format(global_count))
                global_count=global_count+1
                file_handler.write("{} --> {}\n".format(start,end))
                file_handler.write("{}\n\n".format(first_sub.text))




def split_aud_into_chunks_on_speech_recognition(text_file,aud_file,output_dir_name='speaker_recognition_chunks'):
    
    trans_chunk_trunc_limit_milli_sec = 60000
    if os.path.exists(output_dir_name):
        shutil.rmtree(output_dir_name)
    os.makedirs(output_dir_name)
    audio_file= aud_file
    audio = AudioSegment.from_wav(audio_file)
    txt_file=text_file
    with open(txt_file) as f:
        lines = f.readlines()
    start_times=[lin.split()[0].strip() for lin in lines]
    end_times=[lin.split()[2].strip() for lin in lines]
    speaker_number=[lin.split()[4] for lin in lines]
    final_start_milli_sec=[]
    final_end_milli_sec=[]

    for inx in range(len(start_times)):
        times1=start_times[inx]
        timet1 = datetime.strptime(times1,"%H:%M:%S,%f")
        milli_sec=int(timet1.microsecond/1000)
        total_time_in_milli_start = (((timet1.hour*60*60)+(timet1.minute*60)+(timet1.second))*1000)+milli_sec
        final_start_milli_sec.append(total_time_in_milli_start)
        times1=end_times[inx]
        timet1 = datetime.strptime(times1,"%H:%M:%S,%f")
        milli_sec=int(timet1.microsecond/1000)
        total_time_in_milli_end = (((timet1.hour*60*60)+(timet1.minute*60)+(timet1.second))*1000)+milli_sec
        time_dur_milli = total_time_in_milli_end - total_time_in_milli_start
        if time_dur_milli > trans_chunk_trunc_limit_milli_sec:
            total_time_in_milli_end = total_time_in_milli_start + trans_chunk_trunc_limit_milli_sec
        final_end_milli_sec.append(total_time_in_milli_end)
    for times in range(len(final_start_milli_sec)):
        start=final_start_milli_sec[times]
        end=final_end_milli_sec[times]
        audio_chunk=audio[start:end]
        if end>start:
            audio_chunk.export( output_dir_name+"/audio_chunk_{}_{}.wav".format(end,speaker_number[times]), format="wav")



    return output_dir_name

def noise_suppression(dir_name):    
    subprocess.call(["python -m denoiser.enhance --dns48 --noisy_dir {} --out_dir {} --sample_rate {} --num_workers {} --device cpu".format(dir_name, dir_name, 16000, 1)], shell=True)

def media_conversion(file_name, dir_name):   
    subprocess.call(["ffmpeg -i {} -ar {} -ac {} -bits_per_raw_sample {} -vn {}".format(file_name, 16000, 1, 16, os.path.join(dir_name,'input_audio.wav'))], shell=True)    
    
    

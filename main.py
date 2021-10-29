import grpc
from stub.speech_recognition_open_api_pb2_grpc import SpeechRecognizerStub
from stub.speech_recognition_open_api_pb2 import Language, RecognitionConfig, RecognitionAudio, \
    SpeechRecognitionRequest
from grpc_stubs.audio_to_text_pb2_grpc import RecognizeStub 
from grpc_stubs.audio_to_text_pb2 import SRTRequest   
from grpc_interceptor import ClientCallDetails, ClientInterceptor
import os
import shutil
import subprocess
import generate_chunks
from utilities import *
import config
from argparse import ArgumentParser
import shutil


MAX_MESSAGE_LENGTH = 50 * 1024 * 1024

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


def gen_srt_limited_duration(stub,audio_file,language,output_file_path,file_unique_id):
    '''
    Given an audio file, generates srt for the first 5 min
    '''
    audio_bytes = read_given_audio(audio_file)
    lang = Language(value=language, name=config.language_code_dict[language])
    recog_config = RecognitionConfig(language=lang, audioFormat='WAV', transcriptionFormat='SRT',
                               enableInverseTextNormalization=False)
    # audio = RecognitionAudio(audioContent=audio_bytes)

    request = SRTRequest(audio=audio_bytes,language=language,user="ajitesh",filename=file_unique_id)
    print("request sent********")
    response = stub.recognize_srt(request)
    print("************************************")
    #result = store_str_into_file(srt_response,output_file_path)
    with open(output_file_path, "w") as text_file:
        text_file.write(response.srt)
        print(response.srt)
        

def gen_srt_full(stub,audio_file,language, translate_to_en):
    '''
    Given an audio file, generates srt 
    '''
    unique_id=uuid.uuid1()

    file_unique_id=str(unique_id)
    output_dir = 'chunks'+str(unique_id)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    # chunk audio to 5min chunks
    chunk_files = chunk_audio(audio_file,output_dir)
    output_files = []
    for index,chunk in enumerate(chunk_files):
        output_file_path = os.path.join(output_dir,"subtitle{0}.srt".format(index))
        print("Generating subtitle output for chunk {}".format(index))
        gen_srt_limited_duration(stub,chunk,language, output_file_path,file_unique_id)
        output_files.append(output_file_path)
    unique_id=str(unique_id)+'.srt'
    final_srt_file,final_srt_json = merge_srt_files(output_files,unique_id)
    num_words_for_sen_should_less_than=35
    modify_srt_for_long_sen(final_srt_file , num_words_for_sen_should_less_than)

    if translate_to_en:
        print("Translating subtitles to english")
        translate_srt_file(final_srt_file,language)
    shutil.rmtree(output_dir)
    os.remove(audio_file)
    return(final_srt_json)
    

def flaskresponse(url, language):   
        print("url ==== ", url)
        print("language ==", language)

        audio_file = download_youtubeaudio(url)
        key = "mysecrettoken"
        interceptors = [MetadataClientInterceptor(key)]
        # with grpc.insecure_channel('54.213.245.181:50051',options=(('grpc.enable_http_proxy', 0),)) as channel:
        grpc_channel = grpc.insecure_channel('52.13.63.64:50051', options=[('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH)])
        with grpc_channel as channel:
            channel = grpc.intercept_channel(channel, *interceptors)
            stub = RecognizeStub(channel)
            # get_text_from_wavfile_any_length(stub,audio_file,lang=args.lang_code, translation=translate_to_en)
            result = gen_srt_full(stub,audio_file,language, False)
            return(result)

if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument("--url",help="youtub video  url",type=str,required=True)
    parser.add_argument("--lang_code",help="language of video",type=str,required=True,)
    parser.add_argument("--trans_eng",help=" eng Translate ",type=str,)
    args = parser.parse_args()

    translate_to_en = translate_to_english(args.trans_eng)
   
    url = args.url 
    subprocess.call(['youtube-dl {}'.format(url)], shell=True)
    
    audio_file = download_youtubeaudio(url)
    #audio_file="/home/test/Desktop/ASR/OLA/Test calls-20210906T071212Z-001/first112.wav"

    key = "mysecrettoken"
    interceptors = [MetadataClientInterceptor(key)]
    # with grpc.insecure_channel('localhost:50051',options=(('grpc.enable_http_proxy', 0),)) as channel:
    grpc_channel = grpc.insecure_channel('52.13.63.64:50051', options=[('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH)])
    with grpc_channel as channel:
        channel = grpc.intercept_channel(channel, *interceptors)
        # stub = SpeechRecognizerStub(channel)
        stub = RecognizeStub(channel)
        # get_text_from_wavfile_any_length(stub,audio_file,lang=args.lang_code, translation=translate_to_en)
        gen_srt_full(stub,audio_file,args.lang_code, translate_to_en)

import subprocess
import os
import shutil
from pydub import AudioSegment
import time
import tqdm
from utilities import noise_suppression


def split_file_for_denoise(audio_file_for_split,chunk_limit=120000,dir_chunks_denoiser='tmp_denoiser'):

    newAudio = AudioSegment.from_wav(audio_file_for_split)
    if os.path.isdir(dir_chunks_denoiser):
        shutil.rmtree(dir_chunks_denoiser)
    os.makedirs(dir_chunks_denoiser)

    file_names_=[]

    if len(newAudio)>chunk_limit:
        count=0
        count1=0
        for itr in range(int(len(newAudio)/chunk_limit)):
            count1=count1+chunk_limit
            file_names_.append('audio_'+str(count1)+'.wav')
            newAudio_chunk=newAudio[count:count1]
            newAudio_chunk.export(dir_chunks_denoiser+'/audio_'+str(count1)+'.wav', format="wav")
            # print(itr,count,count1)
            count=count1

        last_chunk=(len(newAudio)-count1)
        if last_chunk > 500:
            newAudio_chunk=newAudio[count1:]
            newAudio_chunk.export(dir_chunks_denoiser+'/audio_'+str(len(newAudio))+'.wav', format="wav")
            file_names_.append('audio_'+str(len(newAudio))+'.wav')
    else:
        newAudio.export(dir_chunks_denoiser+'/audio_'+str(len(newAudio))+'.wav', format="wav")
        file_names_.append('audio_'+str(len(newAudio))+'.wav')

    return dir_chunks_denoiser,file_names_


def denoise_all_files(folder):

    tmp_file2='tmp2'
    tmp_file1='tmp1'
    if os.path.isdir(tmp_file2):
        shutil.rmtree(tmp_file2)
    os.makedirs(tmp_file2)
    
    all_files=os.listdir(folder)

    for file in tqdm.tqdm(all_files):
        if os.path.isdir(tmp_file1):
            shutil.rmtree(tmp_file1)
        os.makedirs(tmp_file1)
        source=folder+'/'+file
        shutil.move(source,tmp_file1)
        print('********************noise supress processing**************')
        noise_suppression(tmp_file1)

        for chunk_file in os.listdir(tmp_file1):
            if 'enhanced' in chunk_file:
                shutil.move(tmp_file1+'/'+chunk_file,tmp_file2)

    shutil.rmtree(tmp_file1)
    shutil.rmtree(folder)
    
    return tmp_file2


def merge_chunks_into_one(final_chunk_folder,file_names_,output_file):
    for files in range(1,len(file_names_)):
        sound1 = AudioSegment.from_wav(final_chunk_folder+'/'+file_names_[0][:-4]+'_enhanced.wav')
        sound2 = AudioSegment.from_wav(final_chunk_folder+'/'+file_names_[files][:-4]+'_enhanced.wav')
        combined_sounds = sound1 + sound2
        combined_sounds.export(final_chunk_folder+'/'+file_names_[0][:-4]+'_enhanced.wav', format="wav")

    old_name = file_names_[0][:-4]+'_enhanced.wav'
    shutil.move(final_chunk_folder+'/'+old_name,output_file)
    shutil.rmtree(final_chunk_folder)


def noise_suppression_extended(file_path,file='input_audio.wav'):
    file = file_path + '/input_audio.wav'
    output_file = file_path + '/input_audio_enhanced.wav'

    folder_after_split,file_names = split_file_for_denoise(file)
    folder_after_denoise = denoise_all_files(folder_after_split)
    merge_chunks_into_one(folder_after_denoise,file_names,output_file)
    

if __name__ == "__main__":
    file_path = 'tmp'
    noise_suppression_extended(file_path)















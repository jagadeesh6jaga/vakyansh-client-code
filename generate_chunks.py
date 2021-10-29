import os
from pathlib import Path
import auditok



def split_and_store(input_audio_file):

    input_audio=input_audio_file

    min_dur = 0.4      # minimum duration of a valid audio event in seconds
    max_dur = 8       # maximum duration of an event
    max_silence = 0.05   # maximum duration of tolerated continuous silence within an event
    energy_threshold = 50 # threshold of detection

    output_path =("audio_chunks_" + \
        "_" + str(min_dur) + \
        "_" + str(max_dur) + \
        "_" + str(max_silence) + \
        "_" + str(energy_threshold))

    Path(output_path).mkdir(parents=True, exist_ok=True)

    audio_regions = auditok.split(
        input_audio,
        min_dur=min_dur,     
        max_dur=max_dur,       
        max_silence=max_silence, 
        energy_threshold=energy_threshold
    )

    start_time_stamp=[]
    end_time_stamp=[]
    for i, r in enumerate(audio_regions):
        filename = r.save(os.path.join(output_path,f"chunk{i}.wav"))
        #print("region saved as: {}".format(filename))
        start_time_stamp.append(r.meta.start)
        end_time_stamp.append(r.meta.end)


    return    output_path,start_time_stamp,end_time_stamp
        
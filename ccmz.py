import math
import zipfile
import json
import io
import requests
from midiutil import SHARPS, FLATS
from midiutil.MidiFile import MIDIFile, MAJOR
import os

class CCMZ:
    def __init__(self):
        self.ver = None
        self.score = None
        self.midi = None

class LibCCMZ:
    @staticmethod
    def download_ccmz(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.content
            raise Exception(f"下载失败: {response.status_code}")
        except Exception as e:
            print(f"ccmz文件下载失败: {e}")
            return None

    @staticmethod
    def read_ccmz(buffer, callback):
        info = CCMZ()
        version = buffer[0]
        info.ver = version
        data = buffer[1:]

        if version == 1:
            zip_file = zipfile.ZipFile(io.BytesIO(data))
            info.score = zip_file.read("data.xml").decode('utf-8')
            info.midi = zip_file.read("data.mid").decode('utf-8')
        elif version == 2:
            data = bytes([v + 1 if v % 2 == 0 else v - 1 for v in data])
            zip_file = zipfile.ZipFile(io.BytesIO(data))
            info.score = zip_file.read("score.json").decode('utf-8')
            info.midi = zip_file.read("midi.json").decode('utf-8')
        callback(info)

    @staticmethod
    def write_midi(data, output):
        ticks_per_beat = 480
        tick_delta = 60
        tick_arpeggio_delta = 120
        tempos = data.get('tempos', [])
        if not tempos or not tempos[0].get('tempo'):
            raise ValueError("Invalid tempo data")
        initial_tempo = tempos[0]['tempo']

        tracks = data.get('tracks', [])
        events = data.get('events', [])
        midi = MIDIFile(len(tracks))
        midi.addText(track=0, time=0, text="Made with love by yfishyon from gangqinpu.com") #水印
        sorted_events = [{} for i in range(0,len(tracks))]
        for event in events:
            if event.get('duration', 0) <= 0 or 'staff' not in event:
                continue
            ev = event.get('event', [])
            if not isinstance(ev, list) or len(ev) < 2:
                continue
            if (event['staff'] - 1) < len(sorted_events) and (event['staff'] - 1) >= 0:
                event['tick'] = round(event['tick'] / tick_delta) * tick_delta
                temp_events = sorted_events[event['staff'] - 1].get(event['tick'])
                if temp_events is None:
                    sorted_events[event['staff'] - 1][event['tick']] = [event]
                else:
                    temp_events.append(event)
        for idx, track in enumerate(tracks):
            midi.addTrackName(idx, 0, track.get('name', f"Track{idx}"))
            midi.addTempo(idx, 0, round(60000000 / initial_tempo))
            midi.addProgramChange(idx, 0, 0, 0)
            midi.addKeySignature(idx, 0, 4, FLATS, MAJOR)
            keys = sorted_events[idx].keys()
            for index, key in enumerate(keys):
                temp_events = sorted_events[idx][key]
                for event in temp_events:
                    pitch = event['event'][1]
                    event['tick'] = round(event['tick']/tick_delta)*tick_delta
                    time = event['tick'] / ticks_per_beat
                    event_duration = event['duration'] / 0.9
                    duration: float
                    if index < len(keys) - 1:
                        tick_duration = sorted_events[idx][list(keys)[index + 1]][0]['tick'] - event['tick']
                        if event_duration / tick_duration > 2:
                            tick_duration = sorted_events[idx][list(keys)[index + 2]][0]['tick'] - sorted_events[idx][list(keys)[index + 1]][0]['tick']
                            time = sorted_events[idx][list(keys)[index + 1]][0]['tick'] / ticks_per_beat
                        duration = tick_duration / ticks_per_beat
                    else:
                        duration = event_duration /ticks_per_beat

                    midi.addNote(idx, 0, pitch, time, duration, 80)

        with open(output, 'wb') as f:
            midi.writeFile(f)
        return output

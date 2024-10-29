from sys import exit, stderr
from pydub import AudioSegment
from pydub.playback import play
import signal
import pyaudio
import pyaudio
import threading
import os
import argparse

parser = argparse.ArgumentParser(
	prog='VoiceActor',
	description='VoiceActor reproduces an mp3 soundfile and then, sends its signals to a audio device'
)

parser.add_argument('--root-audio-path', default="audios")
parser.add_argument('--file', '-f')

args = parser.parse_args()

def validate_arguments(args):
	if args.file == None:
		raise Exception('the file to be played (with flag --file) must be provided')

def sigint_handler(signal, frame):
	print('interrupt')
	exit(0)

signal.signal(signal.SIGINT, sigint_handler)

def load_audio_file(filename: str):
	audio = AudioSegment.from_mp3(filename)
	return audio

def pick_audio_devices_indexes(p, audio, *device_names):
	devices = []
	devices_names = []

	print('listing audio devices with names: ', device_names)

	for name in device_names:
		for i in range(p.get_device_count()):
			dev = p.get_device_info_by_index(i)

			device_sample_rate = int(dev['defaultSampleRate'])

			if name == dev['name'] and name not in devices_names:
				if device_sample_rate == audio.frame_rate and dev['maxOutputChannels'] >= audio.channels:
					print(f"FOUND: DEVICE_NAME = {dev['name']}, DEFAULT_SAMPLE_RATE = {dev['defaultSampleRate']}, MAX_CHANNELS = {dev['maxOutputChannels']}")

					devices.append(i)
					devices_names.append(dev['name'])

	return devices

def open_streams(p, audio, indexes):
	print('Opening devices streams')

	if len(indexes) == 0:
		raise Exception('no devices indexes provided')

	streams = []

	for idx in indexes:
		device = p.get_device_info_by_index(idx)

		stream = p.open(
			format=p.get_format_from_width(audio.sample_width),
			channels=audio.channels,
			rate=int(device['defaultSampleRate']),
			output=True,
			output_device_index=idx)

		if stream == None:
			raise Exception(f'failure opening stream for device index: %d' % idx)

		else:
			streams.append(stream)


	return streams

def run_streams_as_threads(audio, streams):
	global args
	print(f'playing sound {os.path.join(args.root_audio_path, args.file)} to streams')
	
	def play_sound(a, stream):
		raw_audio_data = a.raw_data
		stream.write(raw_audio_data)
		stream.stop_stream()
		stream.close()

	threads = []

	for stream in streams:
		th = threading.Thread(target=play_sound, args=[audio, stream])
		threads.append(th)
		th.start()

	# waiting for all threads to finish
	for th in threads:
		th.join()

try:
	validate_arguments(args)

	audio = load_audio_file(os.path.join(args.root_audio_path, args.file))

	p = pyaudio.PyAudio()
	
	devices_indexes = pick_audio_devices_indexes(p, audio, 'Fones de ouvido (Realtek(R) Aud', 'CABLE Input (VB-Audio Virtual C')
	
	streams = open_streams(p, audio, devices_indexes)

	run_streams_as_threads(audio, streams)

	p.terminate()

	print('done')

except Exception as err:
	stderr.write(str(err))
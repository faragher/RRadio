import io
#import pyaudio
import pycodec2
import numpy as np
#import simpleaudio as sa

#filename = 'packed.c2'

#p = pyaudio.PyAudio()
#stream = p.open(format = pyaudio.paInt16,
#                channels = 1,
#                rate = 8000,
#                output = True)


#target_mode = 1600



def CheckMode(codec_mode):
  global supported_modes
  try:
    enabled_modes = supported_modes
  except:
    enabled_modes = {1200,1400,1600,3200}
  if codec_mode in enabled_modes:
    return True
  else:
    return False

def DecodeC2(codec_mode, byte_payload):
  c2 = pycodec2.Codec2(codec_mode)
  encoded = io.BytesIO(byte_payload)
  decoded = b''
  bytes_per_frame = c2.bits_per_frame()//8
  ingest = encoded.read(bytes_per_frame)
  while len(ingest)>0:
    decoded += c2.decode(ingest).tobytes()
    ingest = encoded.read(bytes_per_frame)
  return decoded

def EncodeC2(codec_mode, byte_payload):
  c2 = pycodec2.Codec2(codec_mode)
  decoded = io.BytesIO(byte_payload)
  bytes_per_frame = c2.samples_per_frame() * 2 #INT16 is two bytes
  encoded = b''
  ingest = decoded.read(bytes_per_frame)
  while len(ingest)>=bytes_per_frame:
    buffer = np.frombuffer(ingest, np.int16)
    buffer = c2.encode(buffer)
    encoded += buffer
    ingest = decoded.read(bytes_per_frame)
  return encoded


# Debug code

## Load compressed audio
#with open(filename,'rb') as input:
#  file_payload = input.read()
#print(CheckMode(1200))
#d = DecodeC2(1200,file_payload)
#stream.write(d)

## Load wav/raw PCM audio
#with open('Test8000.wav','rb') as output:
#  file_payload = output.read()
#e = EncodeC2(target_mode,file_payload)
#d = DecodeC2(target_mode,e)


# PyAudio
#stream.write(d)

# SimpleAudio
#play_obj = sa.play_buffer(d, 1, 2, 8000)
#play_obj.wait_done()

#stream.close()
#p.terminate()
#print("PA Terminated")

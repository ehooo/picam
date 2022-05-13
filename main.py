# Web streaming based on
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import json
import mimetypes
import os.path

import logging
import socketserver
from pathlib import Path
from string import Template
from threading import Condition, Lock
from http import server
from time import sleep
from urllib.parse import urlparse, parse_qs

from PIL import Image

try:
    import picamera
except (ImportError, OSError):
    picamera = type('', (), {})
    picamera.PiCameraNotRecording = KeyError
    picamera.PiCameraMMALError = Exception

BASE_PATH = os.path.dirname(Path(__file__).absolute())
FRAMERATE = 5


class PiCam(object):
    FRAMERATES = [5, 10, 15, 20, 25, 30]
    ROTATION_OPTIONS = [0, 90, 180, 270]
    UNLOCK_SEC = 1

    def __init__(self, framerate=FRAMERATE, resolution=720):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()
        self.camera = None
        self._framerate = framerate
        self.resolution = resolution
        self.format = 'mjpeg'
        self.rotation_pos = 0
        self.scroll = ['-', '\\', '|', '/']
        self.scroll_pos = 0
        self.stdout = None

    def _get_framerate(self):
        return self._framerate

    def _set_framerate(self, framerate):
        if framerate in self.FRAMERATES:
            self._framerate = framerate
            if self.camera:
                self.camera.framerate = framerate
    framerate = property(_get_framerate, _set_framerate)

    @property
    def width(self):
        return self._resolution

    @property
    def height(self):
        return self._resolution

    def _get_resolution(self):
        return self._resolution

    def _set_resolution(self, resolution):
        self._resolution = resolution
        if self.camera:
            self.camera.resolution = self.width, self.height
    resolution = property(_get_resolution, _set_resolution)

    def blank_frame(self):
        buff = io.BytesIO()
        img = Image.new('RGB', (self.width, self.height), color='black')
        img.save(buff, format='jpeg')
        return buff.getvalue()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            if self.stdout:
                self.scroll_pos += 1
                print(self.scroll[self.scroll_pos % 4], end='\r', file=self.stdout)

            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

    def _setup_camera(self):
        if self.camera is None and hasattr(picamera, 'PiCamera'):
            try:
                self.camera = picamera.PiCamera(
                    resolution='{}x{}'.format(self.width, self.height),
                    framerate=self._framerate,
                )
                # self.camera.exposure_mode = 'night'
                self.camera.rotation = self.rotation
            except picamera.PiCameraMMALError:
                pass
        return self.camera

    def photo(self):
        if self.camera:
            with self.condition:
                self.condition.wait(timeout=1)
            photo = self.frame
        else:
            camera = self._setup_camera()
            camera.start_preview()
            sleep(2)
            self.buffer.seek(0)
            camera.capture(self.buffer, format='jpeg')
            photo = self.buffer.getvalue()
            self.stop()
        return photo

    def start(self):
        camera = self._setup_camera()
        if camera:
            camera.start_recording(self, format=self.format)

    def stop(self):
        if self.camera:
            try:
                try:
                    self.camera.stop_recording()
                except (KeyError, picamera.PiCameraNotRecording):
                    pass
                self.camera.close()
                try:
                    self.condition.notify_all()
                except RuntimeError:
                    pass
            finally:
                self.frame = None
                self.camera = None

    @property
    def rotation(self):
        return self.ROTATION_OPTIONS[self.rotation_pos]

    def rotate(self):
        self.rotation_pos += 1
        if self.rotation_pos >= len(self.ROTATION_OPTIONS):
            self.rotation_pos = 0
        if self.camera:
            self.camera.rotation = self.rotation

    def __del__(self):
        self.stop()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class StreamingHandler(server.BaseHTTPRequestHandler):
    STREAM_PATH = '/stream.mjpg'
    CONTROL_PATH = '/control'
    MIN_RESOLUTION_CHANGE = 10
    CHANGE_CAM_LOCK = Lock()

    def get_path(self):
        return os.path.abspath('/../{}'.format(self.path))

    # noinspection PyUnusedLocal
    def get_context(self, path):
        return {
            'video_feed': self.STREAM_PATH,
            'fps_5': 'selected' if CAM.framerate == 5 else '',
            'fps_10': 'selected' if CAM.framerate == 10 else '',
            'fps_15': 'selected' if CAM.framerate == 15 else '',
            'fps_20': 'selected' if CAM.framerate == 20 else '',
            'fps_25': 'selected' if CAM.framerate == 25 else '',
            'fps_30': 'selected' if CAM.framerate == 30 else '',
        }

    def stream(self):
        self.send_response(200)
        self.send_header('Age', '0')
        self.send_header('Cache-Control', 'no-cache, private')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.end_headers()
        try:
            while CAM.camera is not None:
                with CAM.condition:
                    got_it = CAM.condition.wait(timeout=1)
                    if not got_it:
                        continue
                    frame = CAM.frame
                self.wfile.write(b'--FRAME\r\n')
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')

            frame = CAM.blank_frame()
            self.wfile.write(b'--FRAME\r\n')
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(frame)))
            self.end_headers()
            self.wfile.write(frame)
            self.wfile.write(b'\r\n')
        except Exception as e:
            logging.warning(
                'Removed streaming client %s: %s',
                self.client_address, str(e))

    def photo(self):
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        photo = CAM.photo()
        self.send_header('Content-Length', str(len(photo)))
        self.end_headers()
        self.wfile.write(photo)
        self.wfile.write(b'\r\n')
        self.wfile.flush()

    def status(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        content = json.dumps({
            'cam': True if CAM.camera else False,
            'rotation': CAM.rotation,
            'resolution': CAM.resolution,
            'fps': CAM.framerate,
        }).encode()
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        self.wfile.flush()

    # noinspection PyPep8Naming
    def do_GET(self):
        url_result = urlparse(self.get_path())
        path = url_result.path
        template_filename = os.path.join(BASE_PATH, 'templates', path[1:])
        if path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif os.path.isfile(template_filename):
            mimetype = mimetypes.guess_type(template_filename)[0]
            self.send_response(200)
            self.send_header('Content-Type', mimetype or 'application/octet-stream')
            with open(template_filename, 'rb') as f:
                content = f.read()

            if mimetype == 'text/html':
                template = Template(content.decode())
                content = template.safe_substitute(**self.get_context(path))
                content = content.encode()

            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif path == self.STREAM_PATH:
            if 'mode=photo' in url_result.query:
                self.photo()
            else:
                self.stream()
        elif path == self.CONTROL_PATH:
            if self.CHANGE_CAM_LOCK.acquire(timeout=0.01):
                try:
                    query = parse_qs(url_result.query)
                    start = False
                    was_started = CAM.camera is not None
                    try:
                        fps = int(query.get('fps', [CAM.framerate])[0])
                        if CAM.framerate != fps:
                            CAM.stop()
                            CAM.framerate = fps
                            start = was_started
                    except (TypeError, ValueError):
                        pass

                    try:
                        resolution = int(query.get('resolution', [CAM.resolution])[0])
                        if abs(CAM.resolution - resolution) > self.MIN_RESOLUTION_CHANGE:
                            CAM.stop()
                            CAM.resolution = resolution
                            start = was_started
                    except (TypeError, ValueError):
                        pass

                    if 'mode' in query:
                        mode = query.get('mode')[0]
                        if mode == 'rotate':
                            CAM.rotate()
                        elif mode == 'photo':
                            if not was_started:
                                pass
                        elif mode == 'stop':
                            CAM.stop()
                        elif mode == 'start':
                            start = True
                    if start:
                        CAM.start()
                finally:
                    self.CHANGE_CAM_LOCK.release()

            self.status()
        else:
            self.send_error(404)
            self.end_headers()
        self.connection.close()


CAM = PiCam()


if __name__ == '__main__':
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()

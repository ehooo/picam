# PiCam

Web streaming based on
http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

The web interface allow:
* Change framerate.
* Change resolution size.
* Change rotation.
* Download photo.

# Install
```
sudo pip3 install -r requirements.txt
```

## Setup systemd
```
sudo cp /home/pi/code/picam/picam.service /lib/systemd/system/picam.service
sudo chmod 644 /lib/systemd/system/picam.service
sudo systemctl daemon-reload
sudo systemctl enable picam.service
```

Check it
```
sudo reboot
sudo systemctl status picam.service
```

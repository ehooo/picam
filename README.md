# PiCam

Web streaming based on
http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

You could configurate the system via config file (see [picam.conf](./picam.conf)).

The web interface allow:
* Change framerate.
* Change resolution size.
* Change rotation.
* Download photo.
* Allows turn on light.

# Setup
```
sudo pip3 install -r requirements.txt
```

## Setup remote GPIO
In order to allow turn on/off light using GPIO you need:
```
sudo apt install pigpio
sudo raspi-config
```
Select `3 Interface Options` > `P8 Remote GPIO` and enable it.


## Autostart with systemd
In order to autorun on system startup:
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

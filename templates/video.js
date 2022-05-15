const ACTION_START = 'start';
const ACTION_STOP = 'stop';
const ACTION_ROTATE = 'rotate';
const ACTION_LIGHT = 'light';
const MIN_RESOLUTION_CHANGE = 10;
const ROTATE_MAP = {
    0: '&#x1F446',
    90: '&#x1F448',
    180: '&#x1F447',
    270: '&#x1F449',
};
const LIGHT = {
  false: '&#x1F31C',
  true: '&#x1F31E',
};

var previous_resolution = 0;
var previous_fps = 0;

function update_setting_picam(callback=undefined, action=undefined){
  var refresh = false;
  let fps = document.querySelector('[name="fps"]').value;
  let data = {}
  if (previous_fps!==fps){
    data.fps = fps;
    previous_fps = fps;
    refresh = true;
  }
  let resolution = Math.min(window.innerHeight, window.innerWidth);
  if (Math.abs(resolution - previous_resolution) > MIN_RESOLUTION_CHANGE) {
    data.resolution = resolution;
    previous_resolution = resolution;
    let video_frame = document.querySelector('#video_frame');
    video_frame.style.width = resolution+'px';
    video_frame.style.height = resolution+'px';
    refresh = true;
  }

  if (action !== undefined){
    data.mode = action
  }

  if(Object.keys(data).length === 0){
    return;
  }

  let url = '/control?';
  url += new URLSearchParams(data).toString();
  const xhttp = new XMLHttpRequest();
  xhttp.open("GET", url, true);
  xhttp.onreadystatechange = function() {
    if(this.readyState === 4) {
      if (typeof callback === "function") {
        let response = JSON.parse(this.responseText);
        callback(response);
      }
      if(refresh) refresh_video();
    }
  };
  xhttp.send();
}

function recording_mode(recording=false) {
  const record_button = document.querySelector('#record');
  const stop_button = document.querySelector('#stop');
  if(recording) {
    record_button.style.display = "none";
    stop_button.style.display = null;
  } else {
    record_button.style.display = null;
    stop_button.style.display = "none";
  }
}

function refresh_video(){
  const video = document.querySelector("#video");
  let src = video.attributes.getNamedItem('data-src').value;
  video.src = src + "?" + new Date().getTime();
}

document.addEventListener("DOMContentLoaded", function(event) {
  const video = document.querySelector("#video");
  const light = document.querySelector("#light");
  const rotate_pointer = document.querySelector("#rotate_pointer");
  window.onresize = update_setting_picam;

  update_setting_picam((response) => {
    recording_mode(response.cam);
    if(response.cam){
      refresh_video();
    }
    rotate_pointer.innerHTML = ROTATE_MAP[response.rotation];
    light.innerHTML = LIGHT[response.light];
  });
  rotate_pointer.addEventListener("click", (event) => {
    update_setting_picam((response) => {
      rotate_pointer.innerHTML = ROTATE_MAP[response.rotation];
    }, ACTION_ROTATE);
  });
  light.addEventListener("click", (event) => {
    update_setting_picam((response) => {
      light.innerHTML = LIGHT[response.light];
    }, ACTION_LIGHT);
  });

  const fps_selector = document.querySelector('[name="fps"]');
  fps_selector.addEventListener("change", (event) => {
    update_setting_picam();
  });

  const stop_button = document.querySelector('#stop');
  stop_button.addEventListener("click", (event) => {
    update_setting_picam((response) => {
      recording_mode(response.cam);
    }, ACTION_STOP);
  });
  const record_button = document.querySelector('#record');
  record_button.addEventListener("click", (event) => {
    update_setting_picam((response) => {
      recording_mode(response.cam);
      refresh_video();
    }, ACTION_START);
  });
  const photo_button = document.querySelector('#photo');
  photo_button.addEventListener("click", (event) => {
      let src = video.attributes.getNamedItem('data-src').value;
      src += "?mode=photo" + new Date().getTime();
      fetch(src).then(
        image => image.blob()
      ).then(imageBlog => {
        const imageURL = URL.createObjectURL(imageBlog)
        const link = document.createElement('a')
        link.href = imageURL
        link.download = 'picam.jpeg'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      });
  });
});

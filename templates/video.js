const ACTION_START = 'start';
const ACTION_STOP = 'stop';
const ACTION_ROTATE = 'rotate';


function update_setting_picam(callback=undefined, action=undefined){
  let data = {
    'fps': document.querySelector('[name="fps"]').value,
    'resolution': document.querySelector('[name="resolution"]').value,
  }
  if (action !== undefined){
    data.mode = action
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


document.addEventListener("DOMContentLoaded", function(event) {
  const video = document.querySelector("#video");
  update_setting_picam((response) => {
    recording_mode(response.cam);
    if(response.cam){
      let src = video.attributes.getNamedItem('data-src').value;
      video.src = src + "?" + new Date().getTime();
    }
  });

  const fps_selector = document.querySelector('[name="fps"]');
  fps_selector.addEventListener("change", (event) => {
    update_setting_picam();
  });

  const resolution_selector = document.querySelector('[name="resolution"]');
  resolution_selector.addEventListener("change", (event) => {
    update_setting_picam((response) => {
      location.reload();
    });
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
      let src = video.attributes.getNamedItem('data-src').value;
      video.src = src + "?" + new Date().getTime();
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

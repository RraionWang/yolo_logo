from ultralytics import YOLO
import cv2
import imutils
import threading
from flask import Flask, send_file, jsonify
import os

# ====== GLOBAL VARIABLES ======
person_count = 0
last_range = -1  # Tracks the last video range index
count_lock = threading.Lock()  # Thread-safe access

# ====== FLASK APP SETUP ======
app = Flask(__name__)

@app.route('/play_video')
def play_video():
    global last_range
    with count_lock:
        pc = person_count

# 1 green 
# 2 blue 
# 3 yellow 
# 4 orange 
# 5 red

    # Determine the range index based on person count
    if pc == 0:
        range_index = 'green'  # 1.mp4
    elif pc==1:
         range_index = 'blue'  # 1.mp4
    elif 2 <= pc <= 3:
        range_index = 'green'  # 1.mp4
    elif 4 <= pc <= 5:
        range_index = 'yellow'  # 3.mp4
    elif 6 <= pc <= 7:
        range_index = 'orange'
    elif pc >7:
        range_index = 'red'  # 5.mp4
    else:
        range_index = 'green'  # 1.mp4
       
 
    
    


    video_path = f"{range_index}.mp4"

    if not os.path.exists(video_path):
        return f"Video file {video_path} not found", 404

    # Only update if the range changed
    if range_index != last_range:
        last_range = range_index

    return send_file(video_path, as_attachment=False, mimetype='video/mp4')


@app.route('/get_count')
def get_count():
    with count_lock:
        pc = person_count
    return jsonify({"count": pc})


@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Video Display</title>
    <style>
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }
        #video-container {
            position: relative;
            width: 100vw;
            height: 100vh;
        }
        video {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
    </style>
    <script>
        let currentRange = -1;

        function loadVideo() {
            fetch('/get_count')
                .then(res => res.json())
                .then(data => {
                    let count = data.count;
                    let range = 1;

                    if (count == 0) range = 1;
                    else if (count >= 1 && count <= 2) range = 2;
                    else if (count >= 3 && count <= 5) range = 3;
                    else if (count >= 6 && count <= 10) range = 4;
                    else range = 5;

                    if (range !== currentRange) {
                        currentRange = range;
                        console.log("Switched to video:", currentRange + ".mp4");

                        const source = document.querySelector('#myVideo source');
                        source.src = "/play_video?" + new Date().getTime(); // cache buster
                        const video = document.getElementById('myVideo');
                        video.load();
                        video.play().catch(e => console.log("Autoplay failed", e));
                    }
                });
        }

        window.onload = function () {
            loadVideo(); // Initial load
            setInterval(loadVideo, 1000); // Check every second
        };
    </script>
</head>
<body>
    <div id="video-container">
        <video id="myVideo" autoplay muted playsinline>
            <source id="videoSource" src="/play_video" type="video/mp4">
            您的浏览器不支持视频播放。
        </video>
    </div>
</body>
</html>
    """


# ====== YOLO DETECTION THREAD ======
def run_yolo():
    global person_count

    model = YOLO("yolov8s.pt")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Webcam could not be opened")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = imutils.resize(frame, width=640)
        results = model(frame)

        count = 0
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls.item())
                conf = box.conf.item()
                if cls == 0 and conf > 0.5:  # Class 0 = 'person'
                    count += 1

        with count_lock:
            person_count = count

        print(f"Detected Persons: {count}")

    cap.release()


# ====== MAIN ======
if __name__ == '__main__':
    print("Starting YOLO detection thread...")
    yolo_thread = threading.Thread(target=run_yolo, daemon=True)
    yolo_thread.start()

    print("Starting Flask web server...")
    app.run(host='0.0.0.0', port=8888)

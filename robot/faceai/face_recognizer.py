#coding=utf-8
import time
import cv2
import face_recognition
import os
import requests
import concurrent.futures

API_VALIDATE = 'c6b94c20c1609c6dc7394079f4f0635a'

class FaceRecognizer:
    def __init__(self, path):
        self.path = path  # 模型数据图片目录
        self.total_image_name = []
        self.total_face_encoding = []
        self.last_detection_time = {}
        self.last_detection_face = ""
        self.cap = None

        # 加载所有已知的面部编码
        for fn in os.listdir(self.path):
            if fn.startswith('.'):
                continue
            print(self.path + "/" + fn)
            image_path = os.path.join(self.path, fn)
            if os.path.isfile(image_path):
                image_name = fn[:-4]  # 去掉文件扩展名
                face_image = face_recognition.load_image_file(image_path)
                face_encoding = face_recognition.face_encodings(face_image)[0]
                self.total_face_encoding.append(face_encoding)
                self.total_image_name.append(image_name)

    def start(self):
        self.cap = cv2.VideoCapture(0)
        while True:
            ret, frame = self.cap.read()
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                matches = face_recognition.compare_faces(self.total_face_encoding, face_encoding, tolerance=0.5)
                name = "Unknown"

                if True in matches:
                    first_match_index = matches.index(True)
                    name = self.total_image_name[first_match_index]
                    self.dectect_callback(name)

                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            cv2.imshow('Video', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    def stop(self):
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()


    def call_api(self, face_name):
        url = f'http://localhost:5001/face_dectect?validate={API_VALIDATE}&face={face_name}'
        response = requests.get(url)
        return response.text
    
    def dectect_callback(self, face):
        current_time = time.time()
        # 连续两次检测到同一个名字才响应，过滤误识别问题
        if self.last_detection_face != face:
            print(f"dectect_callback detect {face} first time")
            self.last_detection_face = face
            return

        if face in self.last_detection_time and (current_time - self.last_detection_time[face]) < 120:
            print(f"Not calling the API for {face} as the time interval is less than 2 minutes.")
            return
        self.last_detection_time[face] = current_time

        print(f"Hello, {face}.")
        # 调用api接口http://localhost:5001/face_dectect?validate=validate_code&face=name
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.call_api, face)
            result = future.result()

# 使用示例
if __name__ == "__main__":
    path_to_images = os.path.join(os.path.expanduser('~'), '.wukong/face_img')
    face_recognizer = FaceRecognizer(path_to_images)
    try:
        face_recognizer.start()
    finally:
        face_recognizer.stop()

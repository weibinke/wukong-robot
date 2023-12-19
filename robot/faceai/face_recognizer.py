#coding=utf-8
import cv2
import face_recognition
import os

class FaceRecognizer:
    def __init__(self, path):
        self.path = path  # 模型数据图片目录
        self.total_image_name = []
        self.total_face_encoding = []
        self.known_faces = {}
        self.cap = None

        # 加载所有已知的面部编码
        for fn in os.listdir(self.path):
            if fn.startswith('.'):
                continue
            print(self.path + "/" + fn)
            image_path = os.path.join(self.path, fn)
            image_name = fn[:-4]  # 去掉文件扩展名
            face_image = face_recognition.load_image_file(image_path)
            face_encoding = face_recognition.face_encodings(face_image)[0]
            self.total_face_encoding.append(face_encoding)
            self.total_image_name.append(image_name)
            self.known_faces[image_name] = False  # 初始化为未打过招呼

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

                    if not self.known_faces[name]:
                        self.known_faces[name] = True
                        print(f"Hello, {name}.")

                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            cv2.imshow('Video', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    def stop(self):
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()

# 使用示例
if __name__ == "__main__":
    path_to_images = os.path.join(os.path.expanduser('~'), '.wukong/face_img')
    face_recognizer = FaceRecognizer(path_to_images)
    try:
        face_recognizer.start()
    finally:
        face_recognizer.stop()

# -*- coding: utf-8 -*-
import os
import platform

from robot import config, logging
from robot.Player import MusicPlayer
from robot.sdk.AbstractPlugin import AbstractPlugin

logger = logging.getLogger(__name__)


class Plugin(AbstractPlugin):

    IS_IMMERSIVE = True  # 这是个沉浸式技能

    def __init__(self, con):
        super(Plugin, self).__init__(con)
        self.player = None
        self.song_list = None

    # 获取子目录下所有.mp3文件路径，支持子目录递归，安全起见，只遍历一层子目录
    def get_song_list(self, path):
        if not os.path.exists(path) or not os.path.isdir(path):
            return []

        song_list = []
        for subdir in os.listdir(path):
            subdir_path = os.path.join(path, subdir)
            if os.path.isdir(subdir_path):
                for file in os.listdir(subdir_path):
                    if file.endswith(".mp3") or file.endswith(".wav"):
                        song_list.append(os.path.join(subdir_path, file))
            else:
                if file.endswith(".mp3") or file.endswith(".wav"):
                        song_list.append(os.path.join(subdir_path, file))

        return song_list

    def init_music_player(self):
        self.song_list = self.get_song_list(config.get("/LocalPlayer/path"))
        if self.song_list == None:
            logger.error(f"{self.SLUG} 插件配置有误", stack_info=True)
        logger.info(f"本地音乐列表：{self.song_list}，共{len(self.song_list)}首")
        return MusicPlayer(self.song_list, self)

    def handle(self, text, parsed):
        if not self.player:
            self.player = self.init_music_player()
        if len(self.song_list) == 0:
            self.clearImmersive()  # 去掉沉浸式
            self.say("本地音乐目录并没有音乐文件，播放失败")
            return
        if self.nlu.hasIntent(parsed, "MUSICRANK"):
            self.player.play()
        elif self.nlu.hasIntent(parsed, "CHANGE_TO_NEXT"):
            self.player.next()
        elif self.nlu.hasIntent(parsed, "CHANGE_TO_LAST"):
            self.player.prev()
        elif self.nlu.hasIntent(parsed, "CHANGE_VOL"):
            slots = self.nlu.getSlots(parsed, "CHANGE_VOL")
            for slot in slots:
                if slot["name"] == "user_d":
                    word = self.nlu.getSlotWords(parsed, "CHANGE_VOL", "user_d")[0]
                    if word == "--HIGHER--":
                        self.player.turnUp()
                    else:
                        self.player.turnDown()
                    return
                elif slot["name"] == "user_vd":
                    word = self.nlu.getSlotWords(parsed, "CHANGE_VOL", "user_vd")[0]
                    if word == "--LOUDER--":
                        self.player.turnUp()
                    else:
                        self.player.turnDown()

        elif self.nlu.hasIntent(parsed, "CONTINUE"):
            logger.info("继续播放")
            self.player.resume()
        elif self.nlu.hasIntent(parsed, "CLOSE_MUSIC") or self.nlu.hasIntent(
            parsed, "PAUSE"
        ):
            logger.info("停止播放")
            self.player.stop()
            self.clearImmersive()  # 去掉沉浸式
        else:
            self.say("没听懂你的意思呢，要停止播放，请说停止播放")
            self.player.resume()

    def pause(self):
        if self.player:
            system = platform.system()
            # BigSur 以上 Mac 系统的 pkill 无法正常暂停音频，
            # 因此改成直接停止播放，不再支持沉浸模式
            if system == "Darwin" and float(platform.mac_ver()[0][:5]) >= 10.16:
                logger.warning("注意：Mac BigSur 以上系统无法正常暂停音频，将停止播放，不支持恢复播放")
                self.player.stop()
                return
            self.player.pause()

    def restore(self):
        if self.player and self.player.is_pausing():
            self.player.resume()

    def isValidImmersive(self, text, parsed):
        return any(
            self.nlu.hasIntent(parsed, intent)
            for intent in [
                "CHANGE_TO_LAST",
                "CHANGE_TO_NEXT",
                "CHANGE_VOL",
                "CLOSE_MUSIC",
                "PAUSE",
                "CONTINUE",
            ]
        )

    def isValid(self, text, parsed):
        return "本地音乐" in text
        # return any(word in text for word in ["播放音乐", "放首歌", "放歌"]) 

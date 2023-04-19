
import json
import logging
import os
import requests

# 获取日志对象
logger = logging.getLogger(__name__)
# 日志输出到终端
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

# 定义类，基类是AbstractPlugin
class Music():
    # 基类成员
    SLUG = "music"

    # 插件初始化
    def __init__(self):
        # 初始化父类
        super().__init__()
        # 插件名称
        self.name = '音乐'
        # 插件描述
        self.description = '播放音乐'
        # 插件别名
        self.alias = ['音乐', '播放音乐', '播放歌曲', '歌曲']
        # 插件类型

    # 基类方法，插件入口
    def handle(self, text, parsed):
        # 说：开始播放音乐
        self.say('开始播放音乐')

    # 基类方法
    def isValid(self, text, parsed):
        # 关键词匹配
        return any(word in text for word in self.alias)
    
    def searchMusic(self, singer):
        # 根据歌手名字，通过网易云音乐api搜索歌曲
        url = 'http://music.163.com/api/search/get'
        data = {
            's': singer,  # 歌手名
            'type': 100,  # 搜索类型为歌手
            'limit': 1,  # 返回结果数量
            'offset': 0  # 偏移量
        }
        # 发送请求
        r = requests.post(url, data=data)
        # 获取歌手信息
        singer_info = r.json()['result']['artists'][0]
        # 获取歌手id
        singer_id = singer_info['id']
        # 获取歌手名字
        singer_name = singer_info['name']
        # 获取歌手照片
        singer_pic = singer_info['picUrl']
        # 根据歌手id，通过网易云音乐api获取热门歌曲
        url = 'http://music.163.com/api/artist/top/song'
        data = {
            'id': singer_id,  # 歌手id
            'limit': 10,  # 返回结果数量
            'offset': 0  # 偏移量
        }
        # 发送请求
        r = requests.post(url, data=data)
        # 打印请求回包
        logger.info(r.json())

        # 获取歌曲列表
        song_list = r.json()['songs']
        # 定义歌曲列表
        songs = []
        # 打印歌曲数量
        logger.info('歌曲数量：{}'.format(len(song_list)))
        # 遍历歌曲
        for song in song_list:
            # 获取歌曲id
            song_id = song['id']
            # 获取歌曲名
            song_name = song['name']

            # 根据song_id，获取网易云音乐播放url
            url = f'http://music.163.com/api/song/detail/?id={song_id}&ids=[{song_id}]'

            headers = {
                'Referer': 'http://music.163.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }

            response = requests.get(url, headers=headers)
            data = json.loads(response.text)
            song_url = data['songs'][0]['mp3Url']
            logger.info('歌曲url：{}'.format(song_url))
            

            # 定义歌曲信息
            song_info = {
                'song_id': song_id,
                'song_name': song_name,
                'song_url': song_url
            }
            # 添加到歌曲列表
            songs.append(song_info)
            # 打印歌曲信息
            logger.info('歌曲信息：{}'.format(song_info))

        # 开始播放第一首歌曲
        self.playMusic(songs[0]['song_url'])

    def playMusic(self, url):
            # 播放音乐
            self.say('开始播放音乐')
            # 播放音乐
            self.play(url)

    def say(self, text):
         # TODO 打印测试日志
        logger.info('say: {}'.format(text))

    def play(self, url):
        # TODO 打印测试日志
        logger.info('play: {}'.format(url))


if __name__ == '__main__':
    # 实例化类
    plugin = Music()
    plugin.searchMusic('周杰伦')
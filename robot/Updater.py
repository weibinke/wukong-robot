import os
import requests
import json
import semver
from subprocess import call
from robot import constants, logging
from datetime import datetime, timedelta
from robot import config

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

_updater = None
URL = "https://service-e32kknxi-1253537070.ap-hongkong.apigateway.myqcloud.com/release/wukong"
DEV_URL = "https://service-e32kknxi-1253537070.ap-hongkong.apigateway.myqcloud.com/release/wukong-dev"



class Updater(object):
    def __init__(self):
        self.last_check = datetime.now() - timedelta(days=1.5)
        self.update_info = {}

    def _pull(self, cwd, tag):
        if os.path.exists(cwd):
            return (
                call(
                    [f"git checkout master && git pull && git checkout {tag}"],
                    cwd=cwd,
                    shell=True,
                )
                == 0
            )
        else:
            logger.error(f"目录 {cwd} 不存在")
            return False

    def _pip(self, cwd):
        if os.path.exists(cwd):
            return (
                call(
                    ["pip3", "install", "-r", "requirements.txt"], cwd=cwd, shell=False
                )
                == 0
            )
        else:
            logger.error(f"目录 {cwd} 不存在")
            return False

    def update(self):
        update_info = self.fetch()
        success = True
        if update_info == {}:
            logger.info("恭喜你，wukong-robot 已经是最新！")
        if "main" in update_info:
            if self._pull(
                constants.APP_PATH, update_info["main"]["version"]
            ) and self._pip(constants.APP_PATH):
                logger.info("wukong-robot 更新成功！")
                self.update_info.pop("main")
            else:
                logger.info("wukong-robot 更新失败！")
                success = False
        if "contrib" in update_info:
            if self._pull(
                constants.CONTRIB_PATH, update_info["contrib"]["version"]
            ) and self._pip(constants.CONTRIB_PATH):
                logger.info("wukong-contrib 更新成功！")
                self.update_info.pop("contrib")
            else:
                logger.info("wukong-contrib 更新失败！")
                success = False
        return success

    def _get_version(self, path, current):
        if os.path.exists(os.path.join(path, "VERSION")):
            with open(os.path.join(path, "VERSION"), "r") as f:
                return f.read().strip()
        else:
            return current

    def fetch(self):
        if (not config.get("enable_update"),False):
            logger.info("fetch update ignored. enable_update to true if you want it.")
            return {}
        
        global URL, DEV_URL
        url = URL
        now = datetime.now()
        if (now - self.last_check).seconds <= 1800:
            logger.debug(f"30 分钟内已检查过更新，使用上次的检查结果：{self.update_info}")
            return self.update_info
        try:
            self.last_check = now
            r = requests.get(url, timeout=3)
            info = json.loads(r.text)
            main_version = info["main"]["version"]
            contrib_version = info["contrib"]["version"]
            # 检查主仓库
            current_main_version = self._get_version(constants.APP_PATH, main_version)
            current_contrib_version = self._get_version(
                constants.CONTRIB_PATH, contrib_version
            )
            if semver.compare(main_version, current_main_version) > 0:
                logger.info(f"主仓库检查到更新：{info['main']}")
                self.update_info["main"] = info["main"]
            if semver.compare(contrib_version, current_contrib_version) > 0:
                logger.info(f"插件库检查到更新：{info['contrib']}")
                self.update_info["contrib"] = info["contrib"]
            if "notices" in info:
                self.update_info["notices"] = info["notices"]
            return self.update_info
        except Exception as e:
            logger.error(f"检查更新失败：{e}", stack_info=True)
            return {}


def fetch():
    global _updater
    if not _updater:
        _updater = Updater()
    return _updater.fetch()


if __name__ == "__main__":
    fetch()

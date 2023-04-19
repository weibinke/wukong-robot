# -*- coding: utf-8 -*-
import requests
import tushare as ts
from bs4 import BeautifulSoup
from robot.sdk.AbstractPlugin import AbstractPlugin
from robot import config, logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Plugin(AbstractPlugin):

    SLUG = "stock"

    def get_stock_info(self):
        # 获取股票收盘信息，https://tushare.pro/document/1?doc_id=108
        summary = ""
        stock_info = ts.get_realtime_quotes(['sh', 'sz', 'cyb'])
        if stock_info.empty:
            logger.error("获取收盘信息错误,stock_info is None")
            return "获取收盘信息错误"
        logger.debug("stock_info: {}".format(stock_info))

        date = datetime.today().strftime('%Y-%m-%d')
        for index, row in stock_info.iterrows():
            closing_price = float(row["price"])
            prev_closing_price = float(row["pre_close"])
            daily_change = closing_price - prev_closing_price
            daily_percentage_change = daily_change / prev_closing_price * 100
            summary += f"{row['name']} ({row['code']}) 收盘信息\n ({date}): {closing_price}, \n日涨跌幅: \n{daily_percentage_change:.2f}%。\n\n"

        logger.info("summary: {}".format(summary))
        return summary

    def get_exchange_rate(self):
        # 获取美元汇率信息
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url)
        if response.status_code != 200:
            return None

        data = response.json()
        exchange_rate = data["rates"]["CNY"]
        prev_exchange_rate = exchange_rate - data["rates"]["USD"]
        daily_percentage_change = prev_exchange_rate / exchange_rate * 100
        date = datetime.today().strftime('%Y-%m-%d')

        result = f"美元兑人民币汇率\n({date}): {exchange_rate}, \n日涨跌幅: \n{daily_percentage_change:.2f}%。\n"
        logger.info(result)
        return result

    def createNews(self):
        result = "" 
        result += self.get_stock_info()
        result += self.get_exchange_rate()
        result += self.get_stock_viewpoint()
        return  result
    
    # TODO 获取新闻信息，目前还没有调通数据
    def get_stock_viewpoint(self):
         # 获取财经大V观点并汇总看多，看空观点情况
        url = 'https://finance.sina.com.cn/7x24/?tag=6'
        header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            # 定期更换Cookie
            'Cookie': 'U_TRS1=00000042.84a04125.5c0e948c.f32a6591; SINAGLOBAL=39.155.232.202_1544459404.539397; vjuids=28258871c.170f6053f67.0.1f2d7e0149f79; vjlast=1584675504; FSINAGLOBAL=39.155.232.202_1544459404.539397; SGUID=1584675509556_63347537; UOR=,,; __gads=ID=aa1defd5d93e1e79-2265b0f06ad30027:T=1653554992:RT=1653554992:S=ALNI_Ma-p5O8FFfc3NNsZydp_fjIBIIpeQ; __gpi=UID=000005c29acf63c3:T=1653554992:RT=1653554992:S=ALNI_MblWWsVCkPByGyiGuKR4mhRaLI_7g; SUB=_2AkMUDjCSf8NxqwJRmPkczWjhaYx1wg7EieKiUsFJJRMyHRl-yD9jqkcztRB6P44efaxt6G-eGD3S0CLHgf4T0LYeJwDq; Apache=122.14.229.248_1680795829.222234; __bid_n=187573d0bcfdd1af934207; Hm_lvt_fcf72dc8287d20a78b3dfd301a50cbf8=1680795831; Hm_lvt_b82ffdf7cbc70caaacee097b04128ac1=1680795831; ULV=1681585207216:8:1:1:122.14.229.248_1680795829.222234:1653554989594; name=sinaAds; post=massage; NowDate=Wed Apr 19 2023 16:26:34 GMT+0800; SFA_version=2021-08-02 09:00; sinaGlobalRotator_https://finance.sina.com=135; SR_SEL=1_511; directAd_wcp=true; FPTOKEN=qJpoXXeQx9LDw0sTistLj/8jUEFAD5cq9cfWEps/ECTGZ7SJruMBLS4EGD5K4Zp511Ad/N5LxLeY6oxKp8GSSBmgv0sDp/EKfjZS7QXnd/E2qoKyK30s3dD5ayDpI/XBCps8sJoyfOxasZMCTlODs0u2JlpIW9rnOwbO8RcLs+JmUvPYtXsoQqW4G9yd7hYdhn5AIM6pZEEfeWSh5ejUQK5wbz/G+fytwGwErCfg51Bwc5ZjQp3hu5HxAzflolwdWmFnbZ2NgOF56cBcn9dXT1sDkURKS2odnf68QmKD8Wnigf+5tvwOhqHPnlc3VH/BYCtm8MQuIuZNrbowFFaRIjujoqN5hRBsUv7s9fRrRqQrn1j6UPAJ0mhWBH+pZMuuFyhtRFiDPJL8FaAtkFbU2g==|5FU1ECoK0PW0NXQWwRmb3NWHvN1vSrc4ntwgOcQW/Fc=|10|68e50e777dd962e87e2fdf265c0abcf6; U_TRS2=000000c2.4a081c9d.643fd57b.975d5639; Hm_lpvt_b82ffdf7cbc70caaacee097b04128ac1=1681904961; Hm_lpvt_fcf72dc8287d20a78b3dfd301a50cbf8=1681904962; hqEtagMode=1'
        }

        # 发送 GET 请求获取HTML内容
        response = requests.get(url,headers=header)
        r = requests.get(url, headers=header)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        div = soup.find('div', class_='liveList01')
        if not div:
            logger.info(soup)
            logger.error("获取财经观点出错了。")
            return "\n\n获取财经观点出错了。\n"
        
        articles = []
        for tr in div.find_all('bd_i_txt_c'):
            summary = tr.text().strip()
            articles.append(summary)

        bullish = 0
        bearish = 0
        neutral = 0
        for article in articles:
            if '看多' in article or '买入' in article:
                bullish += 1
            elif '看空' in article or '卖出' in article:
                bearish += 1
            else:
                neutral += 1

        if bullish > bearish:
            sentiment = '多头市场'
        elif bearish > bullish:
            sentiment = '空头市场'
        else:
            sentiment = '震荡市场'

        # 播报大V观点
        result = result + "\n"
        result = result + "大V观点汇总：\n"
        result = result + "看多观点\n%d个，看空观点\n%d个，中性观点\n%d个。" % (bullish, bearish, neutral)
        result = result + "综合来看，大V观点情绪为\n%s。\n" % sentiment

        logger.info(result)
        return result

    def handle(self, text, parsed):
        self.say("正在为你播报股票行情：", cache=True)
        result = self.createNews()
        self.say(result)

    def isValid(self, text, parsed):
        return any(word in text for word in ["股票", "股市"]) 
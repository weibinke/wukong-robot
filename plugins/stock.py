# -*- coding: utf-8 -*-

import requests
import tushare as ts
from bs4 import BeautifulSoup
from robot.sdk.AbstractPlugin import AbstractPlugin
from robot import config, logging

logger = logging.getLogger(__name__)

class Plugin(AbstractPlugin):

    SLUG = "stock"

    # TODO，还在报错中，继续调，Exception: 抱歉，您没有访问该接口的权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。
    def createNews(self):
        token =  config.get('/' + self.SLUG + '/key')
        # logger.info("token: {}".format(token))

        # 获取股市收盘信息
        pro = ts.pro_api(token)
        df = pro.index_daily(ts_code='000300.SH,000001.SH', start_date='20230403', end_date='20230410')
        hs300 = df[df['ts_code'] == '000300.SH']
        sh = df[df['ts_code'] == '000001.SH']

        result = ""
        # 播报股市收盘信息
        result = result + "沪深300指数今日收盘价为%.2f点，涨幅为%.2f%%" % (hs300.iloc[0]['close'], hs300.iloc[0]['pct_chg'])
        result = result + "上证指数今日收盘价为%.2f点，涨幅为%.2f%%" % (sh.iloc[0]['close'], sh.iloc[0]['pct_chg'])

        # 获取大V观点并汇总
        r = requests.get('http://finance.sina.com.cn/7x24/')
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        div = soup.find('div', class_='bd_i_04')
        articles = []
        for tr in div.find_all('tr'):
            td = tr.find_all('td')
            if len(td) >= 3:
                title = td[1].text.strip()
                summary = td[2].text.strip()
                articles.append(title + ' ' + summary)

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
        result = result + "\n\n"
        result = result + "大V观点汇总："
        result = result + "看多观点%d个，看空观点%d个，中性观点%d个。" % (bullish, bearish, neutral)
        result = result + "综合来看，大V观点情绪为%s。" % sentiment

        return  result
    
    def handle(self, text, parsed):
        self.say("正在为你播报股票行情：", cache=True)
        news = self.createNews()
        self.say(news)

    def isValid(self, text, parsed):
        return any(word in text for word in ["股票", "股市"]) 
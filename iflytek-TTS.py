# -*- coding:utf-8 -*-

import websocket
import datetime
import hashlib
import base64
import hmac
import os
import json
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime


class IFLYTEKTTS:
    def __init__(self, appId: str, apiKey: str, apiSecret: str, text: str, format: str, filename: str):
        '''
        :params appId:申请到的接口appid
        :params apiKey:申请到的接口apikey
        :params appSecret:申请到的接口apisecret
        :params text:待转换的文字内容
        :params format:生成的文件格式 pcm|mp3|speex
        :params filename:生成文件保存名称（不带后缀）
        '''
        self.appId = appId
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        self.text = text
        self.format = format
        self.filename = filename

    def authentication(self):
        '''
        鉴权生成方法
        :return url:带鉴权的握手请求地址
        '''
        # host值可选项未明确说明，固定值？
        request_url = "wss://tts-api.xfyun.cn/v2/tts"
        host = "ws-api.xfyun.cn"
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        # host: $host\ndate: $date\n$request-line
        signature_text = f'host: {host}\ndate: {date}\nGET /v2/tts HTTP/1.1'
        # 使用hmac-sha256加密
        # signature_sha=hmac-sha256(signature_origin,$apiSecret)
        # FIXME hexdigest()？digest()?
        signature = hmac.new(self.apiSecret.encode(
            'utf-8'), signature_text.encode('utf-8'), digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(signature).decode(encoding='utf-8')
        # api_key="$api_key",algorithm="hmac-sha256",headers="host date request-line",signature="$signature"
        authentication = f'api_key="{self.apiKey}",algorithm="hmac-sha256",headers="host date request-line",signature="{signature}"'
        authentication_base64 = base64.b64encode(
            authentication.encode('utf-8'))
        authentication_data = {
            "host": host,
            "date": date,
            "authorization": authentication_base64,
        }
        url = f'{request_url}?{urlencode(authentication_data)}'
        return url

    def paramsMaker(self):
        '''
        根据需求生成对应业务参数
        '''
        format_map = {
            'pcm': {"aue": "raw"},
            # FIXME 文档标注为string,但是这里sfl需要传int
            'mp3': {"aue": "lame", "sfl": 1},
            'speex': {"aue": "speex;7"}
        }
        format_param = format_map[self.format]
        self.common_param = {"app_id": self.appId}
        # mp3需要添加一个参数sfl,固定值为啥不能省略？
        self.bussiness_param = {"vcn": "xiaoyan", "tte": "utf8"}
        self.bussiness_param.update(format_param)
        # status 数据状态，固定为2
        self.data = {"status": 2, "text": str(
            base64.b64encode(self.text.encode('utf-8')), 'utf-8')}

    def transMisson(self):
        '''
        任务启动入口
        '''
        self.paramsMaker()
        url = self.authentication()
        self.app = websocket.WebSocketApp(
            url, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.app.run_forever()

    # FIXME 回调函数必须传入固定数量位置参数？
    def on_message(self, ws, message):
        try:
            message = json.loads(message)
            # print(message)
            # 失败返回格式 {'code': , 'message': , 'sid':}
            # 成功返回格式 {'code': , 'message': , 'sid':,'data’:{'audio':,'status':,'ced':}}
            code = message["code"]
            sid = message["sid"]
            audio = message["data"]["audio"]
            audio = base64.b64decode(audio)
            status = message["data"]["status"]
            if status == 2:
                self.app.close()
                print("合成结束")
            # code:0 成功，其他异常
            if code == 0:
                with open(f'{self.filename}.{self.format}', 'ab') as f:
                    f.write(audio)
            else:
                error_msg = message["message"]
                print(f"错误代码:{code},错误信息：{error_msg}")
        except Exception as e:
            print("Exception:", e)

    # 收到websocket连接错误的处理
    def on_error(self, ws, error):
        print("【Error】:", error)

    # 收到websocket连接关闭的处理
    def on_close(self):
        print("【Message】connection closed")

    # 收到websocket连接建立的处理
    def on_open(self, ws):
        print('连接建立，开始传输数据')
        params = {"common": self.common_param,
                  "business": self.bussiness_param,
                  "data": self.data,
                  }
        params = json.dumps(params)
        print(params)
        self.app.send(params)
        if os.path.exists(f'{self.filename}.{self.format}'):
            os.remove(f'{self.filename}.{self.format}')


if __name__ == "__main__":
    appId = "xxx"    #xxx填写你自己的
    apiKey = "xxx"   #xxx填写你自己的
    apiSecret = "xxx"#xxx填写你自己的
    text = "这只猫很可爱啊！但是他叫什么名字呢？I have no idea"
    filename = "result"
    format = "mp3"
    tts = IFLYTEKTTS(appId, apiKey, apiSecret, text, format, filename)
    tts.transMisson()

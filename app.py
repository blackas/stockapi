# -*- coding: utf-8 -*-
from flask import Flask, request, render_template, make_response
from flask_cors import CORS
from flask_restful import reqparse, abort, Api, Resource, fields, marshal_with
from stocklab.db_handler.mongodb_handler import MongoDBHandler

from datetime import datetime, timedelta
import requests
import json

#주가 전략 테스트 관련 라이브러리
import matplotlib.pyplot as plt
from pandas import Series, DataFrame
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA

app = Flask(__name__)
CORS(app)
api = Api(app)

code_hname_to_eng = {
    "단축코드": "code",
    "확장코드": "extend_code",
    "종목명": "name",
    "시장구분": "market",
    "ETF구분": "is_etf",
    "주문수량단위": "memedan",
    "기업인수목적회사구분": "is_spac"
}

price_hname_to_eng_st = {
    "날짜": "Date",
    "종가": "Close",
    "시가": "Open",
    "고가": "High",
    "저가": "Low",
    "전일대비": "diff",
    "전일대비구분": "diff_type",
    "누적거래량":"Volume"
}

price_hname_to_eng = {
    "날짜": "date",
    "종가": "close",
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "전일대비": "diff",
    "전일대비구분": "diff_type",
    "누적거래량":"volume_usd"
}

code_fields = {
    "code": fields.String,
    "extend_code": fields.String,
    "name": fields.String,
    "memedan": fields.Integer,
    "market": fields.String,
    "is_etf": fields.String,
    "is_spac": fields.String,
    "uri": fields.Url("code")
}
 
code_list_short_fields = {
    "code": fields.String,
    "name": fields.String
} 
code_list_fields = {
    "count": fields.Integer,
    "code_list": fields.List(fields.Nested(code_fields)),
    "uri": fields.Url("codes")
}

price_fields = {
    "date": fields.Integer,
    "start": fields.Integer,
    "close": fields.Integer,
    "open": fields.Integer,
    "high": fields.Integer,
    "low": fields.Integer,
    "diff": fields.Float,
    "diff_type": fields.Integer,
    "volume_usd": fields.Integer
}

price_list_fields = {
    "count": fields.Integer,
    "price_list": fields.List(fields.Nested(price_fields)),
 }


mongodb = MongoDBHandler()

DBName = "stocklab"

API_CERT_KEY = "f65e3d55e94386158e835f5eb20114470063ad39"
kakao_rest_api_key = "028ea5b683384907ee2126203f9e033d"

class Code(Resource):
    @marshal_with(code_fields)
    def get(self, code):
        result = mongodb.find_item({"단축코드":code}, DBName, "code_info")
        if result is None:
            return {}, 404
        code_info = {}
        code_info = { code_hname_to_eng[field]: result[field] 
                        for field in result.keys() if field in code_hname_to_eng }
        return code_info

class CodeList(Resource):
    @marshal_with(code_list_fields)
    def get(self):
        market = request.args.get('market', default="0", type=str)
        if market == "0":
            results = list(mongodb.find_items({}, DBName, "code_info"))
        elif market == "1" or market == "2":
            results = list(mongodb.find_items({"시장구분":market}, DBName, "code_info"))
        result_list = []
        for item in results:
            code_info = {}
            code_info = { code_hname_to_eng[field]: item[field] for field in item.keys() if field in code_hname_to_eng }
            result_list.append(code_info)
        return {"code_list" : result_list, "count": len(result_list)}, 200

class Price(Resource):
    @marshal_with(price_list_fields)
    def get(self, code, sortflag):
        if sortflag == "des":
            sortnum = -1
        else:
            sortnum = 1

        today = datetime.now().strftime("%Y%m%d")
        default_start_date = datetime.now() - timedelta(days=30)
        start_date = request.args.get('start_date', default=default_start_date.strftime("%Y%m%d"), type=str)
        end_date = request.args.get('end_date', default=today, type=str)
        results = list(mongodb.find_items({"code":code}, DBName, "price_info").sort("날짜",sortnum))
        result_object = {}
        price_info_list = []

        for item in results:
            price_info = { price_hname_to_eng[field]: item[field] for field in item.keys() if field in price_hname_to_eng } 
            price_info_list.append(price_info)
        result_object["price_list"] = price_info_list
        result_object["count"] = len(price_info_list)
        return result_object, 200

class OrderList(Resource):
    def get(self):
        status = request.args.get('status', default="all", type=str)
        if status == 'all':
            result_list = list(mongodb.find_items({}, DBName, "order"))
        elif status in ["buy_ordered", "buy_completed", "sell_ordered", "sell_completed"]:
            result_list = list(mongodb.find_items({"status":status}, DBName, "order"))
        else:
            return {}, 404
        return { "count": len(result_list), "order_list": result_list }, 200

class RT_DartList(Resource):
    def get(self):
        page_count = request.args.get('page_count', default="100", type=str)
        page_no = request.args.get('page_no', default="1", type=str)
        
        day = datetime.now().strftime("%Y%m%d")

        darturl = 'https://opendart.fss.or.kr/api/list.json?crtfc_key='+API_CERT_KEY+ '&page_count='+page_count+'&page_no='+page_no +'&bgn_de=' + day
        res = requests.get(darturl)
        jObject = json.loads(res.text)
        status = jObject['status']
        if status == "000":
            Result    = jObject['list']
            totalpage = jObject['total_page']
            totalcnt  = jObject['total_count']
            return { "totalcnt": totalcnt, "totalpage": totalpage, "list": Result }, 200
        else:
            return { "errcode": 100, "errmsg": "금일 조회 된 공시결과가 없습니다." }, 200


class DartList(Resource):
    def get(self):
        corpcls = request.args.get('corpcls', default="all", type=str)
        code = request.args.get('code', default="all", type=str)
        if corpcls == 'all' and code == 'all':
            result_list = list(mongodb.find_items({}, DBName, "dart_publication"))
        elif corpcls in ["Y", "K", "N", "E"]:
            if code == 'all':
                result_list = list(mongodb.find_items({"corp_cls":corpcls}, DBName, "dart_publication"))
            else:
                result_list = list(mongodb.find_items({"stock_code":code}, DBName, "dart_publication"))
        else:
            return {"error:잘못 된 요청입니다."}, 404
        return { "count": len(result_list), "dart_list": result_list }, 200

class StrategyList(Resource):

    def get(self):
        filepath = datetime.now().strftime("%Y%m%d%H%M%S") + ".html"
        code = request.args.get('code', default="all", type=str)
        #n1 = request.args.get('n1', default=5, type=int)
        #n2 = request.args.get('n2', default=20, type=int)
        TCash = request.args.get('cash', default=100000000, type=int)
        TCommission = request.args.get('commission', default=0.0002, type=float)
        pricelist = mongodb.find_items_column({"code":code},{"_id":False,"날짜":1,"시가":1,"고가":1,"저가":1,"종가":1,"누적거래량":1},DBName, "price_info").sort("날짜",1)
        price_info_list = []

        for item in pricelist:
            print(item)
            price_info = { price_hname_to_eng_st[field]: item[field] for field in item.keys() if field in price_hname_to_eng_st }
            price_info_list.append(price_info)

        print("컬럼명 변경 완료")

        df = DataFrame(price_info_list)
        df_int = df.apply(pd.to_numeric)
        df_int['Date'] = pd.to_datetime(df["Date"])
        df_int = df_int.set_index('Date')

        bt = Backtest(df_int, SmaCross,
              cash=TCash, commission=TCommission,
              exclusive_orders=True)
        bt.run()
        bt.plot(filename=filepath,open_browser=False)
        bt.plot(open_browser=False)
        f = open(filepath, 'r')
        line = f.read()
        return { "html": line }, 200

class Check(Resource):
    def get(self):
        lst_code = list(mongodb.find_items({}, DBName, "code_info"))
        time = datetime.now()
        #end = time.strftime("%Y%m%d")
        #start = (time - timedelta(days=40)).strftime('%Y%m%d')
        end = '20200801'
        start = '20191201'
        if len(lst_code) < 21:
            return False
        for code in lst_code:
            results = list(mongodb.find_items({"$and":[{'code':"005930", '날짜' : {'$gt' : start, '$lt' : end}}]}, DBName, "price_info").sort("날짜",1))
            price_info_list = []

            if len(results) == 0:
                return {"status":"조회된 데이터가 없습니다."}, 500

            for item in results:
                price_info = { price_hname_to_eng[field]: item[field] for field in item.keys() if field in price_hname_to_eng } 
                price_info_list.append(price_info)

            df_price = DataFrame(price_info_list)
            ma5  = df_price['close'].rolling(window=5).mean()
            ma20 = df_price['close'].rolling(window=20).mean()
            volumn = df_price['close'].rolling(window=20).mean()
            df_price.insert(len(df_price.columns), "MA5", ma5)
            df_price.insert(len(df_price.columns), "MA20", ma20)
            print(df_price)
            break
        return {"status":"OK"}, 200

class GetKakaoAccessToken(Resource):
    def get(self):
        kakaocode = request.args.get('kakaocode', default="", type=str)

        if kakaocode=="":
            return {"status":"Fail"}, 500

        redirect_uri = "https://blackas.github.io/testreactweb"

        host = "https://kauth.kakao.com/oauth/token?grant_type=authorization_code&client_id=" + kakao_rest_api_key + "&redirect_uri=" + redirect_uri + "&code=" + kakaocode
        print(host)

        headers = {'Content-type': 'application/x-www-form-urlencoded;charset=utf-8'}
        res = requests.post(host, headers=headers)
        jObject = json.loads(res.text)
        
        if "error" in jObject:
            return {"error":jObject["error"],"error_code":jObject["error_code"],"error_description":jObject["error_description"]}, 200

        userinfo={}
        userinfo["kakao_access_token"] = jObject["access_token"]
        userinfo["kakao_expires_in"] = jObject["expires_in"]
        userinfo["kakao_refresh_token"] = jObject["refresh_token"]
        userinfo["kakao_refresh_token_expires_in"] = jObject["refresh_token_expires_in"]

        host = "https://kapi.kakao.com/v2/user/me"
        headers = {'Content-type': 'application/x-www-form-urlencoded;charset=utf-8','Authorization': 'Bearer {'+userinfo["kakao_access_token"] + '}'}
        res = requests.post(host, headers=headers)
        jObject = json.loads(res.text)

        if "error" in jObject:
            return {"error":jObject["error"],"error_code":jObject["error_code"],"error_description":jObject["error_description"]}, 200

        userinfo["userid"] = jObject["id"]
        userinfo["usernick"] = jObject["properties"]["nickname"]

        if mongodb.find_items({"userid":userinfo["userid"]}, DBName, "userinfo").count() == 0:
            mongodb.insert_item(userinfo, DBName, "userinfo")
        else:
            mongodb.update_item({"userid":userinfo["userid"]},{"$set" : userinfo}, DBName, "userinfo")
        return {"status":"OK"}, 200

class SmaCross(Strategy):
    n1 = 5
    n2 = 20
    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.sell()

api.add_resource(CodeList, "/codes", endpoint="codes")
api.add_resource(Code, "/codes/<string:code>", endpoint="code")
api.add_resource(Price, "/codes/<string:code>/sortflag/<string:sortflag>/price", endpoint="price")
api.add_resource(OrderList, "/orders", endpoint="orders")
api.add_resource(RT_DartList, "/rt_dartlist", endpoint="rt_dartlist")
api.add_resource(DartList, "/dart", endpoint="dart")
api.add_resource(StrategyList, "/strategy", endpoint="strategy")
api.add_resource(Check, "/check", endpoint="check")
api.add_resource(GetKakaoAccessToken, "/GetKakaoAccessToken", endpoint="GetKakaoAccessToken")

if __name__ == '__main__':
    app.run(debug=True)
import httpx
from nonebot.adapters.onebot.v11.message import Message
from nonebot.log import logger


class CallApi:
    async def get_token(self, mr_url, username, password):
        mr_url = mr_url + "/api/auth/get_token"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        data = {
            "username": username,
            "password": password
        }
        async with httpx.AsyncClient(headers=headers) as client:
            try:
                res = await client.post(mr_url, json=data, timeout=10.0)
                res_json = res.json()
                if res_json["code"] != 0:
                    reason = res_json["message"]
                    logger.error(f"api：/api/auth/get_token返回信息不正常：{reason}")
                    return False
                if res_json['data']['user']['role_name'] == "管理员":
                    admin = 1
                else:
                    admin = 0
                info = res_json['data']['user']['role_name'] + res_json["data"]["user"]["nickname"]
                token = res_json['data']["access_token"]
                msg = Message(f"欢迎登录！{info}")
                return msg, token, admin
            except Exception as e:
                logger.error("访问api：/api/auth/get_token失败，原因：" + str(e))
                return False

    async def count_unread_sys_notify(self, mr_url, token):
        mr_url = mr_url + "/api/user/count_unread_sys_notify"
        headers = {"Authorization": "Bearer " + token, }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(mr_url, headers=headers, timeout=10.0)
                res_json = res.json()
                if res_json["code"] != 0:
                    reason = res_json["message"]
                    logger.error(f"api：/api/user/count_unread_sys_notify返回信息不正常：{reason}")
                    return False
                if res_json["data"] == 0:
                    return False
                unread_notify_num = res_json["data"]
                msg = Message(f"未读消息：{unread_notify_num}条 开始获取消息详情")
                logger.success(msg)
                return True
            except Exception as e:
                logger.error("访问api：/api/user/count_unread_sys_notify失败，原因：" + str(e))
                return False

    async def search_douban(self, mr_url, token, keyword):
        async with httpx.AsyncClient() as client:
            mr_url = mr_url + "/api/movie/search_douban"
            headers = {"Authorization": "Bearer " + token, }
            params = {'keyword': keyword}
            try:
                res = await client.get(mr_url, params=params, headers=headers, timeout=30.0)
                res_json = res.json()
                if res_json["code"] != 0:
                    reason = res_json["message"]
                    logger.error(f"api：/api/movie/search_douban返回信息不正常：{reason}")
                    return False
                return res_json
            except Exception as e:
                logger.error("访问api：/api/movie/search_douban失败，原因：" + str(e))
                return False

    async def get_unread_sys_notify(self, mr_url, token):
        async with httpx.AsyncClient() as client:
            mr_url = mr_url + "/api/user/get_unread_sys_notify"
            headers = {"Authorization": "Bearer " + token, }
            try:
                res = await client.get(mr_url, headers=headers, timeout=10.0)
                res_json = res.json()
                if res_json["code"] != 0:
                    reason = res_json["message"]
                    logger.error(f"api：/api/user/get_unread_sys_notify返回信息不正常：{reason}")
                    return False
                return res_json
            except Exception as e:
                logger.error("访问api：/api/user/get_unread_sys_notify失败，原因：" + str(e))
                return False

    async def submit(self, mr_url, token, douban_id):
        async with httpx.AsyncClient() as client:
            mr_url = mr_url + "/api/subscribe/sub_douban"
            headers = {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json; charset=utf-8",
            }
            # TODO season_ids是个什么id？？？
            data = {
                "id": douban_id,
                "season_ids": []
            }
            try:
                res = await client.post(mr_url, headers=headers, json=data, timeout=10.0)
                res_json = res.json()
                reason = res_json["message"]
                if res_json["code"] != 0:
                    logger.error(f"api：/api/subscribe/sub_douban返回信息不正常：{reason}")
                    return False
                return reason
            except Exception as e:
                logger.error("访问api：/api/subscribe/sub_douban失败，原因：" + str(e))
                return False

    async def site_data_overview(self, mr_url, token):
        async with httpx.AsyncClient() as client:
            mr_url = mr_url + "/api/site/overview"
            headers = {"Authorization": "Bearer " + token, }
            try:
                res = await client.get(mr_url, headers=headers, timeout=10.0)
                res_json = res.json()
                if res_json["code"] != 0:
                    reason = res_json["message"]
                    logger.error(f"api：/api/site/overview返回信息不正常：{reason}")
                    return res_json
                return res_json
            except Exception as e:
                logger.error("访问api：/api/site/overview失败，原因：" + str(e))
                return False

    async def register_mr(self, mr_url, token, username, password=""):
        async with httpx.AsyncClient() as client:
            mr_url = mr_url + "/api/user/register"
            headers = {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json; charset=utf-8",
            }
            data = {
                "username": username,
                "password": password,
                "nickname": "",
                "role": 2,
                "douban_user": "",
                "qywx_user": "",
                "pushdeer_key": "",
                "bark_url": "",
                "score_rule_name": "",
                "permission_category": [],
                "telegram_user_id": ""
            }
            try:
                res = await client.post(mr_url, headers=headers, json=data, timeout=10.0)
                res_json = res.json()
                reason = res_json["message"]
                if res_json["code"] != 0:
                    logger.error(f"api：/api/user/register返回信息不正常：{reason}")
                    return False
                return reason
            except Exception as e:
                logger.error("访问api：/api/user/register失败，原因：" + str(e))
                return False

    async def register_emby(self, emby_url, api_key, username):
        async with httpx.AsyncClient() as client:
            emby_url = emby_url + "/emby/Users/New"
            headers = {"Content-Type": "application/json; charset=utf-8"}
            data = {"Name": username}
            params = {"api_key": api_key}
            try:
                res = await client.post(emby_url, headers=headers, json=data, params=params, timeout=10.0)
                status_code = res.status_code
                logger.info(f"emby返回的状态码为：{status_code}")
                return status_code
            except Exception as e:
                logger.error("访问api：/emby/Users/New失败，原因：" + str(e))
                return False

    async def search_by_keyword(self, mr_url, token, keyword):
        async with httpx.AsyncClient() as client:
            mr_url = mr_url + "/api/media/search_by_keyword"
            headers = {"Authorization": "Bearer " + token}
            params = {"keyword": keyword}
            try:
                res = await client.get(mr_url, params=params, headers=headers, timeout=10.0)
                res_json = res.json()
                reason = res_json["message"]
                if res_json["code"] != 0:
                    logger.error(f"api：/api/media/search_by_keyword返回信息不正常：{reason}")
                    return False
                return res_json
            except Exception as e:
                logger.error("访问api：/api/media/search_by_keyword失败，原因：" + str(e))
                return False

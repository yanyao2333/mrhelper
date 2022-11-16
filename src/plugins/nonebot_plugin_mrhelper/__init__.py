import datetime
import json
import os
import re

from nonebot import on_command, get_driver, require, get_bots, on_request
from nonebot.adapters.onebot.v11 import Event, Bot, FriendRequestEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.log import logger
from nonebot.params import Arg, CommandArg
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from . import callapi
from . import sqlite
from .model import Config, MediaInfo

logger.info("开始初始化mr-helper")


class ConfigError(Exception):
    ...


require("nonebot_plugin_apscheduler")

plugin_config = Config.parse_obj(get_driver().config.dict())
AUTOADDFRIEND = plugin_config.mrhelper_autoaddfriend
SUPERUSERS = plugin_config.superusers
if len(SUPERUSERS[0]) == 0:
    raise ConfigError("你SUPERUSERS总要填一下吧？？？")
ADMIN = SUPERUSERS[0]
logger.info(f"主人qq：{ADMIN}")
COMMAND_START = plugin_config.command_start[0]
MR_URL = plugin_config.mrhelper_mrurl
DBPATH = os.path.split(os.path.realpath(__file__))[0] + "/mrhelper.db"
if MR_URL is None:
    raise ConfigError("你没有设置movie-robot的地址！！！")
elif MR_URL[0:4] != "http" or MR_URL[-1] == "/":
    raise ConfigError("movie-robot的地址格式不正确！正确示例：http://192.168.5.1:1234")
ENABLE_REGISTEREMBY = plugin_config.mrhelper_enable_registeremby
if ENABLE_REGISTEREMBY:
    if plugin_config.mrhelper_embyurl and plugin_config.mrhelper_embyapikey:
        EMBY_URL = plugin_config.mrhelper_embyurl
        EMBY_APIKEY = plugin_config.mrhelper_embyapikey
    else:
        raise ConfigError("你开启了注册emby功能 但是没有配置apikey和url!!!")
ENABLE_PUSHNOTIFY = plugin_config.mrhelper_enable_pushnotify
add_friends = on_request(priority=2)
login = on_command("登录", priority=15)
search_keyword = on_command("搜索", priority=15)
sub_douban = on_command("订阅", priority=15)
get_site_overview = on_command("今日数据", priority=20, permission=SUPERUSER)
register = on_command("注册", priority=15)
get_help = on_command("帮助", priority=15)
search_in_library = on_command("搜库", priority=15)
search_res = ""
db = sqlite.DB(DBPATH)
mr_api = callapi.CallApi()


@scheduler.scheduled_job("cron", minute="*/1", id="count_notify")
async def count_notify():
    (bot,) = get_bots().values()
    if db.Select("admin", 1) is not None:
        info = db.Select("admin", 1)
        token = info[4]
        msg = await mr_api.count_unread_sys_notify(MR_URL, token)
        if not msg:
            return None
        else:
            await get_unread_notify(token)
    else:
        logger.warning("没有登录mr管理员账号 无法获取未读消息！")


if not ENABLE_PUSHNOTIFY:
    # logger.info("关闭 查询未读消息条数 功能")
    scheduler.remove_job("count_notify")
else:
    logger.success("成功注册定时任务 查询未读消息条数 运行间隔：1min")


@scheduler.scheduled_job("cron", hour="*/5", id="fresh_token")
async def fresh_token():
    logger.info("开始运行刷新token任务")
    num = db.Count()
    fresh_num = 0
    if num is None:
        logger.info("一个账号都没有，我刷新什么？！")
        return None
    for key in range(0, num):
        info = db.Select("id", key + 1)
        update_time = info[6]
        update_time = datetime.datetime.strptime(update_time, '%Y-%m-%d %H:%M:%S.%f')
        username = info[2]
        password = info[3]
        qid = info[1]
        today = datetime.datetime.today()
        diff = today - update_time
        if diff.days >= 28:
            try:
                _, token, _ = await mr_api.get_token(MR_URL, username, password)
            except Exception as e:
                logger.warning(f"获取{username}的token时遇到错误，请查看日志定位问题！")
                continue
            logger.success(f"已刷新{username}的token")
            db.UpdateToken(key + 1, token)
            fresh_num += 1
    logger.success(f"已刷新{fresh_num}个token！")


logger.success("成功注册定时任务 刷新过期token 运行间隔：5h")

logger.debug(scheduler.get_jobs())

logger.success("初始化完成")


@login.handle()
async def _(event: Event):
    logger.info("开始处理登录事件！")
    qid = int(event.get_user_id())
    if db.Select("qid", qid) is not None:
        # 如果qq号在数据库中匹配到 则结束登录事件
        logger.info(f"数据库中有{qid}的信息！")
        await login.finish(f"\n{qid}已登录过", at_sender=True)
    else:
        msg = str(event.get_message())
        msg = msg.split(' ', 2)
        if len(msg) == 3:
            (username, password) = (msg[1], msg[2])
            try:
                msg, token, admin = await mr_api.get_token(MR_URL, username, password)
            except Exception:
                await login.finish("错误！请查看日志定位问题！")
            logger.success(f"获取token成功！")
            # qid:QQ号 admin:是否为管理员（接收通知用）0非1是
            db.Insert(qid, username, password, token, admin)
            logger.success(f"数据库信息插入成功！{msg}")
            await login.finish(f"\n{msg}", at_sender=True)
        else:
            # 检测到无法识别的格式，返回提示，结束
            logger.warning("格式不正确 无法登陆")
            await login.finish(Message(f"\n请使用如下格式：\n{COMMAND_START}登录[空格]账号[空格]密码"), at_sender=True)


@search_keyword.handle()
async def _(state: T_State, keyword: Message = CommandArg()):
    logger.info("开始处理mr搜片事件！")
    if keyword:
        state['keyword'] = keyword


@search_keyword.got("keyword", prompt="请输入片名：")
async def _(event: Event, msg: Message = Arg("keyword")):
    global search_res
    logger.info(f"豆瓣搜索关键词：{msg}")
    session_id = event.get_session_id()
    qid = int(event.get_user_id())
    try:
        fwd_msg, res_num = await build_search_result_msg(qid, msg)
    except Exception:
        await search_keyword.finish("错误！请查看日志定位问题！")
    await search_keyword.send(f"\n{res_num}", at_sender=True)
    await send_forward_msg(session_id, fwd_msg)
    await search_keyword.finish()


async def build_search_result_msg(qid, keyword):
    logger.info("开始在豆瓣搜索关键词并构建合并转发消息节点！")
    global search_res
    info = db.Select("qid", qid)
    token = info[4]
    search_res = await mr_api.search_douban(MR_URL, token, keyword)
    if not search_res:
        return False
    if len(search_res['data']) < 9:
        lens = len(search_res['data'])
    else:
        lens = 9
    fwd_msg = []
    res_num = MessageSegment.text(f"🔎搜索到的前{lens}个影视信息：")
    for key in range(lens):
        msg = ""
        msg += MessageSegment.text(str(key + 1) + ". 🍿" + search_res['data'][key]['cn_name'] + "\n")
        msg += MessageSegment.text("豆瓣链接：" + search_res['data'][key]['url'] + "\n")
        msg += MessageSegment.image(search_res['data'][key]['poster_path'], proxy=False, cache=False)
        fwd_msg.append({"type": "node", "data": {"name": "mrhelper", "uin": f"{qid}", "content": Message(msg)}})
    logger.success("合并转发消息节点构建完成！")
    return fwd_msg, res_num


async def get_unread_notify(token):
    (bot,) = get_bots().values()
    logger.info("开始处理查看消息详情事件！")
    qid = ADMIN
    res_json = await mr_api.get_unread_sys_notify(MR_URL, token)
    if not res_json:
        await bot.send_private_msg(user_id=ADMIN, message="错误！请查看日志定位问题！")
        return False
    num = len(res_json["data"])
    if num == 0:
        return False
    fwd_msg = []
    for key in range(num):
        msg = ""
        msg += MessageSegment.text(str(key + 1) + ". " + "标题：" + res_json["data"][key]["title"] + "\n\n")
        msg += MessageSegment.text("正文：" + res_json["data"][key]["message"] + "\n\n")
        msg += MessageSegment.text("时间：" + res_json["data"][key]["gmt_create"])
        fwd_msg.append({"type": "node", "data": {"name": "mrhelper", "uin": f"{qid}", "content": Message(msg)}})
    await send_forward_msg(ADMIN, fwd_msg)


# 提供构造好node节点的fwd_msg和session_id
async def send_forward_msg(session_id, fwd_msg):
    type = ""
    if session_id[0:5] == "group":
        type, gid, qid = session_id.split('_', 2)
    else:
        qid = session_id
    qid = int(qid)
    (boter,) = get_bots().values()
    if type:
        logger.info("尝试发送群聊消息")
        qid = str(qid)
        try:
            await boter.send_group_forward_msg(group_id=gid, messages=fwd_msg)
        except Exception as e:
            logger.warning(f"发送群聊合并转发消息错误！可能是被风控或无法访问tmdb！具体报错请去go-cqhttp网页查看")
            img_path = os.path.split(os.path.realpath(__file__))[0] + '/xibao.jpg'
            image = f"[CQ:image,file=file:///{img_path}]"
            await boter.send_group_msg(group_id=gid, message=image)
    else:
        logger.info("尝试发送私聊消息")
        qid = int(qid)
        try:
            await boter.send_private_forward_msg(user_id=qid, messages=fwd_msg)
        except Exception as e:
            await boter.send_private_forward_msg(user_id=qid, messages="消息进入了虚空，请查看日志了解原因")
            logger.warning(f"发送私聊合并转发消息错误！大概率是因为无法访问tmdb导致的 具体报错请去go-cqhttp网页查看")


@sub_douban.handle()
async def _(event: Event):
    logger.info("开始处理订阅影片事件！")
    global search_res
    qid = int(event.get_user_id())
    info = db.Select("qid", qid)
    token = info[4]
    try:
        num = str(event.get_message())
        num = int(re.sub(r"\D", "", num))
        num = num - 1
    except Exception as e:
        logger.warning(f"获取订阅序号错误！原因：{e}")
        await sub_douban.finish("\n请检查序号是否输入正确！", at_sender=True)
    if num >= 100:
        logger.info(f"用户输入数字可能为豆瓣id而并非序号 直接订阅")
        res = await mr_api.submit(MR_URL, token, num + 1)
        if not res:
            await sub_douban.finish("\n错误！请查看日志定位问题！", at_sender=True)
        await sub_douban.finish(f"\n豆瓣id：{num}影片已提交订阅\napi返回消息：{res}", at_sender=True)
    if len(search_res) == 0:
        await sub_douban.finish("\n请先使用 #搜片[空格]片名 进行搜索再选取！", at_sender=True)
    douban_id = search_res["data"][num]["id"]
    douban_name = search_res["data"][num]["cn_name"]
    douban_rating = search_res["data"][num]["rating"]
    douban_image = search_res["data"][num]["poster_path"]
    if search_res["data"][num]["sub_id"] is not None:
        logger.debug(search_res["data"][num]["sub_id"])
        logger.info(f"{douban_id}已经在库中 结束事件")
        search_res = ""
        await sub_douban.finish(f"\n{douban_name} ({douban_id})已经在库中！", at_sender=True)
    res = await mr_api.submit(MR_URL, token, douban_id)
    if not res:
        await sub_douban.finish("错误！请查看日志定位问题！")
    # 订阅完成后将搜索结果变量设为空
    search_res = ""
    msg = Message(
        f"\napi返回消息：{res}\n豆瓣id：{douban_id}\n名字：{douban_name}\n豆瓣评分：{douban_rating}\n") + MessageSegment.image(
        douban_image)
    await sub_douban.finish(msg, at_sender=True)


@get_site_overview.handle()
async def _(event: Event):
    logger.info("开始查询今日数据！")
    qid = int(event.get_user_id())
    if db.Select("admin", 1) is not None:
        info = db.Select("admin", 1)
        token = info[4]
    else:
        await register.finish("\n没有登录管理员账号 无法查询今日数据！", at_sender=True)
    data = await mr_api.site_data_overview(MR_URL, token)
    if not data:
        await get_site_overview.finish("\n错误！请查看日志定位问题！", at_sender=True)
    today_up = Message("今日上传：" + str(round(data["data"]["today_up"] / 1024)) + "GB\n")
    today_dl = Message("今日下载：" + str(round(data["data"]["today_dl"] / 1024)) + "GB\n")
    yestday_up = Message("昨日上传：" + str(round(data["data"]["yestday_up"] / 1024)) + "GB\n")
    yestday_dl = Message("昨日下载：" + str(round(data["data"]["yestday_dl"] / 1024)) + "GB\n")
    today_up_rate = Message("上传与昨日相比：" + data["data"]["today_up_rate"] + "\n")
    today_dl_rate = Message("下载与昨日相比：" + data["data"]["today_dl_rate"])
    await get_site_overview.finish("\n" + today_up + today_dl + yestday_up + yestday_dl + today_up_rate + today_dl_rate,
                                   at_sender=True)


@get_help.handle()
async def _():
    await get_help.finish(MessageSegment.text(
        f"\n1. {COMMAND_START}登录[空格]账号[空格]密码\n用途：登录movie robot\n2. {COMMAND_START}搜索[空格]片名\n用途：等同于在网页手动搜索\n3. {COMMAND_START}订阅[空格]数字\n用途：使用mr搜片后用该命令选择相应序号 也可以直接输入豆瓣id订阅\n4. {COMMAND_START}今日数据\n用途：查看当日上传下载等数据\n5. {COMMAND_START}注册[空格]账号[空格]密码\n用途：注册mr账号（可在配置文件中开启“同时注册emby账号”）\n6. {COMMAND_START}搜库[空格]影片名/imdb_id\n用途：查询影片是否入库等相关信息 建议使用imdb_id查询\n‼注意：如果你发指令机器人不回复你 大概率是你忘记先登录了"),
        at_sender=True)


@register.handle()
async def _(event: Event):
    logger.info("开始处理注册mr/emby事件！")
    if db.Select("admin", 1) is not None:
        info = db.Select("admin", 1)
        token = info[4]
    else:
        await register.finish("\n没有登录管理员账号 无法注册新账号！", at_sender=True)
    msg = str(event.get_message())
    msg = msg.split(' ', 2)
    if len(msg) != 3:
        logger.warning("格式不正确 无法注册新用户！")
        await login.finish(Message(f"\n请使用如下格式：\n{COMMAND_START}mr注册[空格]账号[空格]密码"), at_sender=True)
    (username, password) = (msg[1], msg[2])
    res = await mr_api.register_mr(MR_URL, token, username, password)
    if not res:
        await register.send(f"\nmr注册：{username}已经被注册了\n（如确定没有，请自行查看日志定位问题！）", at_sender=True)
    else:
        await register.send(f"\nmr注册：api返回消息：\n{res}", at_sender=True)
    if ENABLE_REGISTEREMBY:
        msg = await register_emby(username)
        await register.finish(f"\n{msg}", at_sender=True)
    else:
        await register.finish()


async def register_emby(username):
    status_code = await mr_api.register_emby(EMBY_URL, EMBY_APIKEY, username)
    if status_code == 200:
        logger.success(f"新建emby用户{username}成功！")
        msg = f"emby注册：新建emby用户{username}成功！"
        return msg
    elif status_code == 401:
        logger.warning(f"api密钥错误！请检查配置文件中的apikey是否正确！")
        msg = "emby注册：api密钥错误！请检查配置文件中的apikey是否正确！"
        return msg
    elif status_code == 400:
        logger.warning(f"用户名已存在！")
        msg = "emby注册：用户名已存在！"
        return msg
    else:
        logger.warning(
            "其他错误 请自行对照状态码在 http://swagger.emby.media/?staticview=true#/UserService/postUsersNew 查看原因！")
        msg = "emby注册：其他错误 请查看日志"
        return msg


@search_in_library.handle()
async def _(event: Event):
    logger.info("开始处理在媒体库中搜索影片事件！")
    session_id = event.get_session_id()
    keyword = str(event.get_message())
    keyword = keyword[3:]
    if keyword[0] == " ":
        keyword = keyword[1:]
    logger.debug(keyword)
    qid = int(event.get_user_id())
    info = db.Select("qid", qid)
    token = info[4]
    res = await mr_api.search_by_keyword(MR_URL, token, keyword)
    if not res:
        await search_in_library.finish("\n错误！请查看日志定位问题！", at_sender=True)
    if len(res["data"]) == 0:
        await search_in_library.finish(
            "\n🔴 该影片不在媒体库中！\nTips：一些影片拥有多个名称 可能导致搜索结果不准确 可以尝试使用imdb id搜索",
            at_sender=True)
    elif len(res["data"]) == 1:
        msg = await build_one_media_info(res["data"][0])
        if not msg:
            await search_in_library.finish("错误！请查看日志定位问题！")
        await search_in_library.finish(Message(msg))
    else:
        fwd_msg = []
        for key in range(len(res["data"])):
            msg = await build_one_media_info(res["data"][key])
            if not msg:
                await search_in_library.finish("\n错误！请查看日志定位问题！", at_sender=True)
            fwd_msg.append({"type": "node", "data": {"name": "mrhelper", "uin": f"{qid}", "content": Message(msg)}})
        await send_forward_msg(session_id, fwd_msg)


async def build_one_media_info(raw_json):
    if raw_json["type"] == "Movie":
        logger.info("开始清洗返回的movie数据")
        for key in range(len(raw_json["subtitle_streams"])):
            name = raw_json["subtitle_streams"][key]["display_title"]
            language = raw_json["subtitle_streams"][key]["language"]
            if language == "chi" or "chs" or "cht":
                logger.success("找到中文字幕！")
                raw_json.update({'have_chi_subtitle': True})
                break
            elif "Chinese" in name:
                logger.success("找到中文字幕！")
                raw_json.update({'have_chi_subtitle': True})
                break
            raw_json.update({'have_chi_subtitle': False})
    else:
        logger.info("开始清洗返回的series数据")
        if raw_json["next_episode_to_air"] is None:
            del raw_json["next_episode_to_air"]
        else:
            raw_json.update({"next_episode_to_air_date": raw_json["next_episode_to_air"]["air_date"]})
            raw_json.update({"next_episode_to_air_index": raw_json["next_episode_to_air"]["episode_index"]})
        str = ""
        for key1 in range(len(raw_json["sub_items"])):
            season = key1 + 1
            now_episode = 0
            all_episode = len(raw_json["sub_items"][key1]["sub_items"])
            for key2 in range(len(raw_json["sub_items"][key1]["sub_items"])):
                if raw_json["sub_items"][key1]["sub_items"][key2]["status"] == 1:
                    now_episode += 1
            str += f"第{season}季 有{now_episode}集 / 缺{all_episode - now_episode}集 / 共{all_episode}集\n"
        raw_json.update({"air_process": str})
    try:
        media_info = MediaInfo.parse_obj(raw_json)
    except Exception as e:
        logger.info(f"感觉哪里不对：{e}")
        return False
    msg = await build_media_info_msg(media_info)
    return msg


async def build_media_info_msg(media_info):
    name = MessageSegment.text("影片名：" + media_info.name + "\n")
    status = MessageSegment.text("🟢存在于媒体库中！\n")
    overview = MessageSegment.text("影片简介：" + media_info.overview + "\n")
    if media_info.type == "Movie":
        type = MessageSegment.text("影片类型：电影📽️\n")
        if media_info.have_chi_subtitle:
            subtitle = MessageSegment.text("🟢该电影有中文字幕 放心食用！\n")
        else:
            subtitle = MessageSegment.text("")
        air_process = MessageSegment.text("")
    else:
        type = Message("影片类型：电视剧📺\n")
        air_process = MessageSegment.text(media_info.air_process)
        subtitle = MessageSegment.text("")
    try:
        next_episode_to_air = MessageSegment.text(
            "➡第" + media_info.next_episode_to_air_index + "集播出时间：" + media_info.next_episode_to_air_date + "\n")
    except AttributeError and TypeError:
        logger.warning("未获取到该影片下集播出时间 跳过！")
        next_episode_to_air = MessageSegment.text("")
    imdb_id = MessageSegment.text("imdb_id：" + media_info.imdb_id + "\n")
    genres = MessageSegment.text("分类：" + media_info.genres + "\n")
    release_date = MessageSegment.text("上映时间：" + media_info.release_date + "\n")
    poster_img = MessageSegment.image(media_info.poster_url, timeout=10.0)
    msg = "[影片信息]\n" + name + type + imdb_id + genres + release_date + overview + "\n[影片状态]\n" + status + subtitle + air_process + next_episode_to_air + poster_img
    return msg


@add_friends.handle()
async def _(event: FriendRequestEvent, bot: Bot):
    add_req = json.loads(event.json())
    logger.debug(add_req)
    add_qq = add_req["user_id"]
    comment = add_req["comment"]
    flag = add_req["flag"]
    if AUTOADDFRIEND:
        await bot.set_friend_add_request(flag=flag, approve=True, remark="")
        await bot.send_private_msg(user_id=ADMIN, message=f"✅机器人成功添加QQ:{add_qq}为好友！")
        await add_friends.finish()
    else:
        await bot.send_private_msg(user_id=ADMIN, message=f"❗有人请求添加我为好友：qq号：{add_qq} 请求内容：{comment}")
        await add_friends.finish()


## 介绍

-----

基于nonebot2+nonebot_plugin_go-cqhttp+onebot v11实现  \
一个为movie-robot开发的qq机器人插件  \
没有通知功能   \
可以在群聊里使用 支持多用户 群友们能自己注册mr、emby账号 订阅、查询影片入库情况 ~~我给室友们用 纯纯不想搞内网穿透罢了~~  \
简单写一下 **技术很菜** bug估计多的一批

## 安装方式

-----

1. 运行镜像

```docker
sudo docker run -d \
--name=mrhelper \
-p 8787:8787 \
-v 配置文件目录:/app \
yanyaobbb/mrhelper
```

2. 进入你映射的配置文件目录修改`.env`文件，修改部分变量（见下方环境配置）

3. 重启容器，进入`http://ip地址:8787/go-cqhttp`登录qq即可

4. 检查日志，是否有`Succeeded to import "nonebot_plugin_mrhelper"`类似字样，如果有的话即成功，去给机器人发送`#帮助`试试吧

## 环境配置

-----

### movie-robot地址 必填 （理论来说只需要配置这个就能成功跑起来了）

`MRHELPER_MRURL="http://127.0.0.1:1329" #需包含协议头 端口 结尾不要有"/"`

### 是否启用emby注册功能（在注册mr账号时会同时自动注册一个同名emby账号） 选填

`MRHELPER_ENABLE_REGISTEREMBY=false #默认为关闭`

### emby地址 上边开启这个功能需要填

`MRHELPER_EMBYURL="http://127.0.0.1:8096" #需包含协议头 端口 结尾不要有"/"`

### emby apikey 上边开启这个功能需要填

`MRHELPER_EMBYAPIKEY="" #在emby后台获取的api密钥`

### 是否开启自动通过好友请求 选填

`MRHELPER_AUTOADDFRIEND=true #默认开启(关闭后也会在收到好友请求时向SUPERUSERS里的第一个qq号发通知 只是不会自动通过)`

## 命令一览

-----

‼注意：如果你发指令机器人不回复你 大概率是你忘记先登录了

1. #登录[空格]账号[空格]密码 用途：登录movie-robot
2. #搜索[空格]片名 用途：等同于在网页手动搜索
3. #订阅[空格]数字 用途：`#搜索`后用该命令选择相应序号（也可以直接输入豆瓣id订阅）
4. #今日数据 用途：查看当日上传下载等数据（只能SUPERUSERS里的qq号用）
5. #注册[空格]账号[空格]密码 用途：注册mr账号（可在配置文件中开启“同时注册emby账号”）
6. #搜库[空格]影片名/imdb_id 用途：查询影片是否入库等相关信息 建议使用imdb_id查询 ‼该功能需要访问tmdb下载图片 请确定可以访问tmdb

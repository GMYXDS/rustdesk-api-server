# rustdesk-api-server
rustdesk api 服务器后端 python实现 支持mysql数据库

可以 实现登录后返回所有 该账号的主机

## rustdesk部署

参考官方文档 和 网上资料 此项目不做过多赘述

官网：https://rustdesk.com/

## 代码目录说明

```python
config.py #配置文件
mysql_async.py #mysql数据库连接库
mytools.py #工具库
requirements.txt #python 库环境
server_v1.py #1.1.9 版本接口
server_v2.py #1.2.0.版本接口
```

## 使用方式

### 安装环境

```python
#推荐安装python3.8.0及以上版本
pip install -r requirements.txt
```

### 配置参数 `config.py`

```python
# 数据模式 mysql|sqlite
db_model = "mysql"

# mysql
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "password"

# sqlite
# 期待pr

# 允许跨域的域名 如果需要可以设置
CORS_ORIGINS = "http://127.0.0.1:8080,http://127.0.0.1"

# 新建用户和重置密码时候的授权码
AUTH_KEY = "123456"

# 运行配置
IP = "0.0.0.0"
PORT = 21114
DEBUG = False
```

### 1.9.0及以前版本

```python
#程序默认使用21114端口 可自行修改
python server_v1.py
```

### 1.2.0版本

```python
python server_v2.py
```

## rustdesk 配置

如果更改了`api服务器端口`则需要自行配置

否则中间的`中继服务器` 和`api 服务器`可以留空，程序会自行填充

![api](https://mss.gmyxds.fun/img/rustdesk_api_1.png)

安卓端不需要填写 `http://` 前缀 且必须为 `21114` 端口

## 后台部署

这里采用systemd部署

```shell
#创建
systemd /etc/systemd/system/rustdesk_api.service
vim /etc/systemd/system/rustdesk_api.service
```

填写 `rustdesk_api.service`

```shell
[Unit]
Description=rustdesk_api_server

[Service]
User=root
# 代码目录
WorkingDirectory=/root/apiserver_py
#运行脚本
ExecStart=python serve_v1.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```shell
#刷新设置
sudo systemctl daemon-reload
#启动服务
sudo systemctl start rustdesk_api
#停止服务
sudo systemctl stop rustdesk_api
#允许开机启动
sudo systemctl enable rustdesk_api
```

## 说明

### 项目使用的技术

- python Sanic 框架 （ps：类flask）
- 官网：https://sanic.dev/

### 登录注册api

- 由于官方没有公布管理后台的使用方法，暂时使用下面2个接口创建用户个更改密码
- 新建：http://127.0.0.1:21114/api/reg?username=test&password=test&auth_key=123456
- 更改密码：http://127.0.0.1:21114/api/set-pwd?username=test&password=test&new_pass=123456&auth_key=123456
- 详细请看源码

### 关于不能保存密码

- 关于官方api没有保存密码的功能，估计是因为安全
- 这个api接口是http传输，所有的请求都能被别人轻松获取到，所以如果带密码，容易泄露

- 目前使用只能自己设置个固定密码，然后根据服务器的备注去记忆

- 或者自己写个api管理密码，或者写个脚本，自动把本地的密码上传到云端，然后其他的机器再同步

### 关于新版1.2.0

- 新版ui上用flutter重写，好看了一点，但是目前没有正式发布，非常不稳定，目前不建议用
- 1.2.0只有切换成大视图才显示服务器备注
- 1.2.0在接口上还增加了许多新特性
  - 支持邮箱登录和三方登录
  - 支持用户分组，和用户分组管理员，分组管理员有权限查看当前分组所有的用户和对应的服务器
  - 支持一些pushr日志接口，目前api/audit在flutter种并没有启用，而是用的是api/heartbeat
  - 新版好像准备支持插件，但貌似功能还没写完

### 关于接口不稳定

- 由于目前这个接口不稳定，和1.2.0尚未发布，所以1.2.0只做了一个简单实现
- 后续等他稳定了会继续更新

### 关于sqlite等其他数据库的支持

-  作者时间有限，欢迎有大佬pr
- 或者使用这个项目：https://github.com/xiaoyi510/rustdesk-api-server

### 致谢

- 感谢rustdesk的开发者和维护者，给我们带来如此好的项目
- 此项目只是一个简单的api实现，如有商业需求欢迎咨询官方人员

## 赞助

<img src="https://mss.gmyxds.fun/img/donate.png" alt="donate" style="zoom: 50%;" />

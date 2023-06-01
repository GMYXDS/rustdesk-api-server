import asyncio
from sanic import Sanic, json
from sanic.response import text
from mysql_async import PoolMysqlAsync
from mytools import *
import json as json_tools
from sanic_ext import Extend
from config import CORS_ORIGINS,AUTH_KEY,IP,PORT,DEBUG

app = Sanic("rustdesk_api_sever_v2")
app.ctx.poolmysqlasync = PoolMysqlAsync() # async pool mysql
app.config.CORS_ORIGINS = CORS_ORIGINS
app.config.CORS_ALLOW_HEADERS = "*"
app.config.CORS_METHODS = "*"
app.config.OAS = False
Extend(app)

@app.route("/",methods=["GET"])
async def index(request):
    return text("欢迎使用rustdesk_api_sever_v2,作者github: https://github.com/test")

# 登录 ok
@app.route("/api/login",methods=["POST"])
async def api_login(request):
    # 请求
    # 请求 type "account","mobile","sms_code","email_code"
    # {'username': 'test', 'password': 'test', 'id': '1231231231', 'uuid': 'uuid', 'autoLogin': True, 'type': 'account', 'verificationCode': '', 'deviceInfo': {'os': 'windows', 'type': 'client', 'name': 'windows'}}

    # 返回
    # 返回type "access_token","email_check"
    # { "type": "access_token","access_token":"eyJhbGciOiJIUzI1","user":{"name":"test","email":"test@163.com","note":"测试","status":1,"grp":"default","is_admin":True}}
    # 400 500 code
    
    username = request.json.get("username","")
    password = request.json.get("password","")
    client_id = request.json.get("id","")
    uuid = request.json.get("uuid","")
    
    token = get_randomkeys(16)
    
    md5_pass = get_md5(password+"rustdesk")
    
    app = Sanic.get_app()
    sql = "SELECT * FROM `rustdesk_v2`.`rustdesk_users` where username = %s and password=%s"
    res = await app.ctx.poolmysqlasync.fetchone(sql,username,md5_pass)
    if not res:
        return json({"error":"username or password error"})
    
    # 删除旧token 防止重复登录导致的登录失败
    sql = "DELETE FROM `rustdesk_v2`.`rustdesk_token` WHERE `username` = %s and `client_id`=%s and `uuid`= %s "
    await app.ctx.poolmysqlasync.execute(sql,username,client_id,uuid)
    
    # 写入token
    sql = "INSERT INTO `rustdesk_v2`.`rustdesk_token` (`username`, `uid`, `client_id`, `uuid`, `access_token`) VALUES (%s,%s,%s,%s,%s)"
    await app.ctx.poolmysqlasync.execute(sql,username,res['id'],client_id,uuid,token)
    
    return json({"type": "access_token","access_token":token,"user":{"name":username,"email":res['email'],"note":res['note'],"status":res['status'],"grp":res['group'],"is_admin":True if res['is_admin']==1 else False }})

# 第三方登录 太复杂 没必要 不实现了
@app.route("/api/oidc/auth",methods=["POST","GET"])
async def api_oidc_auth(request):
    # 请求
    # op GitHub | Google | Okta
    # {'uuid': 'uuid', 'id': '1231231231', 'op': 'GitHub'}
    # 返回
    # {
    #   "state_msg": "Ready",
    #   "failed_msg": "Failed to authenticate user",
    #   "code_url":{
    #         "code":1,
    #         "url":"https://example.com"
    #     } ,
    #   "auth_body": {
    #     "access_token": "abcde12345",
    #     "token_type": "Bearer",
    #     "user": { "id": "12345", "name": "John Doe", "email": "john.doe@example.com", "note": null, "status": 1, "grp": null, "is_admin": true }
    #   }
    # }
    # error
    return json({"error":"未实现"})

# 第三方登录？
@app.route("/api/oidc/auth-query",methods=["POST","GET"])
async def api_oidc_auth_query(request):
    # 请求
    # code ,id ,uuid
    # 返回
    # {}
    return json({"error":"未实现"})

# 退出登录
@app.route("/api/logout",methods=["POST"])
async def api_logout(request):
    # 请求 POST
    # {'id': '1231231231', 'uuid': 'uuid'}
    # 返回 空

    client_id = request.json.get("id","")
    uuid = request.json.get("uuid","")
    
    app = Sanic.get_app()
    sql = "DELETE FROM `rustdesk_v2`.`rustdesk_token` WHERE `client_id` = %s and uuid = %s"
    res = await app.ctx.poolmysqlasync.execute(sql,client_id,uuid)
    if res:
        return json({"code":100, "data": "退出成功" })
    else:
        return json({"code":100, "data": "退出失败" })

# 获取当前用户信息 ok
@app.route("/api/currentUser",methods=["POST"])
async def api_currentUser(request):
    # 请求 post
    # Authorization: Bearer eyJhbGciO
    # post：{"id":"123412341","uuid":"uuid"}
    
    # 返回error |  还能返回400 401 会重置登录信息
    # {"error":"Wrong credentials","msg":"提供的登录信息错误"}
    # {"name":"test","email":"test@163.com","note":"测试","status":1,"grp":"default","is_admin":True}
    
    client_id = request.json.get("id","")
    uuid = request.json.get("uuid","")
    auth_token = request.token
    
    app = Sanic.get_app()
    sql = "SELECT * FROM `rustdesk_v2`.`rustdesk_token` where client_id = %s and uuid=%s and access_token=%s"
    res = await app.ctx.poolmysqlasync.fetchone(sql,client_id,uuid,auth_token)
    if not res:
        return json({"error":"Wrong credentials","msg":"提供的登录信息错误"})
    
    return json({"name":res['username'],"email":res['email'],"note":res['note'],"status":res['status'],"grp":res['group'],"is_admin":True if res['is_admin']==1 else False })
    
    
# 更新地址簿
@app.route("/api/ab",methods=["POST"])
async def api_ab(request):
    # authorization: Bearer eyJhb
    # post： 
    # {'data': '{"tags":[],"peers":[
        # {"id":"123412341","username":"Administrator","hostname":"hostname","platform":"Windows","alias":"test","tags":[""],"forceAlwaysRelay":"false","rdpPort":"","rdpUsername":""},
    # ]}'}
    # 新增id 一样的
    # 改名 一样的
    # 修改标签 一样的

    # 请求 post 
    # { data: JSON.stringify(ab) }
    # 返回 空 没处理
    
    auth_token = request.token
    
    data = request.json.get("data","")
    if not data:
        return json({"code":99,"data":"数据错误！"})
    data2 = json_tools.loads(data)
    
    app = Sanic.get_app()
    sql = "SELECT username,uid FROM `rustdesk_v2`.`rustdesk_token` where access_token=%s"
    res = await app.ctx.poolmysqlasync.fetchone(sql,auth_token)
    if not res:
        return json({"code":99,"data":"登录超时！","error":"登录超时！"})
    
    uid = res['uid']
    tags = data2['tags']
    peers = data2['peers']
    
    # 循环添加tags
    sql = "DELETE FROM `rustdesk_v2`.`rustdesk_tags` WHERE `uid` = %s"
    res = await app.ctx.poolmysqlasync.execute(sql,uid)
    
    for tag in tags:
        sql = "INSERT INTO `rustdesk_v2`.`rustdesk_tags` (`uid`, `tag`) VALUES (%s, %s)"
        res = await app.ctx.poolmysqlasync.execute(sql,uid,tag)
    
    # 循环 peers
    sql = "DELETE FROM `rustdesk_v2`.`rustdesk_peers` WHERE `uid` = %s"
    res = await app.ctx.poolmysqlasync.execute(sql,uid)
    
    for peer in peers:        
        temp_peer = peer
        sql = "INSERT INTO `rustdesk_v2`.`rustdesk_peers` (`uid`, `client_id`, `username`, `hostname`, `alias`, `platform`, `tags`,`forceAlwaysRelay`,`rdpPort`,`rdpUsername`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        res = await app.ctx.poolmysqlasync.execute(sql,uid,temp_peer['id'],temp_peer['username'],temp_peer['hostname'],temp_peer['alias'],temp_peer['platform'],json_tools.dumps(temp_peer['tags']),temp_peer['forceAlwaysRelay'],temp_peer['rdpPort'],temp_peer['rdpUsername'])
    
    return json({"code":100,"data": "成功"})

# 获取地址簿
@app.route("/api/ab/get",methods=["POST"])
async def api_ab_get(request):
    # 请求
    # None
    # 返回
    # return json({})
    # {"error":"Wrong credentials","msg":"提供的登录信息错误"}

    # {"data":json_tools.dumps({"tags":[],"peers":[]})}
    # {
    #     peers: [{id: "abcd", username: "", hostname: "", platform: "", alias: "", tags: ["","", ...],"forceAlwaysRelay":"true","rdpPort":"","rdpUsername":""}],
    #     tags: [],
    # }
    
    auth_token = request.token
    
    app = Sanic.get_app()
    sql = "SELECT username,uid FROM `rustdesk_v2`.`rustdesk_token` where access_token=%s"
    res = await app.ctx.poolmysqlasync.fetchone(sql,auth_token)
    if not res:
        return json({"error":"Wrong credentials","msg":"提供的登录信息错误"})
    
    # 获取全部tags 全部peers
    app = Sanic.get_app()
    sql = "SELECT tag FROM `rustdesk_v2`.`rustdesk_tags` where uid = %s"
    tags = []
    rows = await app.ctx.poolmysqlasync.fetchall(sql,res['uid'])
    for row in rows:
        tags.append(row['tag'])
        
    sql = "SELECT * FROM `rustdesk_v2`.`rustdesk_peers` where uid = %s"
    peers = []
    rows = await app.ctx.poolmysqlasync.fetchall(sql,res['uid'])
    for row in rows:
        peers.append({
            "id": row['client_id'],
            "username": row['username'],
            "hostname": row['hostname'],
            "alias":row['alias'],
            "platform": row['platform'],
            "tags": json_tools.loads(row['tags']),
            "forceAlwaysRelay":row['forceAlwaysRelay'],
            "rdpPort":row['rdpPort'],
            "rdpUsername":row['rdpUsername'],
        })
    
    return json({ "data": json_tools.dumps({"tags":tags,"peers":peers}) })

# 分组？未实现？接口本身功能不全
@app.route("/api/users",methods=["GET"])
async def api_users(request):
    # 请求
    # GET http://127.0.0.1:21114/api/users?current=1&pageSize=20
    # GET http://127.0.0.1:21114/api/users?current=1&pageSize=20&grp=default
    # 返回
    # {}
    # {"error":"error"}
    # {"total":10,"data":[{"name":"test","email":"test@163.com","note":"测试","status":1,"grp":"default","is_admin":True}]}
    return json({})

# 分组？未实现？接口本身功能不全
@app.route("/api/peers",methods=["GET"])
async def api_peers(request):
    # 请求 GET http://127.0.0.1:21114/api/peers?current=1&pageSize=20&grp=default&target_user=test
    # 返回
    # {}
    # {"error":"error"}
    # {"total"：10,"data":[{"id":,"info":,"status":,"user":,"user_name":,"note":,}]}
    return json({})

# 日志接口，历史操作，一些动作会发到这个接口,flutter没有用到好像
@app.route("/api/audit/<str:type>",methods=["POST","GET"])
async def api_audit(request,type):
    return json({"code":100,"error":False,"data":"正常"})

# 文件操作记录
@app.route("/api/record",methods=["POST","GET"])
async def api_record(request):
    # 请求
    # query ("type", "new"), ("file", &filename)
    # query ("type", "part"), ("file", &filename) ("offset", "0"), ("length",
    # query ("type", "tail"), ("file", &filename) ("offset", "0"), ("length",
    # query ("type", "remove"), ("file", &filename)
    # 返回
    # {"error":""}
    # {}
    return json({"code":100,"error":False,"data":"正常"})

# 心跳测试 是否在线 会一直发 30s
@app.route("/api/heartbeat",methods=["POST","GET"])
async def api_heartbeat(request):
    # {'id': '1231231231', 'modified_at': 0, 'ver': 1002000}
    # {'id': '1231231231', 'modified_at': 0, 'ver': 1002000,"conns":{}}
    
    # 返回
    # {"disconnect":[]}
    # {"modified_at":int}
    # {"strategy":{"config_options":[
    #     "relay-server":"",
    #     "api-server":"",
    #     "custom-rendezvous-server":"",
    #     "key":"",
    # ]}}
    return json({"modified_at":int(time.time())})


# 插件？ 程序本身功能未实现
@app.route("/lic/web/api/plugin-sign",methods=["POST"])
async def api_plugin_sign(request):
    # 请求
    # plugin_id  version msg
    # 返回
    # {}
    return json({"code":100,"error":False,"data":"正常"})

# 插件？ 程序本身功能未实现
@app.route("/meta.toml",methods=["POST","GET"])
async def api_plugin_meta(request):
    # 请求
    # 返回
    return json({"code":100,"error":False,"data":"正常"})


# 创建账号 请求 http://127.0.0.1:21114/api/reg?username=test&password=test&auth_key=123456
@app.route("/api/reg",methods=["POST","GET"])
async def api_reg(request):
    if request.method=="GET":
        username = request.args.get("username","")
        password = request.args.get("password","")
        auth_key = request.args.get("auth_key","")
    else:
        username = request.json.get("username","")
        password = request.json.get("password","")
        auth_key = request.json.get("auth_key","")
    if auth_key!=AUTH_KEY:
        return json({ "code":99,"msg": "注册失败" })
    
    md5_pass = get_md5(password+"rustdesk")
    
    app = Sanic.get_app()
    check_nums = await app.ctx.poolmysqlasync.check_num_rows('rustdesk.rustdesk_users','username',username)
    if check_nums >= 1:
        return json({ "code":99,"msg": "注册失败!用户名重复！" })
    
    sql = "INSERT INTO `rustdesk_v2`.`rustdesk_users` (`username`, `password`) VALUES (%s, %s)"
    res = await app.ctx.poolmysqlasync.execute(sql,username,md5_pass)
    if res:
        return json({ "code":100,"msg": "注册成功" })
    else:
        return json({ "code":99,"msg": "注册失败" })

# 修改密码 请求 http://127.0.0.1:21114/api/set-pwd?username=test&password=test&new_pass=123456&auth_key=123456
@app.route("/api/repwd",methods=["POST","GET"])
async def api_re_pwd(request):
    if request.method=="GET":
        username = request.args.get("username","")
        password = request.args.get("password","")
        new_pass = request.args.get("new_pass","")
        auth_key = request.args.get("auth_key","")
    else:
        username = request.json.get("username","")
        password = request.json.get("password","")
        new_pass = request.json.get("new_pass","")
        auth_key = request.json.get("auth_key","")
    if auth_key!=AUTH_KEY:
        return json({ "code":99,"msg": "修改失败" })
    
    md5_pass = get_md5(password+"rustdesk")
    md5_new_pass = get_md5(new_pass+"rustdesk")
    
    app = Sanic.get_app()
    sql = "UPDATE `rustdesk_v2`.`rustdesk_users` SET `password` = %s WHERE `username` = %s and password = %s"
    res = await app.ctx.poolmysqlasync.execute(sql,md5_new_pass,username,md5_pass)
    if res:
        return json({ "code":100,"msg": "修改成功" })
    else:
        return json({ "code":99,"msg": "修改失败" })

# 自动生成数据库表
async def auto_generate_db():
    sql=get_init_db_table_sql()
    dbpool = PoolMysqlAsync()
    await dbpool.execute(sql)

if __name__ == '__main__':
    # 1.2.0 python 版本 flutter前端
    asyncio.run(auto_generate_db())
    print("数据库初始化完成")
    if DEBUG:
        app.run(host=IP, port=PORT, workers=1, access_log=True,debug=True,auto_reload=False)
    else:
        app.run(host=IP, port=PORT,debug=False, access_log=False,workers=1)
        # app.run(host=IP, port=PORT,debug=False, access_log=False, fast=True)
        
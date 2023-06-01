import asyncio
from sanic import Sanic, json
from sanic.response import text
from mysql_async import PoolMysqlAsync
from mytools import *
import json as json_tools
from sanic_ext import Extend
from config import CORS_ORIGINS,AUTH_KEY,IP,PORT,DEBUG

app = Sanic("rustdesk_api_sever_v1")
app.ctx.poolmysqlasync = PoolMysqlAsync() # async pool mysql
app.config.CORS_ORIGINS = CORS_ORIGINS
app.config.CORS_ALLOW_HEADERS = "*"
app.config.CORS_METHODS = "*"
app.config.OAS = False
Extend(app)

@app.route("/",methods=["GET"])
async def index(request):
    return text("欢迎使用rustdesk_api_sever_v1,作者github: https://github.com/gmyxds")

# 登录
@app.route("/api/login",methods=["POST"])
async def api_login(request):
    # 请求 post
    # web端登录，后面是空的 post {'username': 'name', 'password': 'pass', 'id': '', 'uuid': ''}
    # {username: name, password: pass, id: my_id, uuid: handler.get_uuid()}
    # 返回 error | 
    # { "access_token": "eyJhbGciOiJIUzI1", "user": { "name": "test" } }
    
    username = request.json.get("username","")
    password = request.json.get("password","")
    client_id = request.json.get("id","")
    uuid = request.json.get("uuid","")
    token = get_randomkeys(16)
    
    md5_pass = get_md5(password+"rustdesk")
    
    app = Sanic.get_app()
    sql = "SELECT id FROM `rustdesk_v2`.`rustdesk_users` where username = %s and password=%s"
    res = await app.ctx.poolmysqlasync.fetchone(sql,username,md5_pass)
    if not res:
        return json({"error":"username or password error"})
    
    # 删除旧token 防止重复登录导致的登录失败
    sql = "DELETE FROM `rustdesk_v2`.`rustdesk_token` WHERE `username` = %s and `client_id`=%s and `uuid`= %s "
    await app.ctx.poolmysqlasync.execute(sql,username,client_id,uuid)
    
    # 写入token
    sql = "INSERT INTO `rustdesk_v2`.`rustdesk_token` (`username`, `uid`, `client_id`, `uuid`, `access_token`) VALUES (%s,%s,%s,%s,%s)"
    res = await app.ctx.poolmysqlasync.execute(sql,username,res['id'],client_id,uuid,token)
    
    return json({"access_token":token,"user":{"name":username}})

# 更新地址簿
# username 等于 ---- 时不会进行保存
# 标签为空 不保存
@app.route("/api/ab",methods=["POST"])
async def api_ab(request):
    # authorization: Bearer eyJhb
    # 请求 post
    # { data: JSON.stringify(ab) }
    # {"data":"{\"tags\":[\"Liunx\",\"windows\"],\"peers\":[{\"id\":\"4444444\",\"username\":\"root\",\"hostname\":\"China\",\"alias\":\"1001\",\"platform\":\"linux\",\"tags\":[\"Liunx\"]}]}"}  
    # 新增id 需要自己补全其他字段
    # 改名
    # 修改标签
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
        return json({"code":99,"error":"登录超时！"})
    
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
        # 新建的时候只传一个id,补全一下
        temp_peer = {"id": "", "username": "", "hostname": "", "alias": "", "platform": "", "tags": [""]}
        for item in temp_peer:
            if item in peer:
                temp_peer[item] = peer[item]
        # 过滤自己显示的本机
        if temp_peer["username"]=="----":
            continue
        
        sql = "INSERT INTO `rustdesk_v2`.`rustdesk_peers` (`uid`, `client_id`, `username`, `hostname`, `alias`, `platform`, `tags`) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        res = await app.ctx.poolmysqlasync.execute(sql,uid,temp_peer['id'],temp_peer['username'],temp_peer['hostname'],temp_peer['alias'],temp_peer['platform'],json_tools.dumps(temp_peer['tags']))
    
    return json({"code":100,"data": "成功"})

# 获取地址簿
@app.route("/api/ab/get",methods=["POST"])
async def api_ab_get(request):
    # authorization: Bearer eyJhbGciOiJIU
    # 请求 post {}
    # 返回 error | 
    # {"updated_at":12,"data":json_tools.dumps({"tags":[],"peers":[]})}
    # {
    #     peers: [{id: "abcd", username: "", hostname: "", platform: "", alias: "", tags: ["","", ...]}, ...],
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
        })
    
    return json({ "updated_at":get_now_time_string(), "data": json_tools.dumps({"tags":tags,"peers":peers}) })
    # { "data": "{\"tags\":[\"123123\",\"sdafa\"],\"peers\":[{\"id\":\"1231312\",\"username\":\"\",\"hostname\":\"\",\"alias\":\"\",\"platform\":\"\",\"tags\":[\"\"]}}]}","update_at": "2023-05-28 00:02:41" }

# 心跳测试，一些动作会发到这个接口，返回空就行
@app.route("/api/audit",methods=["POST","GET"])
async def api_audit(request):
    return json({"code":100,"error":False,"data":"正常"})

# 退出登录
@app.route("/api/logout",methods=["POST"])
async def api_logout(request):
    # Authorization: Bearer eyJhbGciOiJI
    # 请求 post
    # {id: my_id, uuid: handler.get_uuid()}
    # 返回 无 没处理
    client_id = request.json.get("id","")
    uuid = request.json.get("uuid","")
    
    app = Sanic.get_app()
    sql = "DELETE FROM `rustdesk_v2`.`rustdesk_token` WHERE `client_id` = %s and uuid = %s"
    res = await app.ctx.poolmysqlasync.execute(sql,client_id,uuid)
    if res:
        return json({"code":100, "data": "退出成功" })
    else:
        return json({"code":100, "data": "退出失败" })

# 获取当前用户信息
@app.route("/api/currentUser",methods=["POST"])
async def api_currentUser(request):
    # authorization: Bearer eyJhbGciO
    # 请求 post
    # {id: my_id, uuid: handler.get_uuid()} 
    # 返回error |  还能返回400 401 会重置登录信息
    # { "name": "test" }
    
    client_id = request.json.get("id","")
    uuid = request.json.get("uuid","")
    auth_token = request.token
    
    app = Sanic.get_app()
    sql = "SELECT username FROM `rustdesk_v2`.`rustdesk_token` where client_id = %s and uuid=%s and access_token=%s"
    res = await app.ctx.poolmysqlasync.fetchone(sql,client_id,uuid,auth_token)
    if not res:
        return json({"error":"Wrong credentials","msg":"提供的登录信息错误"})
    
    return json({"name":res['username']})

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
    # 1.9.0 python版本 优化
    asyncio.run(auto_generate_db())
    print("数据库初始化完成")
    if DEBUG:
        app.run(host=IP, port=PORT, workers=1, access_log=True,debug=True,auto_reload=False)
    else:
        app.run(host=IP, port=PORT,debug=False, access_log=False,workers=1)
        # app.run(host=IP, port=PORT,debug=False, access_log=False, fast=True)
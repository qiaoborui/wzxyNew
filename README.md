

## 使用说明
本程序是一个自动完成我在校园晚签到的脚本
### 1. 配置文件
在使用之前，需要先创建一个配置文件，格式如下：

```toml
[[cron]]
expression = "0 22 * * *"

[[user]]
name = "姓名"
username = "用户名"
password = "密码"
school_id = "学校编号"

[[user]]
name = "姓名"
username = "用户名"
password = "密码"
school_id = "学校编号"
latitude = "纬度"
longitude = "经度"
province = "省份"
city = "城市"
area = "区"
township = "街道"
```
- name：你的姓名。
- username：登录校园晚签系统所用的用户名。
- password：登录校园晚签系统所用的密码。
- school_id：学校的编号。

目前有两种签到模式，分别为位置签到和区域签到。区域签到可以自动根据限制区域填写经纬度，而位置签到需要手动填写经纬度和地址信息。
- latitude：纬度。
- longitude：经度。
- province：省份。
- city：城市。
- area：区。
- township：街道。
请按照上述格式填写并保存为 config.toml 文件。
支持多用户使用，只需在配置文件中添加多个用户即可。

#### 1.1 学校编号

https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/getSchoolList 
访问上述链接，获取学校编号。

### 2. 运行程序
确保已经安装了所需的依赖，可以通过 pip install -r requirements.txt 安装。
在终端中运行 python wzxy.py 命令来启动程序。
程序将读取配置文件中的信息，并自动完成晚签到流程。
#### 2.1 调试模式
在调试模式下，程序将会输出更多的信息，以便于调试。
```shell
export ENV=DEV
```
```shell
python wzxy.py
```
### 3.Docker
```shell
docker pull qiaoborui/wzxynew:latest
```
```shell
docker run -itd -v /your/path/config.toml:/usr/src/app/config.toml --name wzxynew qiaoborui/wzxynew:latest
```
将 /your/path/users.toml 替换为你的配置文件路径。
#### 3.1 查看日志
```shell
docker logs -f wzxynew
```
或是进入容器内部查看日志
```shell
docker exec -it wzxynew /bin/bash
```
```shell
cat /usr/src/app/wozaixiaoyuan.log
```

### 感谢

我在校园最新的登录加密方法来自于 [NewWoZaiXiaoYuan](https://github.com/LinChiQ/NewWoZaiXiaoYuan)
@LinChiQ

# Mihomo/Clash Remote Server Manager

基础代理能力来自 [@MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo)。本仓库只提供一个轻量管理脚本，用来在远程 Linux 服务器上更方便地启动、停止、更新配置和查看日志。

这个小工具用于在远程 Linux 服务器上管理 `mihomo`/`clash`：

- 后台启动代理
- 自动选择脚本配置的 mixed-port，默认 `7897`，也可用 `MIHOMO_PORT` 覆盖
- 避免重复启动：如果已有记录中的 mihomo 进程在运行，`start` 不会再拉起第二个进程
- 查看运行状态和日志
- 停止代理
- 下载/更新 Clash/Mihomo 订阅配置
- 更换订阅 token
- 维护 VSCode/Codex/终端可用的代理环境变量文件

默认路径与你当前操作一致：

```text
~/.config/mihomo/clash-linux
~/.config/mihomo/config.yaml
~/.config/mihomo/mihomo.log
~/.config/mihomo/mihomo.pid
~/.config/mihomo/proxy.env
```

## 1. 准备 mihomo 基础文件

本节整理自 [bannedbook/fanqiang 的 Linux 教程](https://github.com/bannedbook/fanqiang/blob/5cb11c6420a95cdc83c4a29ffc54e2cd9e4689d4/linux/readme.md)，用于完成前期目录、二进制文件和地理数据库准备。

创建并进入程序目录：

```bash
mkdir -p ~/.config/mihomo
cd ~/.config/mihomo
```

下载 Linux amd64 版本的 mihomo/clash：

```bash
wget -O clash-linux.gz https://github.com/MetaCubeX/mihomo/releases/download/v1.17.0/mihomo-linux-amd64-v1.17.0.gz
```

如果这个版本链接失效，去 [MetaCubeX/mihomo Releases](https://github.com/MetaCubeX/mihomo/releases) 选择适合你服务器架构的 `linux-amd64` / `linux-arm64` 版本，并把下载后的文件放到：

```text
~/.config/mihomo/clash-linux.gz
```

解压并授权：

```bash
gzip -f clash-linux.gz -d
chmod +x clash-linux
```

初始化执行一次，让 mihomo 生成默认文件；启动后等一会儿，然后按 `Ctrl+C` 退出：

```bash
./clash-linux
```

查看目录：

```bash
ls -rtl ~/.config/mihomo/
```

如果 `Country.mmdb` 没有自动生成，可以手动下载：

```bash
wget -O ~/.config/mihomo/Country.mmdb https://github.com/Dreamacro/maxmind-geoip/releases/latest/download/Country.mmdb
```

如果 `GeoSite.dat` 没有自动生成，可以先用脚本后面的 `update-geodata` 命令补齐；或者手动下载后放到 `~/.config/mihomo/`：

```bash
wget -O ~/.config/mihomo/GeoSite.dat https://github.com/ewigl/mihomo/raw/master/GeoSite.dat
```

## 2. 克隆本管理脚本

在远程服务器上克隆这个仓库：

```bash
cd ~/.config/mihomo
git clone https://github.com/Zhixi-Li/mihomo-manager.git manager
```

进入仓库并确认脚本可执行：

```bash
cd ~/.config/mihomo/manager
chmod +x mihomoctl.sh
```

后续命令都在这个目录执行：

```bash
cd ~/.config/mihomo/manager
```

## 3. 首次配置订阅

注意：URL 一定要加引号，因为里面通常有 `&`。

```bash
./mihomoctl.sh init
./mihomoctl.sh set-url 'https://你的订阅地址/api/v1/client/subscribe?token=你的token&flag=clash'
./mihomoctl.sh fetch
```

`set-url` 原样保存 URL（不再擅自添加可能破坏签名的 `flag=clash` 参数），存到：

```text
~/.config/mihomo/subscription.env
```

这个文件权限会设置为 `600`。

`init` 还会创建或维护：

```text
~/.config/mihomo/proxy.env
```

并在 `~/.bashrc` 里追加一行 source hook：

```bash
[ -f "$HOME/.config/mihomo/proxy.env" ] && . "$HOME/.config/mihomo/proxy.env"
```

之后脚本会通过改写 `proxy.env` 来启用或停用代理环境变量，避免每次手动改 `.bashrc`。

## 4. 后台启动

```bash
./mihomoctl.sh start
```

`start` 会做几件事：

- 把 `config.yaml` 里的 `mixed-port` 写成当前脚本端口，默认是 `7897`
- 如果 `~/.config/mihomo/mihomo.pid` 指向的进程还活着，检查端口是否一致并刷新 `proxy.env`；端口改变时要求执行 `restart`，不会重复启动
- 后台启动 mihomo，并把日志写到 `~/.config/mihomo/mihomo.log`
- 启动成功后把代理环境变量写入 `~/.config/mihomo/proxy.env`

查看状态：

```bash
./mihomoctl.sh status
```

查看日志：

```bash
./mihomoctl.sh logs
```

持续跟踪日志：

```bash
./mihomoctl.sh logs -f
```

## 5. 让当前终端 / VSCode / Codex 走代理

启动成功后，默认代理端口是：

```text
127.0.0.1:7897
```

如果你想换端口，可以在命令前设置 `MIHOMO_PORT`。例如：

```bash
MIHOMO_PORT=7890 ./mihomoctl.sh restart
```

脚本会把 `config.yaml` 的 `mixed-port` 同步改成这个端口，并让 `env`、`run`、`test` 等命令使用同一个端口。

临时设置当前终端：

```bash
[ -f "$HOME/.config/mihomo/proxy.env" ] && . "$HOME/.config/mihomo/proxy.env"
```

也可以直接打印当前端口对应的代理环境变量：

```bash
./mihomoctl.sh env
```

测试：

```bash
./mihomoctl.sh test
```

如果返回 `401`、`403`、`404` 都说明网络连到了，只是 API 身份或路径问题；如果超时才是代理/网络问题。

也可以只让某条命令走代理：

```bash
~/.config/mihomo/manager/mihomoctl.sh run curl https://api.openai.com/v1/models -I
```

如果你想让远程 VSCode/Codex 总是继承代理，可以把下面这行放进 `~/.bashrc`：

```bash
[ -f "$HOME/.config/mihomo/proxy.env" ] && . "$HOME/.config/mihomo/proxy.env"
```

然后：

```bash
source ~/.bashrc
```

之后在 VSCode 命令面板执行：

```text
Remote-SSH: Kill VS Code Server on Host...
```

重新连接服务器，让 VSCode Server 继承新的环境变量。

## 6. 一键查看和切换节点

查看当前节点和全部可选节点：

```bash
./mihomoctl.sh nodes
```

不带参数时会打开交互式编号菜单，输入编号即可切换：

```bash
./mihomoctl.sh switch
```

也可以按地区一键切换。脚本会选择该地区列表中的第一个节点：

```bash
./mihomoctl.sh switch 英国
./mihomoctl.sh switch 美国
./mihomoctl.sh switch 日本
```

常用英文缩写也可以使用，例如 `UK`、`US`、`JP`、`HK` 和 `SG`：

```bash
./mihomoctl.sh switch UK
```

要设置启动后的默认节点，并立即切换到该节点：

```bash
./mihomoctl.sh set-default-node 英国
```

默认节点保存在 `~/.config/mihomo/subscription.env` 中。以后重新启动 Mihomo 时会自动应用，执行 `fetch` 更新订阅也不会丢失。节点切换通过本机控制接口完成，不需要重启 Mihomo。该功能需要系统已安装 `curl` 和 `jq`。

## 7. 更换 VPN/订阅 token

如果只是 token 变了：

```bash
cd ~/.config/mihomo/manager
./mihomoctl.sh set-token 新token
./mihomoctl.sh fetch
./mihomoctl.sh restart
```

如果整个订阅地址变了：

```bash
./mihomoctl.sh set-url 'https://新的订阅地址?token=新token&flag=clash'
./mihomoctl.sh fetch
./mihomoctl.sh restart
```

## 8. 停止代理

停止后台 mihomo/clash：

```bash
cd ~/.config/mihomo/manager
./mihomoctl.sh stop
```

取消当前终端里的代理环境变量：

```bash
. ~/.config/mihomo/proxy.env
```

`stop` 会把 `proxy.env` 改成 unset 版本，所以 source 之后当前终端也会取消代理。

也可以直接执行：

```bash
eval "$(./mihomoctl.sh env-clear)"
```

如果你以前把 `eval "$($HOME/.config/mihomo/manager/mihomoctl.sh env)"` 写进了 `~/.bashrc`，建议删掉或注释掉，改用 `proxy.env` 那一行。这样 `start` 和 `stop` 才能自动控制新 shell 是否启用代理。

## 9. 更新 GeoSite / GeoIP

如果配置依赖 `GeoSite.dat` / `GeoIP.dat`：

```bash
cd ~/.config/mihomo/manager
./mihomoctl.sh update-geodata
./mihomoctl.sh restart
```

## 10. 常见问题

### `cannot unmarshal !!str c3M6Ly9...`

下载到的是 base64/raw 节点订阅，不是 Clash/Mihomo YAML。解决：

```bash
./mihomoctl.sh set-url '你的订阅URL&flag=clash'
./mihomoctl.sh fetch
```

### 命令执行后出现 `[1] 12345`

URL 没加引号，shell 把 `&flag=clash` 当成后台运行符号了。订阅 URL 必须用单引号包住。

### 代理启动了，但 Codex 还是连不上

先检查：

```bash
./mihomoctl.sh status
. ~/.config/mihomo/proxy.env
./mihomoctl.sh test
```

如果 `curl` 能连，但 VSCode/Codex 不行，重启 VSCode Server：

```text
Remote-SSH: Kill VS Code Server on Host...
```

然后重新连接远程服务器。

### 启动时报端口占用

如果日志里出现 mixed proxy port bind 失败，说明当前端口被占用。先看当前脚本配置：

```bash
./mihomoctl.sh config
```

然后换一个端口启动：

```bash
MIHOMO_PORT=7898 ./mihomoctl.sh restart
```

新端口会同步写入 `config.yaml` 和 `proxy.env`。如果你要长期使用该端口，可以把下面这行写进 `~/.bashrc` 中 `proxy.env` source hook 之前：

```bash
export MIHOMO_PORT=7898
```


## 11. 多订阅保存与一键切换（新版）

先保存现有订阅，再添加其他订阅。名称只接受字母、数字、下划线和连字符：

```bash
./mihomoctl.sh profile save old
./mihomoctl.sh profile add provider-b 'https://你的第二个Clash订阅URL'
./mihomoctl.sh profile list
./mihomoctl.sh profile use provider-b
./mihomoctl.sh profile use old
```

`profile use` 自动下载、校验配置并重启，无需再执行 fetch/restart。下载或校验失败会保留原配置和订阅。启动后的运行情况仍需通过 `status`/`test` 检查（例如端口冲突或订阅节点不可达）。订阅必须输出完整 Clash/Mihomo YAML；脚本不提供订阅格式转换服务。下载使用 Clash.Meta User-Agent；如服务商要求特定参数，请自行保留在 URL 中。

每份订阅单独保存 URL、User-Agent、默认节点及节点组，文件位于 `~/.config/mihomo/profiles/`，权限为 600。使用 `profile use` 激活后，`set-url`、`set-token`、`set-selector` 和 `set-default-node` 的修改也会同步到该订阅。不要将这些私密文件提交 Git。

### 不同订阅的节点组

新版通过 `/proxies` 查询节点组，不再写死“🔰 选择节点”。只有一个 Selector 时自动使用；多个时列出可选组，需要明确选择一次：

```bash
./mihomoctl.sh groups
./mihomoctl.sh set-selector '你的主代理组名'
./mihomoctl.sh nodes
./mihomoctl.sh switch US
./mihomoctl.sh set-default-node US
```

下次切回这份订阅会恢复以上设置。`MIHOMO_SELECTOR` 仍可临时覆盖。仅对所选组的直接候选进行切换；若该组的候选是子组，需要通过 `set-selector` 选择实际包含节点的子组。脚本不改写服务商的路由规则，不会自动把所有流量改成全局模式。

US/UK/JP/HK/SG 支持常见中英文和旗帜命名；其他地区支持原有中文别名或直接输入节点名。精确节点名优先，其次匹配列表中的第一个候选，不自动测速。

### 原来的 404 与端口问题

`/proxies/组名` 的 404 通常表示节点组不存在，并不表示 Mihomo 没启动。新版先查询 `/proxies`，提供具体组名提示。本机 API 请求强制绕过 HTTP/SOCKS 代理。缺少 external-controller 时补入本机 `127.0.0.1:9090`；已有的 controller 和 secret 保留。启动会等待 `/version` 返回有效版本，才启用代理环境文件。

`start` 对已运行进程不会热更新端口。修改端口请使用：

```bash
MIHOMO_PORT=7890 ./mihomoctl.sh restart
. ~/.config/mihomo/proxy.env
```

后续命令从 config.yaml 读取已保存的 mixed-port，不需要每次传环境变量。`set-url` 只是保存地址，普通订阅更新仍需 `fetch` 后 `restart`；`profile use` 会完成整套操作。

### 开发验证

```bash
bash -n mihomoctl.sh
python3 -m unittest discover -s tests -v
```

测试使用本机模拟 API 和临时目录，不下载真实订阅、不需要运行 Mihomo。

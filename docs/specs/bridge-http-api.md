# mc-mcp-bridge ↔ aibuild-mod HTTP API 契约(v0.1)

两个模块各自独立开发,本文件是唯一接口约定。改动必须双方同步。

## 总则

- **Base URL**:`http://127.0.0.1:<port>`(mod 每次启动随机端口,经 bridge 启动参数 `--port` 传入)
- **认证**:每个请求带 header `X-Aibuild-Token: <token>`(mod 启动时随机生成,经 `--token` 传入);校验失败 → `403 {"error":"forbidden"}`
- **格式**:请求一律 `application/json`;响应除 render 外一律 `application/json`
- **坐标**:`"min":[x,y,z]` / `"max":[x,y,z]`,**闭区间**(含两端),int
- **方块 id**:命名空间全称,如 `"minecraft:stone_bricks"`;非法 id → `400 {"error":"...","suggestions":["minecraft:stone_bricks",...]}`
- **捎带**:任何 JSON 响应在玩家收件箱非空时附带 `"player_messages":["..."]` 字段;bridge 将其追加进工具返回的文本内容
- **错误码**:400 参数错误(可带 suggestions)/ 403 认证 / 409 状态冲突(写工具锁定、已有 agent 在跑)/ 500 内部错误

## 写工具(异步,返回 job)

### POST /tools/fill
```json
{"min":[x,y,z],"max":[x,y,z],"block":"minecraft:stone_bricks","mode":"replace"}
```
`mode` ∈ `replace|keep|outline|hollow`,可省略默认 `replace` → `200 {"job_id":"..."}`

### POST /tools/set_blocks
```json
{"blocks":[{"x":0,"y":64,"z":0,"block":"minecraft:oak_planks"}]}
```
单请求 ≤ 4096 条 → `200 {"job_id":"..."}`

### POST /tools/set_block
```json
{"x":0,"y":64,"z":0,"block":"minecraft:torch"}
```
→ `200 {"job_id":"..."}`

### GET /tools/job_status?id=<job_id>
→ `200 {"job_id":"...","state":"running|done|failed","total":1000,"placed":640,"failed":0,"errors":[]}`

## 读工具(同步)

### POST /tools/get_block
`{"x":0,"y":64,"z":0}` → `200 {"block":"minecraft:oak_stairs","properties":{"facing":"north","half":"bottom"}}`

### POST /tools/search_blocks
`{"query":"stained_glass"}` → `200 {"matches":["minecraft:white_stained_glass","..."]}`(子串模糊匹配,≤ 16 条;无命中返回空数组)

> 注:`set_blocks_from_file` 是 **bridge 本地工具**,无对应 HTTP 端点——bridge 读文件(JSON 或 .schem)后自动分解为多个 `/tools/set_blocks` 调用。

### POST /tools/get_region_summary
`{"min":[...],"max":[...]}` → `200 {"text":"方块统计 + 每层 ASCII 平面图"}`
体积 ≤ 262144(64³);输出 ~200 行内(top 12 方块计数 + 至多 8 个采样层的 ASCII 平面图,大区自动降采样)

### POST /tools/get_terrain_summary
`{"center":[x,z],"radius":64}` → `200 {"text":"高度图/水体/坡度/平坦度摘要(含 ASCII 高度图)"}`

### POST /tools/render_region
`{"min":[...],"max":[...],"azimuth":45,"elevation":45,"mode":"auto","projection":"persp"}` → `200` body 为 **PNG 二进制**(`Content-Type: image/png`)
- `azimuth`/`elevation`:度,可省,默认 45/45;`mode`/`projection` 可省
- `mode` ∈ `auto|gl|topdown`,默认 `auto`:有客户端(单人游戏)走 GL 真渲染,否则走服务器端俯视光栅;`gl`/`topdown` 强制指定,但 GL 不可用或失败时仍优雅回退 topdown(对调用方透明)
- `projection` ∈ `persp|ortho`,默认 `persp`,仅 GL 路径有效
- 实际使用的渲染路径经响应头 `X-Aibuild-Render-Mode: gl|topdown` 返回
- 区域体积 ≤ 262144(64³);PNG 同时落盘一份到 `<世界>/aibuild/renders/` 供玩家查看

## 流程工具

### POST /tools/propose_site
`{"min":[...],"max":[...]}` → `200 {"status":"pending_confirmation","message":"等待玩家确认"}`;已确认后写工具解锁(此前写工具请求 → `409 {"error":"site not confirmed"}`)

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

### POST /tools/get_region_summary
`{"min":[...],"max":[...]}` → `200 {"text":"方块统计 + 每层 ASCII 平面图"}`

### POST /tools/get_terrain_summary
`{"center":[x,z],"radius":64}` → `200 {"text":"高度图/水体/坡度/平坦度摘要(含 ASCII 高度图)"}`

### POST /tools/render_region
`{"min":[...],"max":[...],"azimuth":45,"elevation":45}` → `200` body 为 **PNG 二进制**(`Content-Type: image/png`);主渲染失败时返回回退渲染的 PNG(对调用方透明)

## 流程工具

### POST /tools/propose_site
`{"min":[...],"max":[...]}` → `200 {"status":"pending_confirmation","message":"等待玩家确认"}`;已确认后写工具解锁(此前写工具请求 → `409 {"error":"site not confirmed"}`)

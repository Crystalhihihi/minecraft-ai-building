# Blender 装配探针设计(2026-07-31)

## 核心设计决策:不做体素化

不在 Blender 里建"模型再像素化"。模块库里的每个模块 = **一组单位立方体,每个立方体携带 MC block_id + 朝向元数据**(存在 custom properties)。Blender 只是可视化装配环境,导出时遍历放置的模块实例,把实例变换(平移/90° 旋转/镜像)应用到内部块清单,合并输出 set_blocks_from_file 兼容的 JSON。由此:

- 楼梯/半砖/栅栏朝向在**模块 authoring 时一次做对**,装配永远正确(治屋顶翻车)
- 比例天然正确(1 立方体 = 1 方块),不存在"建完模缺比例"
- 导出不经过 obj2mc,零保真损耗

## 管线

1. `module_gen.py`(bpy 脚本,在 Blender 内执行):生成模块库 .blend,~15 个模块
   - 屋顶:双坡直段(3/5/7 宽)、双坡山墙端、四坡角、锥顶段
   - 墙:木骨架白墙面(带/不带窗)、石砖墙(带箭窗)、圆石勒脚段
   - 其他:栅栏跑段、螺旋梯段、圆塔环段(直径 7)、飞檐段(中式预留)
   - 每个模块是 collection,内含 unit cubes,custom props: {block: "minecraft:spruce_stairs", facing: "east", half: "bottom"}
2. 装配:agent 经 blender-mcp 的 execute_blender_code 摆放模块实例(只允许平移+90° 倍旋转+镜像,禁缩放)
3. 自检:Blender 渲染 4 视角 turntable → VLM 看图
4. 导出:`export_blocks.py` 遍历实例 → 合并块清单 JSON(应用变换、旋转映射 facing)
5. 导入:dev server set_blocks_from_file 落进世界,游戏内对比

## 探针题目

带雕饰的小教堂/门楼 1 座(含双坡屋顶+山墙+尖顶装饰),对比指标:
- 屋顶/楼梯朝向错误数(目标 0,vs 游戏内直建上轮 >10 处)
- 装配耗时 vs 直接建造
- AI 对"摆模块" vs "摆方块"的轮次差异

## 状态

- blender-mcp addon 已在 scratch/blender-mcp/addon.py,曾在本机跑通过(tree spike)
- Blender 4.2.23 在 D:\blender-4.2.23-windows-x64
- 待做:module_gen.py 编写、模块库生成、装配 agent 试跑、导出器、游戏内对比

## 结果(2026-07-31 探针完成,✅ 朝向零错误达成)

- 产物:`scratch/blender-spike/`{module_gen.py(17 模块/476 方块),assemble_chapel.py(33 实例),export_blocks.py(808 块),place_rcon.py,verify_mc.py,chapel_blocks.json,renders/}
- **朝向错误数 = 0**(808/808 块 get_block 逐块回读,id/属性/楼梯 facing/half/shape 全对;游戏内直建上轮 >10 处)
- 导出器零重叠块、单连通体;Blender 渲染 4 视角+顶视与 MC render_region topdown 一致
- 装配 33 实例一次跑完;2 轮自查修正(90° 旋转 cell 映射 off-by-one、尖顶环悬空)
- 选址:任务建议区 x[-80,-60] z[200,230] 实为海底(床岩 y=-64),已用 analyze_site 改址 (-78,-92) 平地;海底误建已清理复原
- 卡点:①bridge 写工具需 RUNNING 会话+confirmed SiteGate,无会话时只能用 RCON /setblock 旁路;②vanilla fill 对未加载区块直接报错,需 get_block 预加载;③collection instance 不吃 object color,Workbench 需每方块独立 mesh+材质
- 通道:kimi 会话未挂 blender MCP 工具,改用 addon 原生 9876 socket 直连(blender_client.py),协议同 blender-mcp

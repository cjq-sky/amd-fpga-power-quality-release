# PQ 离线波形生成器 v0.2.1
这是电脑端独立命令行工具，不是 FPGA 驱动，不连接或操作 AWG。Python 3.10+，无需第三方库。

## 使用
在本目录执行：
```powershell
python wavegen.py --config s0_s1.json --output ../../outputs/pq_wavegen_S0_S1_v010
```
输出目录必须尚不存在，避免覆盖已有证据。修改 JSON 即可改变基波、谐波 ratio（0.05 表示5%）、phase_rad（弧度）、相对基波峰值。noise_rms_relative 为相对基波峰值的噪声标准差，启用时必须提供 seed；这不是 SNR 参数。
固定为 calibration_dev，正式标签始终为空。支持整数周期稳态记录及暂升/暂降/中断事件、谐波复合与多事件序列。尚不包含扫频、自动下载公开数据和模型训练。

## 新增事件功能

在本目录执行：
```powershell
python wavegen.py --config events_demo.json --output outputs/my_event_candidates
```
示例含正常、50%剩余幅值暂降、1.15倍暂升、完全中断、暂降+H3/H5、暂升+H3及三事件序列，共7个候选。输出目录必须不存在。修改配置即可批量生成不同深度、起点、时长、过渡斜坡、相位与谐波配比；不同配置不是自动独立测试来源。

每个case可添加events数组，各项字段：

| 字段 | 含义 |
|---|---|
| kind | sag、swell、interruption |
| start_s | 事件起点，秒 |
| duration_s | 总时长，包含进入和退出斜坡 |
| level | 相对正常幅值的剩余倍数；0.5为剩余50%，不是下降0.5V |
| ramp_in_s / ramp_out_s | 线性进入/退出时间，默认0，即突变 |

事件时刻必须落在采样网格上，不会静默四舍五入。按时间顺序列出，不能重叠，必须位于记录内部并保留正常首尾；两条斜坡时长之和必须小于事件时长。sag要求0<level<1；swell要求level>1；interruption要求level=0。接近零的残余电压可用sag生成，是否属于物理中断由后续事件规则判定，生成器不冻结标准门限。

每case可设置event_scale_mode：默认all_ac同时缩放基波和全部谐波；fundamental_only只缩放基波，保持谐波绝对幅值。后者在基波下降时会增大相对谐波比值。相位连续，事件不重启正弦相位。

dc_offset_relative为加性直流，默认0，单位同value_relative；噪声在包络之后叠加、相对正常基波峰值，需显式seed。中断期间直流和噪声仍在；fundamental_only也不会消除其他谐波。参数名称是数字设计意图，不是实测标签。

每条新增envelope.csv和metadata内事件索引、平台区间。区间采用[start,end)；下降斜坡起点仍为正常幅值，退出到end才回正常。标注不等于滑动RMS检测器的阈值交越时刻。事件预览显示完整记录，稳态预览仍显示前两个周期。

整段重复率=1/duration_s，独立于基波50Hz。例如1秒记录按1Hz重复会每秒重现全部事件，不能设置成50Hz整段重复。只输出一次事件需要仪器Burst/触发设置及实机确认，软件不会操作仪器。

事件边沿会产生宽带频谱。谐波频点的奈奎斯特检查不代表事件边沿无混叠；可增加斜坡时间并在AWG/ADC实际带宽下核验。整段DFT受事件调制影响，只是诊断，不是平台谐波真值，也不能替代PL THD。

## 验证和限制
覆盖稳态回归、暂降比例/恢复、中断残余、两种谐波缩放、斜坡边界、多事件、非法时间/重叠、种子复现、不覆盖原输出和暂升码值溢出。无仪器参与的软件测试不能证明实机通过。

BIN仍需有依据的编码profile。暂升/谐波叠加可能超出已有4500/5000码幅度预算，超限直接拒绝，绝不自动归一化或削顶。需要显式调整设计幅值或映射并重新测量，不能无条件沿用旧正弦的实机设置。事件示例默认只生成CSV和元数据，没有伪造VERIFIED配置。

## 输出
每条 source.csv、metadata.json、preview.svg；总 manifest.json、preview.html、validation.json及输入配置副本。DFT用于源点验证，不能替代实测。预览纵轴自动缩放，不用于比较物理电压。
派生波形必须显式沿用 lineage_group_id。重复波形计数仅检查完全相同的数值序列，不证明统计独立；相位变化也不自动赋予独立测试资格。

## BIN 导出接口
默认不输出 BIN。可通过 --bin-profile 指定经A/C核验的JSON配置，字段：status=VERIFIED、evidence_reference、header_hex（48字节）、verified_max_points、code_center、codes_per_relative_unit、verified_code_min、verified_code_max，以及实际负载/幅度/偏置等可追溯说明。
采用 code=round(code_center+codes_per_relative_unit*value_relative)，不自动归一化或裁剪。仅支持当前观察到的48字节头、偏移12小端点数、16位小端样本布局。配置状态是人工声明，程序不能验证证据真实性；不能自行标VERIFIED绕过硬件核验。
目前未提供真实已验证编码配置，因此不宣称实际BIN输出已验收。ADC±10V已有确认，不代表AWG输出应接近量程。

## 与FPGA_B关系
可以同仓库独立 tools/pq_wavegen 目录，也可单独仓库。不要放进板端Adapter或推理调用路径。源波形用于激励；训练输入仍来自实板完整Feature和对应版本Adapter。

## 状态
电脑端生成、参数检查、源点频谱检查和受控编码接口已实现。实机码值映射、设备兼容、输出校准待关联A/C证据。当前不冻结分类阈值、正式split或实机通过结论。

## v0.2.1：BIN检查与导出统一入口

以下命令在本目录执行，profile.json替换为有A/C核验依据的编码配置。本版没有伪造或附带实机VERIFIED配置；测试中的全零头仅供软件测试。

生成时同时导出并回读检查：
```powershell
python wavegen.py --config s0_s1.json --output outputs/my_sources_bin --bin-profile profile.json
```
每个候选目录新增BIN和bin_check.json，总目录保存encoding_profile.json。

从已有v0.2候选导出，无需重新生成：
```powershell
python wavegen.py --export-source outputs/my_sources/CASE_ID --output outputs/my_bin_export --bin-profile profile.json
```
每次指定一个含source.csv和metadata.json的候选目录。导出目录含waveform.bin、bin_check.json、encoding_profile.json，原件不改写。检查源哈希、点数、时间网格和时长后编码、回读。

独立检查BIN，并逐点核对源：
```powershell
python wavegen.py --check-bin outputs/my_bin_export/waveform.bin --bin-profile profile.json --compare-source outputs/my_sources/CASE_ID --output outputs/my_bin_check.json
```
省略--compare-source只检查结构、头、长度、点数与码值范围；报告source_compared=false，不能证明与某个源一致。省略--output将报告打印到终端。失败退出码为2；输出文件或目录存在时拒绝覆盖。

报告包含BIN/配置哈希、证据引用、码值极值、上下限余量和首尾跳变。对照源时另含源CSV/元数据哈希、最大量化误差、半LSB相对幅值、采样率和整段重复率。Python round采用半值取偶；未舍入映射超限即拒绝，不自动归一化或削顶。新CSV保存17位有效数字，重新导出与直接生成逐字节一致；旧CSV按照实际保存数值编码。

SOFTWARE_CHECK_PASS仅表示软件检查通过。hardware_verified和training_eligible始终为false，配置VERIFIED是人工声明，不是程序独立鉴定。AWG加载与测量、实板采集、参考标签审核仍需完成。

原工具验证包含17项生成器测试，覆盖三个命令入口、篡改拒绝和重导出一致性。既有结果摘要见../../references/source_verification.json；测试程序不随本工具快照提供。

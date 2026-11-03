# 文件检查与系统观察指南

本页说明如何使用现用入口观察和判定。文件检查、预期输出与真实板端结果分别记录；以下步骤由实际部署者执行，不属于--check。

## 先核对身份

从根目录执行python -B run.py --check和python -B run.py --plan。文件身份、Python3.10语法、原59项payload、BIT/HWH、十窗口及AI/技能/PL合同须PASS；硬件、推理与构建为NOT_RUN。PL独立检查为python -B build/scripts/check_pl.py。

通过只表示检查范围内的文件一致，不代替实板、模型或资源/时序验收。--precheck在合格板端读取环境/文件/占用状态，不编程PL，不读取MMIO。期望ready_for_original_startup=true；完整冷启动仍须由操作者确认。

## 现用应用观察步骤

先完成[接线](hardware_setup.md)、[环境](environment.md)及[部署](run_guide.md)。只启动根run.py，出现STAGE4_READY后在同一ui4>逐条操作：

```text
touch on
auto on
status
capture overview
capture waveform
capture events
capture harmonics
status
```

capture是现有主程序命令，消费同一Reader的共享状态并串行提交，不是独立测试入口。每条返回后再继续；可按实际观察选择页面。没有STAGE4_READY时不把等待/失败当成已显示。

|对象|预期输出与通过条件|不据此推导|
|---|---|---|
|加载|IDENTITY_CHECK_PASS，配套固件、100/125MHz和MMIO身份正确|任意固件或任意内核均可用|
|主链|STAGE4_READY；acquisition_status为LIVE，所有者/会话一致|全工况、长期稳定性|
|Feature|有效RMS/Peak/Crest、CH1频率、两路频谱字段；有限值及有效性门控|物理校准准确度、CH2独立频率|
|Raw|uint32[2048]/8192字节，拆分两路int16[2048]，完整复制/复核/ACK后发布|所有Raw必与Feature同帧|
|关联|帧号/epoch/关联状态真实；UNMATCHED独立解释|相邻帧可以补成同帧|
|事件|两路独立基准与状态，event_error按真实值记录；缺口停止，不报虚假正常|仅一次正常输入覆盖全部扰动|
|模型|CH1合格六维输入及同帧/新鲜度门控，候选类别和概率按原合同呈现|正式泛化准确率、校准概率或CH2模型|
|Frame Retire|seq/generation、新旧槽、ACCEPTED/RETIRE/ACK一致；ACK确认后退还旧槽|软件返回等于独立AXI总线测量|
|HDMI/触摸|实际看到四页、自动更新和正确切页；保留Buffer所有权|60FPS、无撕裂或长期运行指标已测量|
|PC|浏览器和HDMI来自同一SnapshotStore，网络重连不新建Reader|断网后画面仍是当前有效值|

Raw ACK与显示退休ACK是不同机制，不混用计数。drop累积和新增值均保留，不以清计数实现“零丢帧”。既有正常基准、候选资格及受控输入不当作传感器标定。

## 参考工况和判据

已知正常参考输入为正弦50Hz、1Vpp、Offset0、High-Z、ON；参考需按实际负载、接线和波形确认。CH1/CH2的nominal_rms_code分别为1152.9852916757695及1157.8141936125858，两者来自各自受控参考。

|工况|现用检测规则|尚需随提交记录提供|
|---|---|---|
|正常|0.9≤rms_pu≤1.1为NORMAL|实测参考、通道、稳定区间|
|暂降|0.1≤rms_pu<0.9为SAG|实际幅度、起止/持续时间及参考记录|
|暂升|rms_pu>1.1为SWELL|同上，不能超出实际输入电气范围|
|中断|rms_pu<0.1为INTERRUPTION|零/低输入如何形成，不把OFF或悬空当标准零|
|谐波分类|CH1六维、四类候选，按批准来源标签对照|谐波比例/相位、仪器profile、独立参考与批准用途|

标称10kHz/50Hz对应200点滑动窗口及10ms保持确认；这不是屏幕端到端延迟。十组发生器BIN及面板配置见[data](../../data/README.md)，该批含0.06Vpp补偿，实际测量参考、幅频容差和允许延迟未随输入提供。缺少已批准数值时，最多记录观察现象，不自行生成精度PASS线。

## 日志与结果定位

根目录下board/runtime/frame_retire_125/results/在实际运行时生成，不随源码提交。当前boot的load_identity_<boot>.jsonl记录加载；live_ui4_<boot>/内包括：

|文件|用途|
|---|---|
|events.jsonl|启动、MMIO、提交、触摸、status与故障事件|
|FRAME_RETIRE_ITERATIONS.jsonl|显示帧提交/退休/ACK的逐轮身份|
|event_results.jsonl|通道事件与缺口等结果|
|model_results.jsonl|合格/拒绝输入及模型结果|
|snapshot_*.json|HDMI与PC共享的不可变显示快照，含Feature/Raw各自身份|
|ui_worker.log|唯一读取/事件/模型工作线程诊断|
|render_worker.stderr.log|独立纯光栅进程诊断，不拥有Reader或MMIO|

选择一条结果时同时记录：软件payload身份、BIT/HWH SHA256、boot/session/epoch、输入来源/工况、目标帧或seq、参考结果、结论和限制。完整原始资料保留原处；提交包只挑必要、同版本、可核对的结果。不把个人电脑文件位置写入提交说明。

## 哪些已有材料可复用

125MHz综合、资源、两模型时序、布线、CDC、DRC与发布检查中的8份必要原报告已选入[build/reports](../../build/reports/frame_retire_125/README.md)，原正文保持字节身份，仅对Host/输出路径头脱敏。未单独提供的板端结果不创建文件或本机位置入口。

现用UI14整机联调状态不因旧报告的“后续接入”描述被降级。现有波形仅作为验证输入，不新增未取得的整机验收记录。技能包中的既有黄金与EV26资料只覆盖自身数值/计分范围。

## 停止与失败

记录原始失败，不自动重载固件、不放宽身份、标签或帧资格。auto off只暂停新提交，不释放DMA。保持owner及引用，通过另一终端sudo poweroff后完整断电。详细分流见[排障](troubleshooting.md)。


已有六组模块仿真结果见[sim](../../sim/README.md)，记录包含原标记与源码对应关系。模块结果、架构/实物报告、现用整机验收分开，不重复执行或将不同范围合成一次完整测试。

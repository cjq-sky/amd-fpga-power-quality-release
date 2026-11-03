# 既有模块仿真结果

本目录保存六组已存在的模块级仿真记录，原运行日期为2026-11-02，均为既有结果。技术报告负责原理、优化对比、实物与界面展示，本目录补充可核对的模块结果，二者互相引用，不复制整份报告或全部历史资料。

|记录|原始结果|与现用源码的关系|
|---|---|---|
|[聚合定向用例](results/aggregator_directed.txt)|10项分项PASS及最终metadata PASS|Aggregator与Snapshot Bank均逐字节一致|
|[聚合随机对照](results/aggregator_random.txt)|100000周期、98969次决策对照|同上；有限逐周期对照，不是形式证明|
|[配置两级预计算](results/config_precompute.txt)|17729样本、28输出；60区间组合、361次SESSION检查、2084次COMMIT|现用frame_retire_registers逐字节一致|
|[AXI控制桥](results/control_bridge.txt)|513次读、513次写、1次在途复位|RTL逐字节一致，原双时钟条件100/142MHz，不能代替最终100/125MHz整机CDC|
|[Frame Retire协议](results/fence_protocol.txt)|19工况、153次外部AR|仅默认Deadline与现用不同；测试显式覆盖500周期|
|[队列压力对照](results/fence_queue.txt)|48000周期、2402次完成、49次同时操作、2390次提升；bypass=0|同上；bypass=0保持原结果，不宣称该分支已覆盖|

机器可读结果、原日志与测试平台身份以及DUT对应关系见[结果集合](results/module_results.json)。TXT是原始PASS行节选，不是完整原日志；源码对应和参数差异在结果集合中说明。

## 适用范围

四组结果直接绑定与现用逐字节一致的DUT。Fence两组绑定原head实现与现用逻辑：源码仅默认DEADLINE_CYCLES由142857132变为125000000；两个原测试均显式设置DEADLINE_CYCLES=500、FRAME_BYTES=256、LINE_BYTES=64，QDEPTH保留64。文件核对不等于用现用默认参数重新跑过；不外推为生产一秒超时、完整720p/125MHz整机仿真或上板签核。

配置预计算的首次编译失败属于测试平台诊断声明顺序，修正后原记录在新目录重试成功；候选RTL未改变。日志中的三段被动对照反例为预期负对照，不隐藏为全程无失败；正式机器形式证明仍NOT_PROVEN。聚合和配置均为有限激励，不穷尽全部状态。

## 文件边界

按工程包只保留结果的范围，不带testbench、独立测试入口、官方仿真源码、wdb/vcd、生成项目或缓存。此目录本身不提供仿真重跑能力；它用于说明既有功能正确性如何确认。当前工程构建和板端部署步骤仍以[总手册](../docs/reproducibility/reproduction_guide.md)为准。

根python -B run.py --check只核对本目录文件身份，不运行这些历史用例。现用完整整机功能还应由其对应版本的板端记录说明，不能用本目录替代。

# 波形生成与BIN校验技能包

版本：1.0；冻结工具：pq_wavegen v0.2.1；版本日期：2026-11-02。

## 适用范围

在电脑上生成周期基波、谐波及暂降/暂升/中断候选；从已有源导出BIN；检查BIN结构及其与源的一致性。供其他队伍修改配置复用，不依赖本队板卡、六维特征或分类标签。Python 3.10+，无第三方依赖。所有命令从本技能包目录执行，可以直接按命令使用。

## 最小使用方法

先生成不涉及仪器编码的CSV样例，输出目录必须不存在：

```powershell
python assets/pq_wavegen/wavegen.py --config examples/minimal.json --output run_001
```

查看 run_001/validation.json、manifest.json、preview.html，以及各case的source.csv、metadata.json。完整参数与事件示例见 assets/pq_wavegen/README.md、s0_s1.json和events_demo.json。ratio=0.05表示5%，phase_rad为弧度，数值幅度为相对值而非伏特。

已有真实编码依据时，将profile.json换成自己的配置文件：

```powershell
python assets/pq_wavegen/wavegen.py --config examples/minimal.json --output run_bin_001 --bin-profile profile.json
python assets/pq_wavegen/wavegen.py --export-source run_001/EXAMPLE_SINE --output export_001 --bin-profile profile.json
python assets/pq_wavegen/wavegen.py --check-bin export_001/waveform.bin --compare-source run_001/EXAMPLE_SINE --bin-profile profile.json --output check_001.json
```

三条命令分别为直接生成并导出、已有源导出、独立回读对照。profile字段、编码公式及布局见原工具README。随包没有可直接用于真实仪器的VERIFIED配置。测试代码中的全零头是软件夹具。

## 输出和通过标准

命令退出码0且报告无失败方可记录软件通过；失败通常退出码2。BIN检查应记录SOFTWARE_CHECK_PASS、source_compared、文件/配置哈希、点数、码值范围及量化误差。对照源时应source_compared=true；不对照只能证明结构检查通过。工具拒绝超限而不自动削顶或归一化。具体字段以实际JSON为准。

通过软件检查不代表AWG兼容、物理电压正确、实板采集通过或标签合格；hardware_verified和training_eligible保持false。生成结果固定为calibration_dev，正式标签为空。

## 已验证效果与证据

历史独立交付记录中，生成器17项测试通过，覆盖三种命令入口、重导出字节一致、篡改/超限/覆盖拒绝、事件和噪声复现。原记录保存在 references/historical_verification.json；其中管理器结果仅为原件背景，不属于本包验证范围。源版本运行结果摘要见references/source_verification.json。

核心程序及配置与原工具保持一致，当前身份由sha256.json校验，源版本身份见 references/frozen_source.json。它是本包独立运行所需的工具快照，后续功能变更另立版本。工具文档和软件验证结果不能替代现场仪器验证。

## 失效条件

其他厂商BIN布局、超过支持点数、非整数周期、频点越过奈奎斯特、事件时间不在采样网格、事件重叠或越界、未知码值映射均不适用或会被拒绝。1秒记录重复率为1Hz，即使基波为50Hz。仪器回放频率和单次触发仍须现场确认。波形变体不自动形成独立数据来源。详细排查与经验来源见 references/cases.md。

## 可复用工作流

使用workflow.md的任务模板选择入口与整理结果，数值判定由脚本完成。

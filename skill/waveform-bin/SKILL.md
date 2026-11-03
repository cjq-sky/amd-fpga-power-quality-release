---
name: waveform-bin
description: 生成离线周期波形和暂态事件候选，使用既有编码配置导出或检查BIN，并核对源点与量化误差。用于AWG激励准备，不包含仪器控制、实板标签审核或模型训练。
---

使用随包冻结的 assets/pq_wavegen v0.2.1，Python 3.10+，仅标准库。先阅读 [README.md](README.md) 的命令与通过标准；参数细节见 assets/pq_wavegen/README.md。

执行前明确任务是新生成、已有源导出还是BIN检查。询问缺少且影响结果的采样率、时长、基波、谐波或事件参数；不得把本队50Hz示例作为其他项目要求。参数配置与输出放在新目录，保留原件。

BIN操作需要用户提供有实际依据的编码profile。缺少配置时先完成CSV生成并报告缺项，不自行编造硬件VERIFIED声明。软件测试夹具只能在明确的离线测试中使用。

执行后检查退出码和实际报告；有源文件时必须逐点对照。检查成功只报告软件范围，保留 hardware_verified=false、training_eligible=false。失效条件与排查见 [references/cases.md](references/cases.md)。给出输出路径、配置/源/BIN身份、关键检查结果及尚需现场确认的事项。

用户希望更改冻结实现或支持其他BIN布局时，另立工具版本，不覆盖本包v0.2.1副本。

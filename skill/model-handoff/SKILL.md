---
name: model-handoff
description: 整理训练数据准入与用途、模型输入合同、交付身份及跨环境黄金回放，复核真实调用和拒绝输入。用于模型交接与数值一致性，支持固定输入的成对性能计分，不认证独立数据资格或替代系统验收。
---

先读 [README.md](README.md)。按 [workflow.md](workflow.md) 分别处理准入、交付、离线回放和真实调用。引用既有文件审核与追溯结果；本包不依赖另一个技能包才能运行。

先确认用户的数据资格规则、模型合同和数值容差，缺失时记录待确认，不能沿用本队谐波门限作为通用规则。准入及用途模板见templates；设计标签、参考物理标签和预测分开保存。黄金来自TRAIN时只能用于一致性检查。

对照回放使用scripts/compare_replay.py及examples中的通用格式。交付源端和目标端都导出同格式结果，特征适配与模型执行仍由各项目实现；不得伪造目标端结果。核对实际输入、模型哈希、类别及概率，拒绝输入必须没有预测。容差从冻结合同读取，不为得到通过而调整。

examples/physical_portable_v11是本队已验证实例，固定六维与四类，不是通用推理器。保留原模型、黄金数据及对应身份；目录布局与摘要清单按当前版本登记；历史board_verified=false反映打包时点，后续状态由references中的证据说明，不改写旧manifest。

结合references/cases.md解释失败与限制，不将工程回放写成独立准确率，不将包装耗时写成ADC到UI时延。成对性能计分见 [references/paired-evaluation.md](references/paired-evaluation.md) 与 scripts/score_paired.py。资格与批准标签先于计分；两模型缺失/拒绝/错误输出保留共同分母。已有明确授权不重复设签核关卡。

历史阶段与v1.1能力存在疑问时，先读[版本范围](references/version_scope.md)，不从旧阶段待办推断现用系统功能未完成。

# 训练准入与模型交接校验技能包

扩展版1.1，2026-11-02。Python 3.10+，提供标准库比对脚本、用途与合同模板、工作流和已验证实例。

## 适用范围

用于数据训练前的资格与用途记录、模型交付身份确认、源端/目标端数值一致性比较，以及真实调用记录复核。输入为已有审核证据、批准的准入规则、训练清单、模型及合同、黄金输出和目标环境结果。数据格式与模型不限于谐波任务；自动比对仅支持本包约定的JSON交换格式。

## 快速使用

从本目录运行通用示例：

```powershell
python scripts/compare_replay.py --contract examples/contract.json --expected examples/expected.json --actual examples/actual.json --output replay_001.json
```

示例为软件构造，预期PASS；换成examples/bad_actual.json应FAIL、退出2。源端和目标端需各自执行真实模型再转换为该交换格式，不能复制黄金输出冒充目标结果。

合同字段：feature_order为有序特征名；labels为按概率列顺序排列的标签；model_sha256为待比较的实际权重身份；probability_tolerance为预先冻结的绝对容差。结果文件含相同feature_order、labels、model_sha256及rows；每行含id、input、status、label、probabilities。ACCEPTED行要求有限数值输入、合法标签和完整概率向量；REJECTED行label与probabilities必须显式null。两侧同一id、相同实际输入才比较，输入值不设宽松容差。脚本不验证上游拒绝理由或替你执行模型。

已有模型案例可独立运行：

```powershell
python -S examples/physical_portable_v11/verify_board.py --output physical_replay_001.json
```

该实例固定六维、两算法、2496黄金行。原模型和黄金数据保持不变；实例运行不依赖历史工作区。它不是新项目的通用模型模板；新项目应实现自己的模型加载与输入适配，再使用通用比对格式。

## 数据准入与真实调用

按workflow.md执行。templates/admission.csv记录参考标签、资格、排除理由、谱系与用途；templates/contract.json记录特征单位/类型/预处理、模型身份和标签顺序；templates/live_review.csv记录实际帧、原Adapter状态、模型结果和耗时范围。模板的待填值不构成审核通过，不自动划分数据、不自动授予训练资格。

## 通过标准

文件身份与合同匹配；比对集合无缺行/重复行；两侧输入及接受/拒绝状态一致；接受行类别完全一致，概率差不超过冻结容差；拒绝行无预测。报告退出0为PASS，2为FAIL或执行错误。输出不得覆盖原件。准入判断还需真实参考和批准规则，软件比对通过不替代资格审核。

## 已验证效果

历史证据：LR/RF标准库导出与原模型2496行黄金一致；Python3.10.4 ARMv7两模型各2496行类别差异0、概率差小于1e-6；四工况8轮256有效帧经保存输入重放一致，4个真实启动隔离拒绝保留空预测。见references/cases.md与随包历史证据摘要。

源版本的通用比对测试及冻结案例回放结果见references/source_verification.json。原记录在电脑执行；文件检查不执行回放。尚未进行陌生队伍试用。

## 失效条件

模型版本、特征顺序/单位/预处理不一致，应先修正适配，不能放宽容差掩盖差异。浮点运算次序与目标精度变化需保留黄金复核。未知输入资格、未知标签依据、域外工作点须单独标记。包内新增已验证的12工况保存结果计分案例；不认证来源独立性、跨设备泛化、实时指标或最终系统验收。


## v1.1：成对评分扩展

使用方法、交换格式、指标分母与失效条件见[paired-evaluation.md](references/paired-evaluation.md)。脚本scripts/score_paired.py和examples/ev26/可独立运行；不执行模型、不操作硬件。EV26真实案例LR321/384、RF292/384，保留交叉优劣和全部失败分母。原v1.1新增6项自动测试与真实结果交叉验证记录见references/source_paired_verification.json；该历史记录还包含8项黄金比对测试。原模型和数值数据保持不变，各结果仅适用于原运行条件，文件检查不重新运行测试。

v1.0历史ZIP保留；本版增加评分，不重写历史board_verified或原权重。通用计分格式不限定CH1六维或四类，EV26示例是项目案例，不能直接充当新题目的参考标签。

## 历史与当前范围

[版本范围](references/version_scope.md)区分早期正弦、四工况、v1.1 EV26评估与现用125MHz系统。v1.1已包含12工况保存结果计分；早期记录中的HDMI/四工况待办不代表现用系统功能缺失。验证摘要沿用原日期，文件检查不执行回放或板测。

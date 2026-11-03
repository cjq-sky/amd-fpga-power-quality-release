# 同输入成对评估：使用方法与失效条件

先取得用户实际要求的资格/标签依据和用途授权，再执行模型；已批准的同批参考不重复审核或索要第二次签核。将批准的输入集和标签固定后，两模型各自产生输出。scripts/score_paired.py仅计分，不加载模型、不生成标签、不决定算法，也不会判断授权真伪。

## JSON交换格式

cohort顶层labels为类别顺序、feature_order为特征顺序、rows为唯一id列表。每行含id/run_id/input/source_label/eligible=true。只放已经完成资格决定的输入，未资格记录在外部总账保留，不能依据预测决定是否进cohort。

模型文件顶层labels/feature_order与cohort一致，model_sha256记录各自实际权重身份，rows含id/input/status/label/probabilities。ACCEPTED为合法类别与归一化有限概率；REJECTED或ERROR显式null标签和概率。两模型哈希可以不同。实际执行模型和核对预期权重身份由调用方完成，计分器不认证模型。

缺失某个输出、拒绝、运行异常均保留该输入的服务分母，列为ABSTAIN_OR_ERROR（不是增加分类标签）；多余id、重复id、输入不一致、未知标签或无效概率拒绝计分。不能取“两模型都成功”的交集作为分母。

## 可执行命令

从技能包目录运行；输出文件应是新路径：

```text
python scripts/score_paired.py --cohort examples/ev26/cohort.json --left examples/ev26/lr.json --right examples/ev26/rf.json --output paired_report_001.json
```

此例是真实已评分EV26结果的最小交换副本，不是通用的无污染测试数据。预期384条共同输入、LR321条正确、RF292条正确。脚本只读取已保存结果，不新增推理或板端实验。

## 指标含义

service_accuracy、service_recall包括全部已批准输入和模型失败；conditional_accuracy/conditional_recall/conditional_f1仅针对有效四类输出，须和失败数一起看。Run等权平均降低不同帧数权重差异，但不把同一Run帧变独立实验。缺类或没有该类有效输出时完整macro-F1为null；未预测某类时precision为null。混淆矩阵行真值、列预测，另给含失败列的操作矩阵。类别正确数/该类输入数是Recall，不混用含真负例的one-vs-rest Accuracy。

计分SCORED只代表计算完成，不是工程验收PASS或数据独立性证明。来源/谱系重叠需另行披露，结果用于选模、调参或重训后按验证/开发历史登记。训练回代、黄金回放、已知工程调用、新参数工况评估和外部来源测试不可互换。

## 从实际失败提炼的经验

EV26四类各96输入：LR83.59%、RF76.04%，但RF的H5为96/96而LR83/96。一个总体分数不能证明全面占优。当前LR由用户授权按本批表现及既有工程开销推荐，保留RF对照和全部错误。63条LR错误与92条RF错误不删；模型稳定输出不等于分类正确。数据/权重/模型调用稳定性与长期系统运行稳定性分别报告。

验证覆盖标准库计分器的共同分母、缺失输出、拒绝/异常、错输入、重复id、未资格标签和旧预测残留；真实交换副本与项目既有评分及sklearn交叉验证结果一致。陌生队伍/跨板卡试用尚未完成；新任务须自备模型执行适配与已批准参考标签。

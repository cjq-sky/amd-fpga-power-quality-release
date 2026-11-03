# 实板数据审核与追溯技能包

版本1.0，2026-11-02。整理已完成的数据完整性与身份追溯经验，独立于数据管理器后续集成、标签门限、训练及板端模型验收。

## 适用范围与输入

适用于具有源文件、采集Run、Raw/Feature和独立参考的实验交付。输入为原件、源清单、采集清单、重采记录与现场声明。Python 3.10+，脚本仅用标准库。支持的自动检查格式为capture-registration-0.1；其他格式使用本包表格与人工流程，不承诺自动解析所有板卡格式。

## 使用方法

从本技能包目录运行正常示例及故障示例，报告必须在Run外且尚不存在：

```powershell
python scripts/check_capture.py --run examples/good --report good_report.json
python scripts/check_capture.py --run examples/mismatch --report mismatch_report.json
```

GOOD预期退出0、STRUCTURALLY_COMPLETE；MISMATCH预期退出1并包含SOURCE_MISMATCH。两个示例全部是人工构造的软件夹具，哈希字段和现场信息均不构成真实实验依据。报告路径错误退出2。

真实使用：先按templates/inventory.csv登记源、Run、参考及文件哈希；按templates/selection.csv记录重采选定和隔离；按templates/confirmation.json记录已存在的现场声明。对于兼容目录，可将命令中的--run换成其路径，报告另存。字段范例见examples/good，文件限定在raw/、feature/、reference/子目录。

脚本检查字段、源快照一致性、文件存在/非空/哈希、路径限制和声明的关联状态，不解析Raw/Feature数值、不核验外部源清单内容、不校准仪器，也不自动处理跨Run替换。后几项须按workflow.md执行并保留依据。源码副本来源见references/provenance.json。

## 输出和通过标准

输出分为三类：自动完整性报告；人工确认的源—Run—参考映射及替换清单；未知事项清单。自动检查通过只代表登记结构完整。只有外部源身份、参考对应和选定依据均有证据时，才能称该条追溯关系已核对；缺证据记PENDING，不用软件通过替代人工结论。measurement_validity=NOT_ASSESSED、formal_training_eligible=false保持原意。

## 已验证效果

原检查器的6项测试覆盖结构通过、篡改、缺件、路径越界、未关联与非法JSON。源版本独立运行结果摘要见references/source_verification.json；包含两个可运行样例。历史项目已完成80条源/Run/参考身份交叉核对，重采采用3/24/44/46号_002、44号参考44_repeat0，并保留旧尝试隔离。证据摘要见references/cases.md。这些历史结果不代表本包能一键重新完成80条数值审核。

## 失效条件与边界

哈希正确仍可能对应错误实验；元数据和源快照同时填错也可能通过结构检查。关联状态仅是声明，非硬件认证。批量现场声明应保存覆盖范围和解释边界，未知时序不得补造。跨板卡、采集格式解析、物理标签、计量有效性及训练放行不在本包自动检查范围。

scripts/register.py仅保留用于原测试依赖，含项目CH1与ADC默认值，不作为陌生队伍的通用注册入口。不要未经核对沿用这些默认值。正式使用以本包清单模板和真实记录为准。

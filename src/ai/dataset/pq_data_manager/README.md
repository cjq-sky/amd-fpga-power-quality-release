# 离线数据管理器v0.2.1

用于数据登记、导入、归档、审核、冻结与导出，保留原判定和固定依赖。基本工具使用标准库；H13 NPZ导入需要NumPy，可选依赖见requirements_optional_h13.txt。输出目录放在工程外，不覆盖板端环境。

```sh
python -B src/ai/dataset/pq_data_manager/manager.py --help
python -B src/ai/dataset/pq_data_manager/manager.py import-run --help
python -B src/ai/dataset/pq_data_manager/manager.py review --help
python -B src/ai/dataset/pq_data_manager/manager.py export --help
```

register、check_capture、summarize_runs、catalog用于登记及结构核对；import_h12、import_h13是特定历史格式入口。pipeline.py prepare可调用同级pq_wavegen，不自动访问发生器或板卡。输入/证据路径由参数明确指定，优先显式给出工程外data-root。

v0.2.1通用readiness规则与limited_scope_label_policy_v1.0的限定边界不同，不能用旧通用review替代冻结训练批次或EV26标签审核。结构完整不等于标签获准，标签不能由模型预测推断。

本v0.2.1版本中的import-run及vendor/prepare_features_v05.py独立日志入口按旧Lab07 BIT/HWH身份读取历史数据；原身份检查和预期哈希保留。现用125MHz在线链路采用ui14_service中的实时适配器，已绑定最新配套固件并已有模型/HDMI接入验证，不调用这里的历史归档导入入口。因此，本工具的历史格式边界不构成整机兼容性待验项；需要整理新格式归档时，应对照实际使用的工具版本和输入协议。运行源码及固定依赖保持原字节。

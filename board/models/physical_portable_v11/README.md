# 板端模型运行文件

本目录四个运行文件与src/ai中的冻结原件逐字节相同：portable_model.py、deployment_manifest.json、logistic_regression.json、random_forest.json。LR为当前工程候选，RF保留。仅需Python标准库，原模型资格保持TRAINING_ONLY。

最新125MHz实时服务的既有固定查找目录为：

```text
/home/xilinx/jupyter_notebooks/lab07_bai_integration/physical_portable_v11_ge8e6qs4
```

在没有活动采集/显示进程时，将四个运行文件部署到该位置；已有目录应先核对身份，不覆盖未知或正在运行的文件。README不需要部署。只把模型保存在源码目录不能自动满足服务固定路径，不修改服务哈希白名单绕过。

从工程根目录运行python -B build/scripts/check_ai.py核对源文件、模型和本目录副本。现用125MHz板端模型与HDMI接入已有验证；本检查只确认本地模型文件身份。本地根run.py已转调现用实时服务，四文件及服务核心逻辑保持原件。文件检查不执行推理、重训或板测。

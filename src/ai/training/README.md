# 模型训练与冻结权重导出

环境：Python3.12.7，固定依赖见requirements.txt。使用电脑端虚拟环境，不安装到板端PYNQ环境。

## 从批准的Manifest训练

从工程根目录执行，DATA_ROOT替换为外部实际数据目录：

```sh
python -B src/ai/training/train_from_manifest.py --manifest DATA_ROOT/released_training_manifest.json --output DATA_ROOT/new_training_run
```

默认核对冻结2496帧Manifest哈希，并检查TRAIN、training_eligible、CH1六维合同及四类覆盖。哈希只能证明身份，不能代替标签批准。其他批准清单需显式指定--expected-manifest-sha256。

训练保持原参数：float32输入、谱系等权；LR标准化器与分类器均加权，max_iter3000、seed20261102；RF160树、depth12、minleaf2、seed20261102、n_jobs1。输出必须为新目录，新权重不覆盖冻结模型，也不保证新joblib逐字节等同原件。文件检查不执行训练。

## 精确导出冻结原权重

```sh
python -B src/ai/training/export_frozen_portable.py --models-dir src/ai/models/original_training --deployment-template src/ai/models/physical_portable_v11/deployment_manifest.json --output DATA_ROOT/new_portable_export
```

只加载来源可信且冻结哈希匹配的joblib；输出JSON需匹配原portable1.1哈希，Windows CRLF编码保留。该入口专用于已有冻结版本，不是任意新模型的通用发布器。新训练模型需要自己的版本、部署清单及数值验证，不能复用旧身份。

原训练数据和黄金输出不在源码目录中，缺少这些输入时训练复现保持未完成。源码和权重存在不等于已复现训练过程。

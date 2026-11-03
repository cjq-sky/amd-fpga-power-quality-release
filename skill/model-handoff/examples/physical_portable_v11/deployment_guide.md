# 标准库模型案例使用说明

实例版本physical-portable-1.1，模型limited-scope-physical-v1-20261102。两份JSON、portable_model.py、golden.json与deployment_manifest均保持冻结原字节。此案例用来演示模型交付数值一致性，功能和实际用途见[版本范围](../../references/version_scope.md)。

## 运行前提

Python3.10+，标准库推理不要求NumPy、scikit-learn或joblib。verify_board.py是离线回放程序，不连接Reader或显示设备，也不会加载固件。需要自行回放时在本目录执行，输出须是新文件：

```sh
python -S verify_board.py --output portable_replay_001.json
```

既有回放结果见export_verification.json和offline_verification.json；两者为原版本结果摘要，运行命令须另行记录实际输出。

LR保留输入float32及分步缩放舍入，RF保留160棵树和阈值分支。输入为CH1六维，前五项百分数、Crest为比值；标签0 CLEAN、1 H3_DOMINANT、2 H5_DOMINANT、3 MIXED。预测不回写物理标签，LR不再二次标准化。

验证器先读取sha256.json、核对黄金数据及模型身份，随后比较2496行类别及固定1e-6概率容差。原TRAIN黄金不是独立测试集；模型包装耗时不是ADC到UI端到端时延。

本例不依赖历史工作区的导出脚本。工程中冻结权重的可移植导出入口位于src/ai/training/export_frozen_portable.py，训练环境依赖由该模块说明。本例本身可以独立完成现有模型黄金回放，不承诺替其他模型生成黄金结果。

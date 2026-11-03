# 电能质量智能辨识

本模块包含波形生成、离线数据管理、特征合同、LR/RF训练、冻结模型、标准库推理和保存结果计分。所有命令从工程根目录运行，路径使用src/ai。DATA_ROOT表示工程目录外的实际受控数据目录，执行前替换为真实路径；输出选择尚不存在的新位置。

|目录|内容|
|---|---|
|dataset/pq_wavegen|v0.2.1波形生成及BIN编解码|
|dataset/pq_data_manager|v0.2.1数据登记、导入、审核、冻结及导出|
|dataset/policies|限定工况标签规则|
|preprocessing|CH1六维特征顺序、单位、类别及无效输入处理合同|
|training|固定参数训练及冻结权重精确导出入口|
|models|原joblib与板端JSON，LR工程候选及RF对照|
|inference|标准库推理与保存输入入口|
|evaluation|保存输出成对计分|

## 环境和文件检查

离线工具及板端JSON推理使用Python3.10+；原训练环境为Python3.12.7、NumPy1.26.4、scikit-learn1.5.1、joblib1.4.2，依赖见training/requirements.txt。训练依赖只安装到电脑端独立虚拟环境，不覆盖板端PYNQ环境。H13导入另有可选NumPy依赖。

```sh
python -B build/scripts/check_ai.py
python -B src/ai/dataset/pq_wavegen/wavegen.py --help
python -B src/ai/dataset/pq_data_manager/manager.py --help
python -B src/ai/inference/predict_saved.py --help
python -B src/ai/evaluation/score_paired.py --help
```

check_ai只核对文件、语法、模型身份和特征合同，不训练、不执行推理、不操作硬件。模块校验清单为sha256sums；根SHA256SUMS核对整个工程文件集合。原始训练数据、黄金输出、历史日志和完整测试程序不在源码目录内。

## 板端部署

board/models/physical_portable_v11提供同字节的四文件部署集合。运行合同和安装位置见该目录README.md。复制模型文件不会改变实时服务；服务必须由原有单Reader提供已审核的六维输入，不能由模型另建Reader。现用125MHz系统已有板端模型调用与HDMI显示验证，实时输入由该版本ui14_service适配器提供。根run.py已转调现用125MHz实时程序，在线适配、单Reader和模型调用保持原件；文件检查不执行推理或板测。

## 适用范围

输入仅CH1：H3/H5/H7/H9百分比、奇次THD百分比与Crest；原模型状态保持TRAINING_ONLY。LR为当前工程候选，RF保留对照；不承诺正式泛化精度。原部署manifest的board_verified=false是导出时元数据，不代表当前整机验收状态。

数据管理器所保留的v0.2.1历史日志导入入口按旧Lab07固件身份检查，仅用于其对应历史数据格式；它不参与现用125MHz在线模型与HDMI链路。现用实时适配器已绑定125MHz配套固件，不能把历史导入接口的版本限制列为整机不兼容。后续使用离线导入工具时应选择与实际数据版本对应的入口，不改身份检查绕过。缺少原训练Manifest及批准数据时，可以使用已交付模型和工具，不能声明已复现原训练。各模块README明确命令、输入格式及限制。

代码和模型沿用原有版权边界，第三方依赖从各自渠道取得，不代选开源许可证。

# 冻结模型推理

portable_model.py保持physical-portable-1.1原件；权重在../models/physical_portable_v11。Python3.10+标准库实现，含float32转换及LR缩放/RF树遍历，不再二次标准化。

predict_saved.py只读保存的Adapter对象，不访问Reader。输入为非空JSON数组，每行含唯一id和checked；checked包含input_status、schema_id、feature_config_version、frame_identity及features，按../preprocessing/feature_contract.json提供。

```sh
python -B src/ai/inference/predict_saved.py --model-dir src/ai/models/physical_portable_v11 --algorithm logistic_regression --input DATA_ROOT/approved_saved_inputs.json --output DATA_ROOT/new_lr_outputs.json
```

DATA_ROOT替换为外部目录。RF使用--algorithm random_forest及相同输入。输出路径必须未存在，拒绝/错误保留空预测和原因。离线CLI不能重新判断保存数据此刻的实时新鲜度。

在线服务由唯一Reader提供已审核输入，调用PortableModel(...).predict_checked(checked)。模型不接管采集、显示或会话。板端四文件部署集合在board/models/physical_portable_v11；路径以工程根目录为基准。现用125MHz板端版本已完成模型调用与HDMI接入，并有对应既有验证记录。本地根run.py已转调这一现用版本；核心运行文件保持原件，文件检查只核对身份与静态合同。

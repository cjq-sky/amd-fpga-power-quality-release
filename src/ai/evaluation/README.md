# 保存结果成对计分

score_paired.py对保存结果计算指标，不执行模型、不生成参考标签。

```sh
python -B src/ai/evaluation/score_paired.py --cohort DATA_ROOT/released_cohort.json --left DATA_ROOT/lr_results.json --right DATA_ROOT/rf_results.json --output DATA_ROOT/new_paired_metrics.json
```

cohort顶层feature_order、labels及rows；每行含id、run_id、input、source_label、eligible=true。两模型结果包含相同feature_order/labels、各自model_sha256和对应rows；每行含id、input、status、label、probabilities。ACCEPTED输出合法标签及概率，REJECTED/ERROR保留空标签与概率。

全部批准输入使用共同分母，缺失、拒绝及错误计入ABSTAIN_OR_ERROR；不能只取两算法成功交集。service_accuracy与仅合法输出的conditional指标需同时披露，Run等权指标不代表连续帧相互独立。

predict_saved.py与本工具使用的交换格式不同，当前没有自动转换入口，不能直接串接。已有数据需按上述实际协议组织，不通过编造输出凑接口。SCORED只表示已计分，不等于验收PASS。

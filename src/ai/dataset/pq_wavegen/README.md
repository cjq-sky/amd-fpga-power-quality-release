# 波形生成器v0.2.1

Python3.10+标准库工具，保留wavegen.py、events.py和bin_codec.py。配置描述生成参数，不是实际采样或训练数据。

从工程根目录执行，DATA_ROOT替换为工程外实际目录，输出不得已存在：

```sh
python -B src/ai/dataset/pq_wavegen/wavegen.py --config DATA_ROOT/user_waveform_config.json --output DATA_ROOT/new_sources
```

配置顶层需要split_role、sample_rate_hz、duration_s、fundamental_hz和cases；各case有唯一id及对应谐波/事件参数。现有目录不含可直接运行的完整示例配置，参数细节需结合源码和--help核对。

--bin-profile需要适合实际仪器的编码配置；没有合法、匹配的profile时只生成候选波形，不生成仪器BIN。--export-source、--check-bin、--compare-source的参数见--help。

ratio是比例，0.05表示5%；基波频率不同于整段记录重复率。码值越界会拒绝，不自动归一化或削顶。生成物标记calibration_dev、source_label空，不自动取得物理参考或训练资格。程序不会操作仪器或板卡。

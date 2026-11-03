# 十组验证输入波形

本目录提供十个AWG任意波形BIN，用于双通道、幅值事件及CH1谐波分类的输入配置。BIN字节保持提供版本原样，包内文件名统一为英文小写；[配置表](waveform_catalog.csv)保留原文件名对应、幅度、点数和SHA256。这里存放验证输入，不将其标为板端实测输出或新参考比对结果。

## 通用AWG配置

- 输出负载High-Z，Offset=0V。
- 每个文件10000点、记录长度1秒，整段重复率设置1Hz，段内正弦基波50Hz。不要把整段重复率设成50Hz。
- 切换文件时分别核对两路面板幅度：HIGH使用1.25Vpp，SWELL使用1.50Vpp，其余为1.00Vpp。
- 文件格式保留48字节头及10000个16位小端无符号码值，中心10000、比例4500；每个文件20048字节。不要自动归一化、削顶或改写头部。
- 导入适配此既有BIN格式的AWG，从文件导入并按下表设置；仪器确切型号和操作按实际设备，不猜测通用按键步骤。

## 文件与面板幅度

|包内文件|波形内容|AWG面板Vpp|BIN补偿后名义Vpp|
|---|---|---:|---|
|[demo_sine_low.bin](waveforms/demo_sine_low.bin)|低幅正弦|1.00|0.660000|
|[demo_sine_base.bin](waveforms/demo_sine_base.bin)|基准正弦|1.00|1.060000|
|[demo_sine_high.bin](waveforms/demo_sine_high.bin)|高幅正弦|1.25|1.260000|
|[demo_ev_sag20.bin](waveforms/demo_ev_sag20.bin)|暂降后恢复|1.00|1.06 -> 0.26 -> 1.06|
|[demo_ev_swell150.bin](waveforms/demo_ev_swell150.bin)|暂升后恢复|1.50|1.06 -> 1.56 -> 1.06|
|[demo_ev_interrupt.bin](waveforms/demo_ev_interrupt.bin)|低幅残余段后恢复|1.00|1.06 -> 0.06 -> 1.06|
|[tr_clean_00.bin](waveforms/tr_clean_00.bin)|纯正弦|1.00|0.710000|
|[tr_h3_r00_v0.bin](waveforms/tr_h3_r00_v0.bin)|三次谐波2%|1.00|0.698174|
|[tr_h5_r00_v0.bin](waveforms/tr_h5_r00_v0.bin)|五次谐波2%|1.00|0.721132|
|[tr_mix_00_v0.bin](waveforms/tr_mix_00_v0.bin)|三次、五次谐波各3%|1.00|0.708205|

## 幅值补偿的含义

这批文件保留配套说明中的v1.4设置：在原幅值设计上增加0.06Vpp交流峰峰值补偿，Offset仍为0。面板幅度与文件内波形缩放共同决定输出，表中“BIN补偿后名义Vpp”不等于示波器实测或已校准值。

例如BASE的文件名义设定为1.06Vpp，面板仍用1.00Vpp；仅当实际链路具有所针对的0.06Vpp幅值偏差时，才可能回到原基准。SAG/SWELL分别补偿前后基线与事件平台；INTERRUPT保留0.06Vpp残余正弦，不是完全静音。实际是否进入事件门限由现用基准和真实输入决定，不改事件阈值迁就文件。

四个TR文件按整体幅值补偿，保留相应谐波比例；H3/H5百分比描述输入构成，不是模型输出或独立准确率保证。这些文件属于已有来源的幅值变体，不自动成为新独立测试集。CLEAN表示谐波形态，不等于事件必须为NORMAL。

## 输入组合

|用途|CH1|CH2|配置要点|
|---|---|---|---|
|双路独立性|BASE→HIGH→BASE→BASE|LOW→LOW→LOW→HIGH|每步只改变一路，按各自文件设置面板幅度|
|谐波及通道对应|TR_CLEAN_00|TR_MIX_00_V0|两路1.00Vpp；需交换接线时按硬件接线规范操作|
|幅值事件|BASE→SAG20→SWELL150→INTERRUPT|LOW|SWELL切为1.50Vpp，其他CH1文件恢复1.00Vpp|
|CH1谐波分类|四个TR文件依次输入|LOW|两路1.00Vpp；可在CH1保持MIX时仅改变CH2输入观察通道隔离|

上表使用文件名的简写，完整名称见配置表。它描述输入操作，不代表实测PASS、帧数、分类准确率或板测结论。切换后按原程序的有效性/稳定规则观察，Raw/Feature关联状态如实保留。

## 内容边界

本目录仅收录实际提供的十组输入及使用说明，不创建未提供的实测/参考结果、空参考目录或个人文件位置索引。板卡和信号接线见[硬件说明](../docs/reproducibility/hardware_setup.md)，现用程序启动见[运行指南](../docs/reproducibility/run_guide.md)。文件长度、点数、编码范围和哈希检查不代表重新验证了AWG模拟输出。

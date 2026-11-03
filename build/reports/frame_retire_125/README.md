# 125 MHz联合工程最终报告

选入2026-11-02既有实现的8份必要报告。这些是既有结果，文件检查不重新运行综合、实现或板测。这些结果对应正式发布来源，不是便携脚本在新目录重新构建的结果。

|文件|用途|
|---|---|
|[utilization_synth.rpt](utilization_synth.rpt)|现用设计既有综合资源|
|[utilization_routed.rpt](utilization_routed.rpt)|最终Routed层次资源及各模块组成|
|[timing_startup.rpt](timing_startup.rpt)|最终startup时钟模型完整时序汇总及路径|
|[timing_operating.rpt](timing_operating.rpt)|同一最终实现的operating模型完整时序汇总及路径|
|[route_status.rpt](route_status.rpt)|32928条可布线网络全部布通、routing error为0|
|[cdc_startup.rpt](cdc_startup.rpt)|startup模型CDC结果与开放项，不将Critical改成PASS|
|[drc_startup.rpt](drc_startup.rpt)|startup模型DRC结果与警告|
|[bitstream_checks.rpt](bitstream_checks.rpt)|正式发布生成BIT前的专用ruledeck检查|

来源、SHA256、阶段及正式BIT/HWH/DCP绑定见[source_binding.json](source_binding.json)。为避免带入个人主机名及开发机路径，只替换Host头和Command头中的输出绝对路径；版权、日期、工具版本及其余报告正文逐字节保留。这里是明确标注的脱敏副本，原报告不改写、不删除。

## 指标口径

最终联合顶层utilization_routed表的Total LUTs=13731、FFs=21084、RAMB36=18、RAMB18=15、DSP48 Blocks=41；不要与历史Lab07单独核心、Lab05/Lab06优化表或Logic LUTs口径混为一组数据。

startup/operating最终WNS均+0.087ns、WHS均+0.019ns、TNS/THS为0。H16独立125MHz、FCLK0为100MHz、FCLK1为125MHz，不表示所有视频时钟都是125MHz。正时序裕量只适用于原已约束的内部模型；AD7606板级I/O签核仍OPEN，既有CDC Critical及DRC Warning按原报告保留。

技术报告继续保留架构、实物、实现图片与优化前后汇总，本目录不复制这些章节，也不整体搬入旧Lab05/Lab06/联合候选报告。最终报告表格应标明实际模块和阶段，不能把不同版本数字合成当前整机指标。

这是实现证据，不能代替模块仿真或现用PS/AI/HDMI整机实测。便携构建如何生成新报告见[构建指南](../../../docs/reproducibility/build_guide.md)，已有模块仿真记录见[sim](../../../sim/README.md)。

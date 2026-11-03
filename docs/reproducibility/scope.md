# 当前版本与适用范围

主模式为REALTIME_FRAME_RETIRE_125，日常入口为根目录run.py。系统包括同步采集、Feature/Raw、单Reader、双路事件、CH1模型、HDMI触摸四页和电脑共享显示。

运行源码版本为6fcc422f90f56e1b20854e18a28847564df03313。正式BIT/HWH、运行Python源码和模型保持原字节。CH2基准配置仅省略不参与计算和文件读取的历史目录字段，基准数值不变；59项payload由当前11_payload_sha256.json严格校验。board/application.json分别记录当前与原始payload清单身份，二者不能混用。

|正式固件|SHA256|
|---|---|
|BIT|45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4|
|HWH|54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f|

PL源码位于src/pl/frame_retire_125，构建脚本位于build/scripts；依赖与源码对应关系见[构建指南](build_guide.md)和[PL来源说明](pl_source_binding.md)。便携目录完整重建尚无执行结果，不能将既有实现报告登记为新构建结果。

AI的TRAINING_ONLY、导出时board_verified=false及历史UNMATCHED分别保留各自数据和验证范围，不代表现用系统尚未接入模型。离线数据管理器与现用在线适配器使用各自的输入合同。技能v1.1包含保存结果成对计分，不能代替独立泛化测试。

根SHA256SUMS检查整个工程文件集合；payload、部署、PL、AI及技能清单用于对应模块的独立身份检查。--check不导入PYNQ、不访问MMIO、不运行推理或构建；通过只能说明文件和静态合同一致。

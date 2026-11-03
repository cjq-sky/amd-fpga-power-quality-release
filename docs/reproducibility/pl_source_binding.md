# 125 MHz PL源码来源与固件对应

设计候选为FINAL_FRAME_RETIRE_FCLK1_125_EVAL_1，正式发布为FINAL_FRAME_RETIRE_FCLK1_125_RELEASE_1。src/pl/frame_retire_125来自已定位的实际构建输入；原始工程、生成项目、检查点及历史报告保留原处，不作为新目录的构建输入。

|现用身份|SHA256|
|---|---|
|正式BIT|45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4|
|正式HWH|54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f|
|既有routed DCP|51034a1528d12ee76214c58f53b33089fb280d0da81908ca9221e15c4ea22df0|
|原BD|106ebdc243eae39d1ae5dfb83b98b6193d39f6f4b31edcf3b86eb235023dd5fc|
|原raw HWH|858a9f807b7a1af973db03f08d0aa65601df155e59724bfa66d6862cf5c72670|

正式BIT/HWH位于board/runtime/frame_retire_125，PL source_identity.json、来源清单及离线检查与它们交叉核对。DCP只记录身份，不用已实现检查点代替可维护源码；新构建只读取源码及合法工具依赖。

## 源码输入与便携设置

原Route编译列表含工具生成源，构建时由合法工具重新生成。原来源清单72项中67项按字节保留、5项为已登记便携派生；27份Lab07直接设计源、7份候选RTL、IP封装、XDC、PS7配置、FFT XCI和同字节Hann ROM均包含在内。

便携派生仅涉及同字节ROM路径、Python解释器、诊断输出位置、独立目录守卫及HWH发布路径。Frame Retire状态机、队列64、Deadline125000000、握手/ACK/epoch、时钟和时序例外不改变。构建支持脚本使用工程相对路径；工程身份元数据绑定正式pair及源码输入。

## 外部依赖

PYNQ固定commit d9c752164644ebdbf7f96e4cd7d96661d1276a34，共25项依赖，只保存白名单/哈希。VDMA只保存团队增量配方：合法Vivado2018.2原文件SHA256 a180b97756081106fc48be6531d78d044268ab9e3cb34dcc556e3f8e9ce3745a，还原结果必须为1d8c313b9a9e2dae981230ffbf033ef4fa7d2f30252827652d1bedb478722c08。官方专有实现和工具生成RTL不随源码分发。工具许可和各源文件自身通知继续适用，见[依赖与版权](../compliance/third_party.md)。

## 核对与执行边界

离线哈希、路径、来源、语法和元数据对应检查不等于重新实现。既有离线prepare-only与HWH转换检查分别确认过VDMA还原和发布HWH逐字节一致；这不产生新BIT，也不启动硬件。完整构建状态以实际构建输出为准。

原Route记录startup/operating的WNS+0.087ns、WHS+0.019ns、TNS/THS0、32928/32928网络布通属于既有实现，不能当作便携目录的新构建结果。AD7606板级I/O签核OPEN、CDC-1 Critical×4、CDC-4 Critical×1及DRC52 Warning按原范围保留，不由文件整理消除。

便携目录尚无完整HLS、综合、实现或板测执行结果。新构建若执行，输出rebuilt前缀并形成新身份，未经独立审核不得替换正式pair或改PS白名单。已完成的整机联调与这些新增构建包装器的执行状态分开记录。

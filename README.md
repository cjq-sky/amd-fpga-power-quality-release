# 电能质量感知与智能辨识

面向谐波畸变、电压暂升暂降、短时中断及非线性负载的FPGA软硬件协同终端，用于2026全国大学生嵌入式芯片与系统设计竞赛AMD FPGA自主创新赛道初级组。

当前主模式为REALTIME_FRAME_RETIRE_125：同步采集→FPGA特征与Raw缓冲→单Reader及双路事件检测→CH1轻量模型辨识→HDMI触摸四页与电脑浏览器共享显示。板端实时系统已完成既有联调；本目录统一使用该版本入口。模型及量值资格按原合同保留，详见运行模块说明。

## 平台

PYNQ-Z2、AD7606、七寸HDMI屏幕与USB触摸；系统镜像pynq_z2_v3.1.1。记录环境为Python3.10.4、PYNQ3.1.1、NumPy1.21.5、Pillow9.0.1。PL的FCLK0为100MHz，FCLK1为125MHz；原生库与内核指纹也须符合[环境要求](docs/reproducibility/environment.md)。

## 快速开始

电脑端在工程根目录执行：

```sh
python -B run.py --check
python -B run.py --plan
```

--check只核对文件、语法、合同及固定身份，不加载固件、不推理、不运行测试。--plan仅显示原程序的两段启动命令。文件检查通过不代替硬件验收。

将工程部署到板端新的英文目录，先满足固定模型路径、系统字体和192.168.2.99网络配置。已有合格系统直接进入[部署与启动](docs/reproducibility/run_guide.md)，不要求重新制作镜像。冷上电后，在合格PYNQ Python环境执行：

```sh
sudo python3 -B run.py --precheck
sudo python3 -B run.py
```

出现STAGE4_READY和ui4>后依次输入touch on、auto on、status。电脑浏览器访问http://192.168.2.99:8765。详细前提、预期输出与停止方式见运行说明；不要并行启动其他采集/显示入口。

## 目录与文档

|路径|用途|
|---|---|
|src/ai|数据工具、特征合同、训练、冻结模型、推理及评估|
|src/pl/frame_retire_125|现用125MHz设计对应的RTL、约束、IP配置与构建助手|
|board/runtime/frame_retire_125|现用实时程序、正式BIT/HWH及冻结身份清单|
|board/models/physical_portable_v11|板端四文件模型部署集合|
|board/application.json、board/precheck.py|当前应用环境合同与只读初筛|
|build、tools|现用PL构建入口、依赖配方、源码身份及全仓离线检查|
|skill|三项可复用技能及其必要资源|
|docs|环境、部署、硬件、构建、合规等说明|

- [从零复现指南：19章操作与判据](docs/reproducibility/reproduction_guide.md)
- [环境与依赖](docs/reproducibility/environment.md) · [部署运行](docs/reproducibility/run_guide.md) · [硬件接线](docs/reproducibility/hardware_setup.md)
- [构建说明](docs/reproducibility/build_guide.md) · [范围和版本](docs/reproducibility/scope.md) · [排障](docs/reproducibility/troubleshooting.md)
- [AI模块](src/ai/README.md) · [模型部署](board/models/physical_portable_v11/README.md) · [技能包](skill/README.md)
- [既有模块仿真结果](sim/README.md) · [最终综合与实现报告](build/reports/frame_retire_125/README.md)
- [十组验证输入与AWG设置](data/README.md)
- [测试与观察判据](docs/reproducibility/test_guide.md)
- [第三方合规](docs/compliance/third_party.md)

完整125MHz PL源码及便携构建脚本见构建说明。文件身份检查不代表已重新构建或通过板端验收；既有仿真与实现结果按各自版本和适用范围解读。运行配置与固件身份见[范围和版本](docs/reproducibility/scope.md)。


## 官方推荐目录对照

按AMD指南3.3.5.4给出实际目录对应；目录骨架为推荐结构，不创建没有材料的空目录。

|推荐位置|当前实际组织|
|---|---|
|src/|PL在src/pl/frame_retire_125，AI在src/ai；PS完整源码保留于board/runtime/frame_retire_125以维持冻结相对导入和部署身份|
|sim/|六组既有模块仿真结果、原始标记节选及源码对应；不包含测试程序或整机仿真宣称|
|build/|构建脚本、依赖、清单与最终125MHz综合/实现报告已有|
|board/|固件、模型与运行程序已有；正式实测输出待筛选纳入|
|data/|十组实际提供的AWG验证输入、面板配置与幅值补偿说明；没有附加未提供的实测/参考结果|
|skill/|三项技能和必要说明/示例已纳入|
|report/|正式设计报告及图表待单独交付|
|docs/、tools/|额外集中复现/环境/接线/合规文档和全仓离线检查|

根`SHA256SUMS`用于核对文件完整性和版本一致性；固件、模型及模块清单还用于各自入口的身份检查。这些是复现所需的机器校验文件，不是功能验收结论。

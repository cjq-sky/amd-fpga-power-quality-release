# 125 MHz PL源码构建

## 环境

Python3.10+用于构建辅助工具；Vivado2018.2 SW2258646/IP2256618、Vivado HLS2018.2、Zynq-7000器件支持及xc7z020clg400-1。建议进入已安装工具的命令环境，使vivado、vivado_hls和XILINX_VIVADO可用。不同工具版本不能直接视为同等重建；指南建议版本与本项目2018.2基线的差异应在最终报告中说明。本包不安装全局依赖。

实际构建使用英文短路径。工程根目录采用英文路径；--output必须使用新的英文目录。下文.build示例应位于这样的构建位置，不覆盖原工程。

## 1. 检查源码包

在工程根目录：

```sh
python -B build/scripts/check_pl.py
```

PASS表示源码/依赖清单、原始72项来源、27份Lab07直接输入、自有IP引用、固件对应关系和Python3.10语法一致；vivado/hls/hardware仍为NOT_RUN。根python -B run.py --check也包含此检查。

## 2. 准备新构建目录和HLS

在工具命令环境：

```sh
python -B build/scripts/prepare_pl.py --output .build/pl_001
```

准备脚本将顶层Hann ROM路径绑定到新目录中的同哈希ROM；不依赖原开发机目录。脚本读取XILINX_VIVADO中的2018.2 VDMA，校验原始哈希，应用团队Frame Retire修改并精确核对原候选结果哈希。PYNQ依赖从固定commit获取，核对Git blob和项目SHA256；视频HLS从原C++生成，不带testbench。两个原HLS时钟约束7ns/10ns和原综合设置保持，7ns是HLS设计目标，不将其误改成PS7的8ns；实际FCLK1仍为125MHz。

非工具命令环境可显式指定工具安装位置与可执行文件：

```sh
python -B build/scripts/prepare_pl.py --output .build/pl_002 --vivado-home <vivado_2018_2目录> --vivado-hls <vivado_hls可执行文件>
```

尖括号参数需替换，不能原样执行。离线可额外用--vendor-source指向合法取得、与固定哈希匹配的candidate/ip/vendor目录；只读该目录。--vdma-source可显式指定相同版本官方原文件，不接受修改版冒充原件。

只准备文件、不调用工具时追加--prepare-only；此时HLS NOT_RUN，不能跳过标志强行构建。后续完整构建应换新目录重新prepare，不覆盖前一次输出。

## 3. 预览与构建

```sh
python -B build/scripts/build_pl.py --workspace .build/pl_001 --plan
python -B build/scripts/build_pl.py --workspace .build/pl_001
```

--plan只打印步骤。实际构建顺序：BD/IP生成与125MHz校验、命名reset端口补接、FFT生成、自有VDMA封装绑定、默认综合、默认opt/Place、一次默认phys_opt、一次默认Route、startup/operating两模型时序与DRC检查、BIT生成、HWH转换和接口核对。构建日志和资源/时序/CDC/DRC报告当场写入新目录，不拿旧报告冒充本次结果。任何阶段失败立即停止并保存输出；不放宽约束、不自动重试或更换策略。

本包装器保留设计输入、时钟/约束及原主要实现命令顺序；历史测试执行器、原报告解析和旧会话批准文件不作为新构建的伪造门槛。没有原始测试通过记录的新环境，不因此自动得到原完整验证结论。

## 4. 输出与验收边界

- .build/pl_001/output/checkpoints：本次新DCP；构建不读取历史DCP作替代输入。
- .build/pl_001/output/reports：本次资源、两模型时序、CDC、DRC、布线状态与HWH检查。
- .build/pl_001/output/artifacts：rebuilt_frame_retire_fclk1_125.bit/.hwh及新身份记录。

构建内部门槛：FCLK0/H16/FCLK1与startup Pixel/Serial时钟符合合同；两模型最差setup/hold非负；全部可布线网络完成，routing error为0；bitstream DRC无Error/Critical Warning；HWH的10公共寄存器窗口和reset隔离检查通过。CDC Critical、DRC Warning及外部未约束项必须如实保留，不等于全部板级签核。

新HWH通过发布版原有转换逻辑生成，写入本次新routed DCP哈希；不是从netlist直接提取，也不写旧DCP身份。不把未经转换的raw BD HWH拿去加载，不使用旧原厂VDMA驱动替代自有协议。

即使内部构建通过，新产物也保持NEW_BUILD_REQUIRES_REVIEW_NOT_APPROVED_FOR_BOARD。不得覆盖正式BIT/HWH或修改PS预期哈希强行加载。完整流程在此便携目录中尚未实跑，首次构建若失败应按实际错误修复独立包装器并重新限定验证范围。


## 工程内位置

|路径|内容|
|---|---|
|src/pl/frame_retire_125|设计源码、约束、IP配置、FFT XCI/ROM及原相对路径构建助手|
|build/scripts/prepare_pl.py|核对外部依赖，创建新工作目录，按参数生成HLS|
|build/scripts/build_pl.py|预览或执行新工作目录的构建，不覆盖正式固件|
|build/scripts/check_pl.py|仅离线核对，不运行设计或工具|
|build/dependencies/frame_retire_125|PYNQ固定白名单及VDMA增量配方|
|build/manifests/frame_retire_125_sources.json|72项源码身份、便携派生说明和构建支持文件|
|build/manifests/frame_retire_125_sha256sums|PL模块文件清单|

src内部的build_unified2.tcl和旧层次信号名属于已验证设计的内部名称，实际PS7配置为125MHz；保留名称不表示仍使用旧固件。不要为目录整齐改模块名、reset连接或时序约束。sim/内若由IP元数据引用，则是设计副本，不能当成独立testbench删除。

来源及现用pair对应关系见[PL来源说明](pl_source_binding.md)。便携目录完整重建尚无执行结果；--prepare-only也不能当作HLS或实现通过。出现任何未知错误停止并保留输出，不删除已有结果重试。


## 既有最终实现报告

正式125MHz设计的8份既有综合/实现/发布检查报告位于[build/reports](../../build/reports/frame_retire_125/README.md)。它们用于原发布来源追溯，不是上述便携脚本的新构建结果。新执行产生的报告仍写入新工作目录output/reports，必须与既有报告分开。

# 从零复现指南

本手册对应REALTIME_FRAME_RETIRE_125：PYNQ-Z2、AD7606双通道采集、PL特征与Raw缓冲、唯一Reader、双路事件、CH1模型、独立HDMI触摸四页及电脑浏览器共享显示。现用整机已完成既有联调；文件检查和实际构建、上板验收分别判定。

先取得含根SHA256SUMS的完整同版本目录；不要把其他提交的固件、软件或模型拼进来。以下命令均从工程根目录执行。电脑示例使用python，板端使用合格环境的python3。DATA_ROOT是工程目录外、需自行替换的实际数据位置；new_*输出必须是尚不存在的新位置。TODO表示材料或操作信息未补齐，NOT_RUN表示相应命令没有执行该操作，均不能当作PASS。

## 1. 选择复现路线

已有合格板端系统：第2、4、6、7、10章准备→第11章部署→第12章启动→第13至18章观察与运行。此路线使用正式发布固件，不要求先安装Vivado、重做镜像或重训模型。

需要从源码重建：完成第2、3、5、8、9章；新产物先独立审核身份、资源、时序与接口，再决定上板，不直接替换正式pair。便携构建脚本已交付，便携目录完整重建尚无执行结果。

预期：明确选择正式发布物部署或新源码构建，分别记录结果。通过条件：不混用两条路线的固件和验收结论。

## 2. 电脑环境与目录完整性

Windows或Linux，Python3.10+用于文件检查；浏览器用于电脑显示。将完整目录保存在英文路径。无需为检查安装PYNQ、NumPy、Pillow或训练依赖。

```sh
python --version
python -B run.py --check
python -B run.py --plan
```

预期：检查输出global_file_identity、file_coverage、python310_syntax，以及runtime、AI、skill、PL各模块身份均PASS；hardware、inference、fpga_build为NOT_RUN。--plan只有原固件加载和实时程序两段命令，execution=NOT_RUN。

通过条件：文件检查退出0，当前mode为REALTIME_FRAME_RETIRE_125，缺失或身份差异为0。检查通过仅证明文件及合同，不证明硬件或模型效果。

## 3. Vivado与HLS安装条件

源码重建基线为Vivado2018.2（SW2258646/IP2256618）、Vivado HLS2018.2及Zynq-7000器件支持，目标xc7z020clg400-1。从合法渠道安装到自己的工具目录；本包不带安装包、官方专有源码或预生成HLS实现。

在相应工具命令环境确认vivado、vivado_hls和XILINX_VIVADO指向该版本。指南推荐其他较新版本，本项目采用2018.2的原因与差异须在最终设计报告说明；其他版本需要独立核对IP与构建兼容性。

预期/通过条件：工具和器件支持与基线一致；版本不一致先停止。详细依赖见[构建指南](build_guide.md)，只部署正式固件可跳过本章。

## 4. 板卡与PYNQ系统

使用PYNQ-Z2、pynq_z2_v3.1.1镜像标识及匹配的ARMv7环境。记录为Python3.10.4、PYNQ3.1.1、NumPy1.21.5、Pillow9.0.1，内核6.6.10-xilinx-v2024.1-g3c0eca68c652。合格系统还须满足原生库/内核哈希、系统字体、模型、网络、锁与冷启动条件，见[环境说明](environment.md)及board/application.json。

预期/通过条件：已有系统与实际环境合同匹配，可直接部署，不要求重新烧写。只有镜像名称相同不足以证明所有指纹相同。新系统的完整获取与准备配方尚待补充；不要假设任意同名镜像开箱可用。

## 5. Python依赖分工

电脑文件检查使用Python标准库；板端沿用合格系统，不运行pip批量升级。训练仅在电脑独立虚拟环境使用Python3.12.7和固定依赖。以下为可选训练环境准备，实际解释器名称依电脑安装情况替换：

```sh
python3.12 -m venv DATA_ROOT/new_ai_env
DATA_ROOT/new_ai_env/bin/python -m pip install -r src/ai/training/requirements.txt
```

Windows可用已安装的3.12解释器创建环境，环境内可执行文件为Scripts/python.exe；不要原样执行Linux的bin路径。依赖固定为NumPy1.26.4、scikit-learn1.5.1、joblib1.4.2。冻结JSON板端推理不需要sklearn/joblib。

预期/通过条件：板端环境保持原身份；电脑训练依赖与requirements一致。缺少训练数据时可直接复用冻结模型，不因安装训练环境宣称复现训练成功。

## 6. AD7606与屏幕接线

断电按[硬件说明](hardware_setup.md)和[数字接线表](ad7606_wiring.csv)接线。表内DB0至DB15、BUSY、FRSTDATA、CONVST、RESET、CS_N、RD均与当前XDC核对；CONVST_A/B共接RPi物理37，J5-32 GND接RPi物理6。RPi物理针脚不是BCM编号。

信号源连接模块模拟输入：CH1为V1/J3-9，CH2为V2/J3-8，模拟参考为AGND。本工程模块独立5V供电，J1选3V3（2–3），J2选±10V（1–2），OS[2:0]=000、SER=0、STBY=1。电源及固定脚位置见硬件说明，保持既有配置，不改控制器。

七寸触摸屏HDMI接板卡HDMI OUT，CTOUCH用数据线接板卡USB；供电方式见硬件说明。面板标称1024×600与工程1280×720输出分别记录，不照抄树莓派config.txt或改动现用视频配置。

预期/通过条件：物理连接、共地、电平与跳帽逐项确认，HDMI与USB均连接正确。AD7606电源、接口电平、量程及固定模式按本手册固定设置，实际部署须核对电源、电平和跳帽。

## 7. 信号发生器与输入条件

实际提供的十组输入已放入[data](../../data/README.md)。导入该批BIN时使用High-Z、Offset0、整段重复率1Hz，段内基波50Hz；面板幅度按十组配置表设置。该批为0.06Vpp补偿版本，面板值与文件名义幅值分开，不能直接套用下列原基准幅值作为新实测值。

既有正常参考条件为正弦50Hz、1Vpp、Offset0、High-Z、输出ON；双通道相对工况曾使用CH2=600mVpp。先核对仪器实际负载设置、幅度、偏置和示波器观察，不能只读取发生器面板数值。

现用CH1事件基准RMS为1152.9852916757695 ADC code，CH2为1157.8141936125858；两者都是受控相对参考，不是传感器或物理量标定。发生器OFF、悬空与已知零输入不同。

预期：保存实际输入配置、持续时间、接线和参考依据。通过条件：配置与引用的既有结果同条件；各谐波/扰动具体配置和仪器BIN profile未提供时按[测试指南](test_guide.md)记TODO，不根据模型预测反推参考标签。

## 8. 准备FPGA源码构建目录

源码位于src/pl/frame_retire_125，包含实际设计输入及原相对路径助手；外部依赖在build/dependencies/frame_retire_125。先检查：

```sh
python -B build/scripts/check_pl.py
```

正式准备新目录（会调用HLS，只有明确需要重建时执行）：

```sh
python -B build/scripts/prepare_pl.py --output .build/pl_001
```

只准备文件、不执行HLS可追加--prepare-only；离线依赖、工具路径参数见构建指南。脚本拒绝已有输出，核对25项PYNQ固定依赖及合法安装VDMA的原始/还原哈希。

预期/通过条件：check_pl身份通过；新工作目录preparation.json明确hls_generated状态、依赖身份且无覆盖。prepare-only的false不能手工改为true，完整构建需要换新目录正常准备。

## 9. 综合、实现与BIT/HWH生成

对完成HLS准备的新目录：

```sh
python -B build/scripts/build_pl.py --workspace .build/pl_001 --plan
python -B build/scripts/build_pl.py --workspace .build/pl_001
```

--plan只预览。实际流程依次为BD/IP、综合、Place、一次默认phys_opt和Route、两时序模型/布线/DRC核对、BIT、发布派生HWH转换及十窗口/reset隔离核对，详见[构建指南](build_guide.md)。

预期：output/artifacts/rebuilt_frame_retire_fclk1_125.bit、同名hwh和rebuilt_identity.json；新报告在output/reports，新DCP在output/checkpoints。

通过条件：构建门槛全满足，产物完整并有新SHA256。即使构建退出0，新身份仍为NEW_BUILD_REQUIRES_REVIEW_NOT_APPROVED_FOR_BOARD；不要求新BIT逐字节等于旧发布物，也不能改PS白名单强行加载。便携目录完整构建尚无执行结果，历史报告不代替新输出。

## 10. 正式固件身份与SHA256

部署使用board/runtime/frame_retire_125中的同名正式pair：

|文件|SHA256|
|---|---|
|final_frame_retire_fclk1_125.bit|45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4|
|final_frame_retire_fclk1_125.hwh|54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f|

根run.py --check会同时核对文件、原59项payload和身份表。板端也可只读核对两文件：

```sh
sha256sum board/runtime/frame_retire_125/final_frame_retire_fclk1_125.bit
sha256sum board/runtime/frame_retire_125/final_frame_retire_fclk1_125.hwh
```

预期/通过条件：两个SHA256精确相等，HWH为100/125MHz配套自有Frame Retire元数据。不能混用旧Lab07/unified_2或未经转换的raw HWH。

## 11. 部署文件、模型与Overlay前提

把完整同版本目录传入板端新英文目录，不覆盖在用目录。核对board/models/physical_portable_v11中的四个运行文件与固定服务目录；安装及已有文件处理见[运行指南](run_guide.md)。系统字体和192.168.2.99网络配置亦须满足，运行目录可写。

完成接线后正常关机、完整断电、重新上电。本boot内不先运行其他PL、Reader或视频程序；不要将杀掉旧进程视为硬件已安全复位。板端执行：

```sh
python3 -B run.py --check
sudo python3 -B run.py --precheck
```

预期/通过条件：文件通过；ready_for_original_startup=true，关键checks全true，hardware_access=false、bit_loaded=false。初筛不导入PYNQ或访问MMIO，也不独立证明冷启动历史。Overlay只由下一章根入口加载，不另开Notebook预加载。

## 12. 唯一PS入口与正式加载

使用同一合格Python解释器；若sudo的python3不指向该环境，使用实际合格解释器路径。执行：

```sh
sudo python3 -B run.py
```

根入口先校验文件与环境，再依次执行原01_load_identity.py和11_live_ui_touch.py，不另建Reader。预期加载日志最终IDENTITY_CHECK_PASS，时钟/寄存器身份符合；实时程序出现STAGE4_READY及ui4>。

在ui4>逐条输入：

```text
touch on
auto on
status
```

通过条件：实时所有者就绪，启用自动提交和触摸，运行身份/锁/epoch/ACK规则仍有效。失败停止处理，不自动重载、reset或重复启动。

## 13. 基础Feature查看

继续使用同一进程，在ui4>中可输入capture overview及status。观察双通道RMS/Peak/Crest、CH1频率与谐波特征；检查有效位、状态、帧身份及新鲜度，失效值不当0或当前正常。

预期/通过条件：合格输入下有效Feature可读，来自同一受控会话且持续更新，非有限数值/无效字段如实隐藏。独立幅频误差、传感器换算容差尚无批准数值时不新增“准确度通过”。具体条目见测试指南。

## 14. Raw波形与ACK

在ui4>输入capture waveform及status。共享快照snapshot_*.json中的waveform提供CH1/CH2本地副本，每路2048个int16样本；原Raw为uint32[2048]、8192字节，低16位CH1、高16位CH2。

预期/通过条件：只有完整copy、descriptor复核及ACK确认的数据才发布；帧号、epoch、关联和drop诊断保留。Feature/Raw为UNMATCHED时分别说明，不能拿它们做同帧整数比对；相邻帧不补配。不得另开Raw测试程序争用Reader。

## 15. 双通道事件

在ui4>输入capture events及status；双路事件消费同一已ACK的Raw副本，分别使用各自基准。标称fs=10000Hz、f0=50Hz、窗口200点、确认保持10ms。

预期状态按pu阈值：<0.1为INTERRUPTION，0.1至小于0.9为SAG，0.9至1.1为NORMAL，>1.1为SWELL。缺口/故障不得继续报正常；CH2基准和输出独立。

通过条件：在已知参考工况下通道、状态、起止/确认和缺口处理与预先批准规则一致。工况幅度、持续时间及允许检测延迟缺少正式记录时写TODO。本系统事件已接入，不因缺少提交材料倒写为未实现。

## 16. AI训练、推理与既有模型

在线主模式已加载CH1 LR，并显示符合资格的结果。输入顺序为H3_pct、H5_pct、H7_pct、H9_pct、THD_ODD_pct、Crest；前五项为百分比，最后为比值。LR缩放器已包含，不重复标准化；原资格保持TRAINING_ONLY。

复用冻结模型按第11章部署即可，不必重训。可选训练需提供批准Manifest及其真实数据、标签/谱系/用途审核，使用独立电脑环境：

```sh
python -B src/ai/training/train_from_manifest.py --manifest DATA_ROOT/released_training_manifest.json --output DATA_ROOT/new_training_run
```

上面训练命令中的python必须是第5章的独立电脑虚拟环境解释器；未激活环境时，替换为DATA_ROOT/new_ai_env/bin/python，Windows替换为该环境的Scripts/python.exe。不要在板端环境执行训练。

默认冻结Manifest有身份门槛；其他批准清单须显式指定--expected-manifest-sha256，不能改默认值冒充同一训练。当前未随代码包交付原训练数据；缺少真实输入时本步骤TODO，不伪造数据或运行结果。

已有批准的保存Adapter输入可在电脑使用Python3.10+标准库推理，不操作Reader：

```sh
python -B src/ai/inference/predict_saved.py --model-dir src/ai/models/physical_portable_v11 --algorithm logistic_regression --input DATA_ROOT/approved_saved_inputs.json --output DATA_ROOT/new_lr_outputs.json
```

输入格式按推理README，不能用未审核的任意六个数替代checked合同；RF将algorithm改为random_forest。输出必须是新文件，拒绝/错误保留空预测，保存输入CLI不能重新证明现场新鲜度。

保存输入推理和冻结原权重导出见[推理](../../src/ai/inference/README.md)、[训练](../../src/ai/training/README.md)。保存结果计分见[评估](../../src/ai/evaluation/README.md)：predict_saved与score_paired交换格式不同，不能直接串接。技能中的黄金/EV26实例有自己的用途范围，不是新独立泛化测试。

预期/通过条件：模型/特征身份一致，拒绝输入不显示旧预测；可选新训练/推理输出在新位置并有可追溯输入。在线结果不由离线工具另建Reader，历史离线数据管理器旧Lab07身份不影响现用125MHz适配器。

## 17. 电脑端UI

板端唯一实时程序运行并启用auto后，电脑浏览器访问http://192.168.2.99:8765，可只读查看/api/state。电脑需有到板端的网络路由，不安装第二个采集服务。浏览器与板端HDMI共用SnapshotStore。

预期/通过条件：四页能访问，快照身份与板端同一来源；过期、拒绝或无效值按合同清空。电脑连接/关闭不抢占Reader。页面刷新率不等于ADC采样率，既有显示观察不外推为60FPS或长期稳定指标。

## 18. 完整联调、停止与排障

按[测试指南](test_guide.md)观察采集→Feature/Raw→双路事件→CH1模型→HDMI触摸/PC共享链。检查日志目录board/runtime/frame_retire_125/results/，包括events.jsonl、FRAME_RETIRE_ITERATIONS.jsonl、event_results.jsonl、model_results.jsonl、snapshot_*.json及worker日志。

预期/通过条件：同一Reader/会话，提交/退休/ACK保持身份，画面实际可见，触摸可切换；同帧资格不足时不伪配、不沿用旧分类，错误和drop如实保留。协议验证、模拟准确度和泛化性能分别说明。

正常结束用另一终端执行sudo poweroff，待系统关机后完整断电；保留原owner和Buffer引用到关机。auto off仅暂停提交，不释放DMA。不要使用kill、Ctrl+C、freebuffer或重复reset替代关闭。故障先保留原报错和状态，见[排障](troubleshooting.md)，不以放宽身份检查处理。

## 19. 结果记录与复现范围

六组既有模块仿真见[sim](../../sim/README.md)，8份最终综合与实现报告见[build/reports](../../build/reports/frame_retire_125/README.md)，十组波形输入及AWG设置见[data](../../data/README.md)。各结果按其原日期、源码、参数和适用范围解读；输入波形不等同于实测输出。

独立部署或重建时，将实际使用的软件、固件与模型哈希、输入设置、输出和判据一并保存到新的结果目录。未执行的步骤标为NOT_RUN，不能以预期输出或旧报告代替实际结果。完整构建和板端操作是否执行，由实际操作者据实记录。

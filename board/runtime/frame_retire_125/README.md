# 125 MHz实时运行模块

工程唯一应用入口为根目录[run.py](../../../run.py)。它使用同一Python解释器，依次转调本目录01_load_identity.py与11_live_ui_touch.py；采集、事件、模型、HDMI、触摸和PC共享显示均由原有实时程序完成，不建立第二个Reader。

本目录对应2026-11-03实时版本。正式BIT/HWH、Python源码和shell入口保持原字节；CH2基准配置仅省略未使用的历史目录字段，所有基准数值保留。11_payload_sha256.json严格校验59项运行文件，DEPLOYMENT_SHA256.json校验完整部署集合。regression_support、live_boot_assets及其余受身份清单约束的文件是冻结运行集合，不按名称裁剪；其中独立探针和旧smoke入口不作为操作步骤，不直接启动。

## 启动

先按[环境说明](../../../docs/reproducibility/environment.md)核对固定模型、字体、网络及合格系统，再按[运行说明](../../../docs/reproducibility/run_guide.md)冷启动。在工程根目录执行：

```sh
python3 -B run.py --check
python3 -B run.py --plan
sudo python3 -B run.py --precheck
sudo python3 -B run.py
```

python3必须指向记录的合格PYNQ环境；sudo下也要使用同一环境。出现STAGE4_READY和ui4>后，依次输入touch on、auto on、status。PC浏览器访问http://192.168.2.99:8765，与HDMI共用SnapshotStore。原shell入口保留用于来源核对，日常使用根入口。

固件FCLK0=100MHz、FCLK1=125MHz。模型固定目录及四文件哈希见[模型部署说明](../../models/physical_portable_v11/README.md)。字体来自板端系统，不在模块中分发。运行产生results/，不纳入版本管理。

## 停止与边界

auto off仅暂停新画面提交，不停止DMA或释放Buffer。通过另一终端正常poweroff，再完整断电；在此之前保留owner与引用。不要用kill、Ctrl+C、freebuffer或重复reset作为关闭流程。启动失败停止处理，不自动重载或重试。

既有记录包含触摸四页、双路事件、模型显示、PC重连及85次提交/ACK；这些记录只代表对应版本及运行条件。悬空输入、Raw/Feature UNMATCHED、模型TRAINING_ONLY及未校准量值按真实状态呈现，不外推为全部工况、长期稳定或泛化精度通过。完整系统已完成既有联调；版本与构建范围见[范围说明](../../../docs/reproducibility/scope.md)。

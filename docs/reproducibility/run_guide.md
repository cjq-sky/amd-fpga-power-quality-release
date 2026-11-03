# 125 MHz实时系统部署与运行

唯一日常入口是工程根目录run.py。它依次运行原01_load_identity.py和11_live_ui_touch.py，保留原固件身份、冷启动、锁、单Reader、缓冲区和ACK规则；不会另写一套采集或显示实现。

## 1. 部署准备

按[环境说明](environment.md)确认合格系统。把工程放入新的英文路径，不覆盖板端正在运行的版本。运行目录需要写权限。核对[接线](hardware_setup.md)、HDMI OUT、USB触摸及可控输入；不要同时运行旧Notebook、视频或Reader进程。

模型四文件来源为board/models/physical_portable_v11，既有服务固定查找/home/xilinx/jupyter_notebooks/lab07_bai_integration/physical_portable_v11_ge8e6qs4。已有该目录先按board/application.json核对四文件SHA256；完全匹配直接使用。目录缺失时，在无硬件程序运行的状态下创建并部署四文件；未知或不匹配内容先另行保存、核实，不能覆盖或改白名单凑通过。README不用部署。必须有固定中文字体，且网络已配置192.168.2.99、TCP8765空闲。

电脑可先做文件检查。板端使用包含合格PYNQ环境的同一Python解释器；若sudo环境的python3不是该解释器，使用其实际绝对路径，不切换到其他虚拟环境。

```sh
python3 -B run.py --check
python3 -B run.py --plan
```

预期：检查JSON的global_file_identity、file_coverage、python310_syntax及runtime身份均PASS，hardware/inference/fpga_build为NOT_RUN；计划只有两个原程序命令，execution为NOT_RUN。任何身份失败先停止。

## 2. 冷启动与只读环境初筛

旧版本使用后按原流程关机并完整断电，再冷上电。本boot内不要先启动其他PL/采集/视频程序；仅杀掉旧进程不足以证明DMA已停止。部署目录内也不得存在本boot的旧启动记录。

```sh
sudo python3 -B run.py --precheck
```

预期：ready_for_original_startup=true，所有checks为true；hardware_access=false、bit_loaded=false。检查读取版本/指纹、字体、模型、网络、端口、锁及本目录启动记录，不导入PYNQ、不访问MMIO、不改网络、不加载固件。它不能独立证明此前硬件总线历史安全，操作者仍须满足完整冷启动前提。

## 3. 正式启动

```sh
sudo python3 -B run.py
```

程序再次核对文件和环境，然后使用同一sys.executable执行固件加载身份检查，成功后以原实时程序接管进程。不能在--plan输出里手工替换boot标识跳过前提。

预期：原加载记录最终为IDENTITY_CHECK_PASS；配套固件、PS时钟与MMIO身份符合合同；随后STAGE4_READY并进入ui4>。加载失败立即停止，不自动reset、重载或重试。启动记录位于board/runtime/frame_retire_125/results/，不提交生成物。

## 4. 实时显示与电脑访问

在ui4>中逐条输入，观察每步返回后继续：

```text
touch on
auto on
status
```

预期：触摸切换四页，自动提交新画面；Feature/Raw、双路事件及符合资格的CH1模型结果按原合同呈现。PC访问http://192.168.2.99:8765，与HDMI共用同一SnapshotStore，不另建Reader。UNMATCHED、无效输入、TRAINING_ONLY、未标定量值和缺失结果必须如实显示。丢帧计数如实记录，不通过清零或伪配帧制造PASS。

操作PASS以真实现场画面和对应运行状态为准，文件检查不证明像素/事件/分类正确。既有记录按其软件、固件和输入条件引用。

## 5. 结束

auto off只暂停提交，不代表DMA停止或Buffer释放。保持原owner进程与引用，在另一终端执行正常poweroff，再完整断电。不要把Ctrl+C、kill、freebuffer、stop/start或反复reset当作正常关闭。故障分流见[排障](troubleshooting.md)。


## 四文件模型的首次安装

只有固定模型目录缺失时才需要复制。在无活动采集/显示进程时，下面命令从板端工程根目录使用合格解释器执行：校验源/目标身份，仅目标缺失时写入副本，不导入模型、不访问硬件。目标已存在且匹配则直接复用；不匹配立即停止，不覆盖原文件。复制中断的部分目录也保留，核实后另行处理。

```sh
sudo python3 -B - <<'PY'
from pathlib import Path
import hashlib
import json
import shutil

profile = json.loads(Path('board/application.json').read_text(encoding='utf-8'))
source = Path('board/models/physical_portable_v11')
target = Path(profile['external_model_directory'])
expected = profile['model_sha256']
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name, value in expected.items():
    if digest(source / name) != value:
        raise SystemExit('SOURCE_MODEL_IDENTITY_MISMATCH: ' + name)
if target.exists():
    for name, value in expected.items():
        path = target / name
        if not path.is_file() or digest(path) != value:
            raise SystemExit('EXISTING_MODEL_MISMATCH_NO_OVERWRITE: ' + name)
    print('MODEL_ALREADY_MATCHES')
else:
    target.mkdir(parents=True, exist_ok=False)
    for name in expected:
        with (source / name).open('rb') as src, (target / name).open('xb') as dst:
            shutil.copyfileobj(src, dst)
        if digest(target / name) != expected[name]:
            raise SystemExit('COPIED_MODEL_IDENTITY_MISMATCH: ' + name)
    print('MODEL_INSTALLED_AND_VERIFIED')
PY
```

预期是MODEL_ALREADY_MATCHES或MODEL_INSTALLED_AND_VERIFIED。出现MISMATCH停止；不能修改board/application.json或原服务白名单来接纳不同文件。仅在目标目录缺失时执行安装。

Feature、Raw、事件、模型和共享显示的观察命令及判据见[测试指南](test_guide.md)。整个流程见[总手册](reproduction_guide.md)。

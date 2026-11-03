# 环境与依赖

## 合格板端系统

板卡为PYNQ-Z2，镜像标识pynq_z2_v3.1.1。已有符合下表及原平台指纹的系统，可直接进入[部署步骤](run_guide.md)，不要求重新制作镜像。镜像名称相同不自动证明内核/原生扩展一致。

|项目|既有运行记录/要求|
|---|---|
|CPU架构|armv7l|
|Python|记录3.10.4；原平台门槛为3.10系列|
|PYNQ|3.1.1|
|NumPy|1.21.5，匹配的ARM原生扩展|
|Pillow|记录9.0.1，须可导入PIL|
|Linux|6.6.10-xilinx-v2024.1-g3c0eca68c652|
|PL|配套125MHz BIT/HWH；FCLK0=100MHz、FCLK1=125MHz|
|网络|板端地址192.168.2.99，TCP8765空闲|
|中文字体|/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf，必须存在|
|可选等宽字体|/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf；缺失按原渲染器回退|

原platform_guard还核对PYNQ mmio.py、embedded_device.py、NumPy原生扩展、/boot/image.ub及/sys/kernel/notes的精确SHA256。期望值见board/application.json，原程序仍保留自己的独立检查。不要为通过而修改指纹或pip升级板端库。字体采用板端已有合法系统文件，不随工程分发。

## 环境检查

工程根目录执行python -B run.py --check仅需电脑Python3.10+标准库，不安装板端库。python -B run.py --plan不运行命令。板端以实际合格Python运行sudo python3 -B run.py --precheck，预期ready_for_original_startup=true；文件身份、模型、字体、网络和锁任何关键项不满足先处理，禁止直接绕过初筛启动。该步骤不加载固件、不导入PYNQ。

版本元数据差异会列为warning；原实时程序仍会核对实际导入的PYNQ/NumPy版本及原生指纹。同名镜像仍须核对实际版本与原生库指纹，不能仅凭镜像名称认定兼容。

## 电脑与构建环境

PC显示使用可访问板端的浏览器，不需要独立采集客户端。离线AI工具依赖及训练环境见src/ai/README.md；训练使用独立电脑环境，不改板端PYNQ。Vivado/HLS2018.2属于PL源码重建路径，现用发布固件部署不要求先安装工具或重建；现用125MHz源码构建入口已在build/scripts，工具版本、依赖准备和新目录要求见[构建说明](build_guide.md)；便携目录完整构建尚无执行结果。


## 检查边界与七寸屏

--precheck不会测量供电/波形、读取屏幕EDID或打开USB触摸，不能由ready=true推导这些实物项目通过。数字接线完整表及7英寸屏资料已整理到[硬件说明](hardware_setup.md)。屏幕说明书标称面板1024×600；现用工程输出1280×720，两者分开记录，不改已使用的视频配置。

PC只需浏览器与到192.168.2.99的可达网络，根离线检查也不需要NumPy/Pillow。board/requirements/pc.txt记录此范围；离线AI训练依赖只安装到电脑独立虚拟环境。

具备合格系统的板卡直接部署。尚无合格系统时，必须取得满足记录版本及原生指纹的合法环境；其完整获取/准备配方待补，不提供猜测的pip/内核升级命令，也不要求现有板卡备份或重做SD卡。

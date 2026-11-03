# 版权与外部依赖

团队代码重新发布授权仍待确认，不擅选MIT/Apache。公开发布前须确认作者授权及各项依赖许可。

视频IP依赖固定来自[Xilinx/PYNQ](https://github.com/Xilinx/PYNQ/tree/d9c752164644ebdbf7f96e4cd7d96661d1276a34/boards/ip)，根BSD-3-Clause通知在pynq_license.txt；各文件自身Digilent/Xilinx通知及设备用途限制也须保留。根许可不能抹去文件自身条款。

不直接打包vendor实现、Vivado/HLS安装源或生成RTL；固定来源/哈希和本地生成步骤见build/dependencies/frame_retire_125/pynq_dependencies.json、build/scripts/prepare_pl.py及构建说明。自有BD辅助脚本保留PYNQ来源与通知，自有VDMA适配不冒充原厂core或驱动。

现用实时UI使用合格板端系统的DroidSansFallbackFull.ttf，NotoSansMono-Regular.ttf为可选回退字体来源，具体路径见环境说明。字体不随工程分发，系统字体各自许可由其合法安装渠道保留。旧Windows Microsoft YaHei个人用途子集不纳入本包。不要擅改字体路径或把更换字体后的视觉效果当作原验证结果。

不带历史照片和整批原始测试数据。live_boot_assets为冻结运行清单内的冷初始化素材，须保持完整；实时四页由原程序的受控快照渲染。程序中的Linux设备/锁/部署接口路径是运行合同，不是开发者本地磁盘路径。

固件payload名称保留冻结大小写，不能单独更名破坏软件身份合同。其他新文件用英文路径。


## 125MHz VDMA构建依赖

官方VDMA原源含专有/保密声明，不纳入本包。build/dependencies/frame_retire_125/vdma_patch.json只保存团队增量及原始/结果SHA256；用户从合法授权的Vivado2018.2安装在自己的新构建目录生成所需派生输入。此配方不替代适用工具/IP许可，也不授予额外公开权利。官方FFT及视频HLS生成实现同样在用户构建目录生成，不作为源码提交。源文件自身通知、器件用途限制与团队公开授权边界仍适用。

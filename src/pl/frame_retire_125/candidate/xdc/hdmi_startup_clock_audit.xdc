# Audit-only startup model: original MMCM M=10,D=1,O=2, BUFR/5.
create_generated_clock -name I -source [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/Inst_mmcme2_drp/mmcm_adv_inst/CLKIN1}] -multiply_by 5 [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/Inst_mmcme2_drp/mmcm_adv_inst/CLKOUT0}]
create_generated_clock -name axi_dynclk_0_PXL_CLK_O -source [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/Inst_mmcme2_drp/mmcm_adv_inst/CLKIN1}] -multiply_by 1 -duty_cycle 40 [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/BUFR_inst/O}]
# SerialClk inherits the same physical I clock through BUFIO; no backwards pixel-derived clock.

# Lab08 external-serial mode: both outputs have a forward physical path
# from the MMCM reference. Do not derive serial backwards from pixel.
# Native PYNQ DisplayClkFindParams(74.25MHz pixel): M=52,D=7,O=2.
# Serial=100*26/7MHz; BUFR/5 pixel=100*26/35MHz, duty40%.
# STA operating point only; official DRP/PHY RTL is unchanged.
create_generated_clock -name I -source [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/Inst_mmcme2_drp/mmcm_adv_inst/CLKIN1}] -multiply_by 26 -divide_by 7 [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/Inst_mmcme2_drp/mmcm_adv_inst/CLKOUT0}]
create_generated_clock -name axi_dynclk_0_PXL_CLK_O -source [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/Inst_mmcme2_drp/mmcm_adv_inst/CLKIN1}] -multiply_by 26 -divide_by 35 -duty_cycle 40 [get_pins -hier -filter {NAME =~ */axi_dynclk/U0/BUFR_inst/O}]
# SerialClk inherits the same physical I clock through BUFIO; no backwards pixel-derived clock.

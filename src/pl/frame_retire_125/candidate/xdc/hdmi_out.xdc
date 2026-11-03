# PYNQ-Z2 HDMI OUT only; official base.xdc ball/IOSTANDARD mapping.
set_property -dict {PACKAGE_PIN L17 IOSTANDARD TMDS_33} [get_ports hdmi_out_clk_n]
set_property -dict {PACKAGE_PIN L16 IOSTANDARD TMDS_33} [get_ports hdmi_out_clk_p]
set_property -dict {PACKAGE_PIN K18 IOSTANDARD TMDS_33} [get_ports {hdmi_out_data_n[0]}]
set_property -dict {PACKAGE_PIN K17 IOSTANDARD TMDS_33} [get_ports {hdmi_out_data_p[0]}]
set_property -dict {PACKAGE_PIN J19 IOSTANDARD TMDS_33} [get_ports {hdmi_out_data_n[1]}]
set_property -dict {PACKAGE_PIN K19 IOSTANDARD TMDS_33} [get_ports {hdmi_out_data_p[1]}]
set_property -dict {PACKAGE_PIN H18 IOSTANDARD TMDS_33} [get_ports {hdmi_out_data_n[2]}]
set_property -dict {PACKAGE_PIN J18 IOSTANDARD TMDS_33} [get_ports {hdmi_out_data_p[2]}]
set_property -dict {PACKAGE_PIN R19 IOSTANDARD LVCMOS33} [get_ports {hdmi_out_hpd[0]}]
# HPDN is asynchronous status, terminated only at a two-flop synchronizer.
set hpd_meta [get_pins -hier -filter {NAME == hpd_sync/sync_meta_reg/D}]
# Endpoint count is checked by the full Tcl implementation hook (not the restricted XDC parser).
set_false_path -from [get_ports {hdmi_out_hpd[0]}] -to $hpd_meta
# Clock constraints are applied separately by the LATE
# hdmi_external_serial_clock.xdc. Both runtime720p and the unchanged startup
# MMCM state are audited; a faster startup clock alone is not a timing proof.
# XDC models do not program runtime DRP/VTC or assert hardware display PASS.

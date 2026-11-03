# Independent unified_2 candidate; all writes stay in this new task directory.
set root [file normalize [file join [file dirname [info script]] ..]]
set attempt FINAL_FRAME_RETIRE_FCLK1_125_EVAL_1
set smoke 0
cd $root
file mkdir [file join reports $attempt]
set reportdir [file join $root reports build_1]
file mkdir $reportdir
set projdir [file join $root p u2]
if {[file exists $projdir]} {error "Refuse to overwrite existing project"}
set status [open [file join $reportdir stage_status.txt] w]
proc mark {s} {global status; puts $status $s; flush $status; puts "LAB08_STAGE: $s"}
proc pin {s} {return [get_bd_pins $s]}
proc ip {name vlnv} {return [create_bd_cell -type ip -vlnv $vlnv $name]}
proc must_run {name} {
  set s [get_property STATUS [get_runs $name]]
  if {![string match "*Complete*" $s]} {error "$name failed: $s"}
}
proc build {} {
  global root attempt reportdir projdir smoke
  if {[version -short] ne "2018.2"} {error "Requires Vivado2018.2"}
  set_param general.maxThreads 4
  create_project lab07_lab08_unified_2 $projdir -part xc7z020clg400-1
  mark CREATE_PROJECT_PASS
  set_property target_language Verilog [current_project]
  set_property ip_repo_paths [list [file join $root ip vendor] [file join $root ip warm_reset] \
      [file join $root ip generated pixel_unpack solution1 impl ip] \
      [file join $root ip generated color_convert solution1 impl ip]] [current_project]
  set_property ip_repo_paths [concat [get_property ip_repo_paths [current_project]] [list [file normalize $root/../lab07_ip_repo]]] [current_project]
  update_ip_catalog
  mark IP_CATALOG_PASS
  add_files -norecurse [file join $root rtl hdmi_hpd_sync.v]
  # Initialize the installed IPI Tcl procedures exactly as the verified Lab07 flow.
  set ipi_init [file join $::env(XILINX_VIVADO) scripts ipintegrator init.tcl]
  if {![file readable $ipi_init]} {error "Installed IPI initialization unreadable: $ipi_init"}
  set previous_cwd [pwd]
  cd [file dirname $ipi_init]
  uplevel #0 [list source -notrace $ipi_init]
  cd $previous_cwd
  create_bd_design base
  source [file join $root tcl unified2_out_helpers.tcl]
  set ps7_0 [ip ps7_0 xilinx.com:ip:processing_system7:5.5]
  source [file join $root tcl official_ps_preset.tcl]
  # Remove PS fabric interfaces belonging to non-video full-Base components.
  set_property -dict [list CONFIG.PCW_USE_M_AXI_GP0 {1} CONFIG.PCW_USE_M_AXI_GP1 {0} \
    CONFIG.PCW_USE_S_AXI_GP0 {0} CONFIG.PCW_USE_S_AXI_GP1 {0} \
    CONFIG.PCW_USE_S_AXI_HP0 {1} CONFIG.PCW_USE_S_AXI_HP2 {0} \
    CONFIG.PCW_USE_FABRIC_INTERRUPT {1} CONFIG.PCW_IRQ_F2P_INTR {1} \
    CONFIG.PCW_EN_CLK2_PORT {0} CONFIG.PCW_EN_CLK3_PORT {0} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ {125} CONFIG.PCW_S_AXI_HP0_FREQMHZ {125}] $ps7_0
  set ddr [create_bd_intf_port -mode Master -vlnv xilinx.com:interface:ddrx_rtl:1.0 DDR]
  set fixed [create_bd_intf_port -mode Master -vlnv xilinx.com:display_processing_system7:fixedio_rtl:1.0 FIXED_IO]
  connect_bd_intf_net $ddr [get_bd_intf_pins ps7_0/DDR]
  connect_bd_intf_net $fixed [get_bd_intf_pins ps7_0/FIXED_IO]
  set tmds [create_bd_intf_port -mode Master -vlnv digilentinc.com:interface:tmds_rtl:1.0 hdmi_out]
  create_bd_port -dir I -from 0 -to 0 hdmi_out_hpd_sync
  create_bd_port -dir O -type clk hpd_sync_clk_100m
  set_property CONFIG.FREQ_HZ {100000000} [get_bd_ports hpd_sync_clk_100m]
  set_property CONFIG.ASSOCIATED_RESET {hpd_sync_resetn} [get_bd_ports hpd_sync_clk_100m]
  create_bd_port -dir O -type rst hpd_sync_resetn
  set_property CONFIG.POLARITY {ACTIVE_LOW} [get_bd_ports hpd_sync_resetn]
  set video [create_bd_cell -type hier video]
  current_bd_instance $video
  create_bd_intf_pin -mode Slave -vlnv xilinx.com:interface:aximm_rtl:1.0 S_AXI
  create_bd_intf_pin -mode Master -vlnv xilinx.com:interface:aximm_rtl:1.0 M_AXI
  create_bd_intf_pin -mode Master -vlnv digilentinc.com:interface:tmds_rtl:1.0 TMDS_out
  foreach name {clk_100M clk_142M} {create_bd_pin -dir I -type clk $name}
  foreach name {periph_resetn_clk100M periph_resetn_clk142M ic_resetn_clk100M ic_resetn_clk142M} {
    create_bd_pin -dir I -type rst $name
  }
  create_bd_pin -dir I -from 0 -to 0 hdmi_out_hpd
  foreach name {mm2s_irq vtc_irq hpd_irq} {create_bd_pin -dir O -type intr $name}
  create_hier_cell_hdmi_out $video hdmi_out
  create_bd_pin -dir O retire_video_resetn
  connect_bd_net [get_bd_pins hdmi_out/retire_video_resetn] [get_bd_pins retire_video_resetn]

  set dma [ip axi_vdma xilinx.com:ip:axi_vdma:6.3]
  set_property -dict [list CONFIG.c_include_mm2s {1} CONFIG.c_include_s2mm {0} \
    CONFIG.c_m_axi_mm2s_data_width {32} CONFIG.c_m_axis_mm2s_tdata_width {32} \
    CONFIG.c_mm2s_genlock_mode {1} CONFIG.c_mm2s_linebuffer_depth {512} \
    CONFIG.c_mm2s_max_burst_length {32} CONFIG.c_num_fstores {4}] $dma
  set ctrl [ip axi_interconnect_0 xilinx.com:ip:axi_interconnect:2.1]
  set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {7}] $ctrl
  set mem [ip axi_mem_intercon xilinx.com:ip:axi_interconnect:2.1]
  set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] $mem
  connect_bd_intf_net [get_bd_intf_pins S_AXI] [get_bd_intf_pins axi_interconnect_0/S00_AXI]
  set leaves {axi_vdma/S_AXI_LITE hdmi_out/S01_AXILite hdmi_out/S03_AXILite hdmi_out/S04_AXILite hdmi_out/S02_AXILite hdmi_out/S00_AXILite hdmi_out/S05_AXILite}
  for {set i 0} {$i < 7} {incr i} {
    connect_bd_intf_net [get_bd_intf_pins axi_interconnect_0/M0${i}_AXI] [get_bd_intf_pins [lindex $leaves $i]]
    set clock [expr {$i in {1 2} ? "clk_142M" : "clk_100M"}]
    set reset [expr {$i in {1 2} ? "periph_resetn_clk142M" : "periph_resetn_clk100M"}]
    connect_bd_net [pin $clock] [pin axi_interconnect_0/M0${i}_ACLK]
    connect_bd_net [pin $reset] [pin axi_interconnect_0/M0${i}_ARESETN]
  }
  connect_bd_intf_net [get_bd_intf_pins axi_vdma/M_AXI_MM2S] [get_bd_intf_pins axi_mem_intercon/S00_AXI]
  connect_bd_intf_net [get_bd_intf_pins axi_mem_intercon/M00_AXI] [get_bd_intf_pins M_AXI]
  connect_bd_intf_net [get_bd_intf_pins axi_vdma/M_AXIS_MM2S] [get_bd_intf_pins hdmi_out/in_stream]
  connect_bd_intf_net [get_bd_intf_pins hdmi_out/TMDS_out] [get_bd_intf_pins TMDS_out]
  connect_bd_net [pin clk_100M] [pin axi_interconnect_0/ACLK] [pin axi_interconnect_0/S00_ACLK] [pin axi_vdma/s_axi_lite_aclk] [pin hdmi_out/clk_100M]
  connect_bd_net [pin clk_142M] [pin axi_mem_intercon/ACLK] [pin axi_mem_intercon/S00_ACLK] [pin axi_mem_intercon/M00_ACLK] [pin axi_vdma/m_axi_mm2s_aclk] [pin axi_vdma/m_axis_mm2s_aclk] [pin hdmi_out/clk_142M]
  connect_bd_net [pin periph_resetn_clk100M] [pin axi_interconnect_0/S00_ARESETN] [pin axi_vdma/axi_resetn] [pin hdmi_out/periph_resetn_clk100M]
  connect_bd_net [pin ic_resetn_clk100M] [pin axi_interconnect_0/ARESETN]
  connect_bd_net [pin periph_resetn_clk142M] [pin axi_mem_intercon/S00_ARESETN] [pin axi_mem_intercon/M00_ARESETN] [pin hdmi_out/periph_resetn_clk142M]
  connect_bd_net [pin ic_resetn_clk142M] [pin axi_mem_intercon/ARESETN]
  connect_bd_net [pin hdmi_out_hpd] [pin hdmi_out/hdmi_out_hpd]
  connect_bd_net [pin axi_vdma/mm2s_introut] [pin mm2s_irq]
  connect_bd_net [pin hdmi_out/vtc_out_irq] [pin vtc_irq]
  connect_bd_net [pin hdmi_out/hdmi_out_hpd_irq] [pin hpd_irq]
  current_bd_instance /
  connect_bd_intf_net $tmds [get_bd_intf_pins video/TMDS_out]
  set ctrl [ip ps7_0_axi_periph xilinx.com:ip:axi_interconnect:2.1]
  set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {4}] $ctrl
  ip system_interrupts xilinx.com:ip:axi_intc:4.1
  set concat [ip video_interrupts xilinx.com:ip:xlconcat:2.1]
  set_property CONFIG.NUM_PORTS {3} $concat
  set one [ip one xilinx.com:ip:xlconstant:1.1]
  set zero [ip zero xilinx.com:ip:xlconstant:1.1]
  set_property CONFIG.CONST_VAL {1} $one
  set_property CONFIG.CONST_VAL {0} $zero
  foreach n {0 1} {
    set rst [ip rst_ps7_0_fclk$n xilinx.com:ip:proc_sys_reset:5.0]
    set_property CONFIG.C_EXT_RESET_HIGH {0} $rst
    set_property CONFIG.C_AUX_RESET_HIGH {1} $rst
    connect_bd_net [pin ps7_0/FCLK_CLK$n] [pin rst_ps7_0_fclk$n/slowest_sync_clk]
    connect_bd_net [pin ps7_0/FCLK_RESET0_N] [pin rst_ps7_0_fclk$n/ext_reset_in]
    connect_bd_net [pin one/dout] [pin rst_ps7_0_fclk$n/dcm_locked]
    connect_bd_net [pin zero/dout] [pin rst_ps7_0_fclk$n/aux_reset_in] [pin rst_ps7_0_fclk$n/mb_debug_sys_rst]
  }
  connect_bd_net [get_bd_ports hdmi_out_hpd_sync] [pin video/hdmi_out_hpd]
  connect_bd_net [pin ps7_0/FCLK_CLK0] [pin ps7_0/M_AXI_GP0_ACLK] [pin video/clk_100M] [pin ps7_0_axi_periph/ACLK] [pin ps7_0_axi_periph/S00_ACLK] [pin ps7_0_axi_periph/M00_ACLK] [pin ps7_0_axi_periph/M01_ACLK] [pin system_interrupts/s_axi_aclk] [get_bd_ports hpd_sync_clk_100m]
  connect_bd_net [pin ps7_0/FCLK_CLK1] [pin ps7_0/S_AXI_HP0_ACLK] [pin video/clk_142M]
  connect_bd_net [pin rst_ps7_0_fclk0/peripheral_aresetn] [pin ps7_0_axi_periph/S00_ARESETN] [pin ps7_0_axi_periph/M00_ARESETN] [pin ps7_0_axi_periph/M01_ARESETN] [pin video/periph_resetn_clk100M] [pin system_interrupts/s_axi_aresetn] [get_bd_ports hpd_sync_resetn]
  connect_bd_net [pin rst_ps7_0_fclk0/interconnect_aresetn] [pin ps7_0_axi_periph/ARESETN] [pin video/ic_resetn_clk100M]
  connect_bd_net [pin rst_ps7_0_fclk1/peripheral_aresetn] [pin video/periph_resetn_clk142M]
  connect_bd_net [pin rst_ps7_0_fclk1/interconnect_aresetn] [pin video/ic_resetn_clk142M]
  connect_bd_intf_net [get_bd_intf_pins ps7_0/M_AXI_GP0] [get_bd_intf_pins ps7_0_axi_periph/S00_AXI]
  connect_bd_intf_net [get_bd_intf_pins ps7_0_axi_periph/M00_AXI] [get_bd_intf_pins video/S_AXI]
  connect_bd_intf_net [get_bd_intf_pins ps7_0_axi_periph/M01_AXI] [get_bd_intf_pins system_interrupts/s_axi]
  connect_bd_intf_net [get_bd_intf_pins video/M_AXI] [get_bd_intf_pins ps7_0/S_AXI_HP0]
  connect_bd_net [pin video/mm2s_irq] [pin video_interrupts/In0]
  connect_bd_net [pin video/vtc_irq] [pin video_interrupts/In1]
  connect_bd_net [pin video/hpd_irq] [pin video_interrupts/In2]
  connect_bd_net [pin video_interrupts/dout] [pin system_interrupts/intr]
  connect_bd_net [pin system_interrupts/irq] [pin ps7_0/IRQ_F2P]
  # Lab07 stays in its original H16/125MHz domain; root AXI interconnect
  # provides the 100MHz->125MHz clock conversion for these two MI ports.
  set shared [create_bd_port -dir I -type clk shared_clk]
  set_property CONFIG.FREQ_HZ 125000000 $shared
  ip lab07_mmio pq.local:user:lab07_feature_mmio:1.0
  ip lab07_raw pq.local:user:lab07_raw_window:1.0
  set_property CONFIG.RAW_BASE_ADDRESS 0x43C10000 [get_bd_cells lab07_raw]
  ip rst_shared xilinx.com:ip:proc_sys_reset:5.0
  set_property CONFIG.C_EXT_RESET_HIGH 0 [get_bd_cells rst_shared]
  connect_bd_net $shared [pin rst_shared/slowest_sync_clk] [pin lab07_mmio/s_axi_aclk] [pin lab07_raw/s_axi_aclk] [pin ps7_0_axi_periph/M02_ACLK] [pin ps7_0_axi_periph/M03_ACLK]
  connect_bd_net [pin one/dout] [pin rst_shared/dcm_locked]
  connect_bd_net [pin ps7_0/FCLK_RESET0_N] [pin rst_shared/ext_reset_in]
  connect_bd_net [pin rst_shared/peripheral_aresetn] [pin lab07_mmio/s_axi_aresetn] [pin lab07_raw/s_axi_aresetn]
  connect_bd_net [pin rst_shared/interconnect_aresetn] [pin ps7_0_axi_periph/M02_ARESETN] [pin ps7_0_axi_periph/M03_ARESETN]
  connect_bd_intf_net [get_bd_intf_pins ps7_0_axi_periph/M02_AXI] [get_bd_intf_pins lab07_mmio/S_AXI]
  connect_bd_intf_net [get_bd_intf_pins ps7_0_axi_periph/M03_AXI] [get_bd_intf_pins lab07_raw/S_AXI]
  source $root/../lab07_scripts/export_features.tcl
  assign_bd_address -offset 0x43C00000 -range 4K -target_address_space [get_bd_addr_spaces ps7_0/Data] [get_bd_addr_segs lab07_mmio/S_AXI/Reg]
  assign_bd_address -offset 0x43C10000 -range 8K -target_address_space [get_bd_addr_spaces ps7_0/Data] [get_bd_addr_segs lab07_raw/S_AXI/Reg]
  # Independent demo: preserve official Base OUT register placement.
  foreach {seg offset} {
    system_interrupts/s_axi/Reg 0x41800000
    video/axi_vdma/S_AXI_LITE/Reg 0x43000000
    video/hdmi_out/frontend/axi_dynclk/s00_axi/reg0 0x43C30000
    video/hdmi_out/frontend/vtc_out/ctrl/Reg 0x43C20000
    video/hdmi_out/frontend/hdmi_out_hpd_video/S_AXI/Reg 0x41230000
    video/hdmi_out/color_convert/s_axi_AXILiteS/Reg 0x43C60000
    video/hdmi_out/pixel_unpack/s_axi_AXILiteS/Reg 0x43C70000
    video/hdmi_out/warm_reset/S_AXI/Reg 0x43C40000
  } {
    assign_bd_address -offset $offset -range 0x00010000 -target_address_space [get_bd_addr_spaces ps7_0/Data] [get_bd_addr_segs $seg]
  }
  assign_bd_address -offset 0x00000000 -range 0x20000000 -target_address_space [get_bd_addr_spaces video/axi_vdma/Data_MM2S] [get_bd_addr_segs ps7_0/S_AXI_HP0/HP0_DDR_LOWOCM]
  if {[llength [get_bd_cells -quiet hpd_sync]]} {error "Unexpected HPD cell in BD"}
  mark NO_MODULE_REFERENCE_HPD_PASS
  mark CREATE_BD_PASS
  validate_bd_design
  save_bd_design
  mark VALIDATE_BD_PASS
  write_bd_tcl -force [file join $reportdir actual_bd.tcl]
  set bd [get_files */base.bd]
  set_property synth_checkpoint_mode None $bd
  generate_target {synthesis simulation} $bd
  mark GENERATE_TARGET_PASS
  # The BD vendor cell has no retire observation pin. Add the matching named
  # connection only to this candidate's emitted HDL, after target generation.
  puts [exec $::env(PQ_BUILD_PYTHON) $root/../patch_generated_reset.py $projdir]

  # No hardware handoff target or HWH publication in this evaluation.
  set wrapper [make_wrapper -files $bd -top]
  add_files -norecurse $wrapper
  mark GENERATE_WRAPPER_PASS
  if {[llength $wrapper] != 1} {error "Expected exactly one generated wrapper"}
  # Top generated independently from unchanged Lab07 wiring and HDMI ports.
  mark GENERATE_CUSTOM_TOP_PASS
  source $root/../lab07_scripts/main_sources_unified2.tcl
  add_files -norecurse $root/../fft_ip/lab06_fft.xci
  add_files -norecurse $root/../fft_ip/hann_q17.hex
  generate_target all [get_ips lab06_fft]
  add_files -fileset constrs_1 -norecurse $root/xdc/lab07.xdc
  add_files -norecurse [file join $root rtl unified_top.sv]
  set_property top unified_top [current_fileset]
  set tf [open [file join $reportdir synthesis_top.txt] w]
  puts $tf [get_property TOP [current_fileset]]; close $tf
  add_files -fileset constrs_1 -norecurse [file join $root xdc hdmi_out.xdc]
  add_files -fileset constrs_1 -norecurse [file join $root xdc hdmi_external_serial_clock.xdc]
  set_property PROCESSING_ORDER LATE [get_files hdmi_external_serial_clock.xdc]
  # Replace only the generated peripheral wrapper binding. Vendor core/deps
  # are untouched. The own wrapper has the same external port/address contract.
  set old_wrapper [get_files -all -quiet *base_axi_vdma_0.vhd]
  if {[llength $old_wrapper] != 2} {error "Expected exactly one generated VDMA wrapper: $old_wrapper"}
  set_property USED_IN_SYNTHESIS false $old_wrapper
  set_property USED_IN_SIMULATION false $old_wrapper
  set_property SOURCE_MGMT_MODE None [current_project]
  add_files -norecurse [file join $root rtl vdma_axil_snapshot_bridge.sv]
  add_files -norecurse [file join $root rtl base_axi_vdma_0.sv]
  add_files -norecurse [file join $root rtl vdma_mm2s_r_slice.sv]
  set_property SOURCE_MGMT_MODE None [current_project]
  set own [get_files -all [list */rtl/vdma_axil_snapshot_bridge.sv */rtl/vdma_mm2s_r_slice.sv */rtl/base_axi_vdma_0.sv]]
  if {[llength $own]!=3} {error "Missing own RTL files"}
  set_property USED_IN_SYNTHESIS true $own
  foreach name {frame_retire_fence.sv frame_retire_registers.sv} {
    add_files -norecurse [file join $root rtl $name]
  }
  set original_reader [get_files -all -quiet *ipshared*/hdl/axi_vdma_v6_3_rfs.vhd]
  if {[llength $original_reader]!=1} {error "Expected one vendor VDMA source: $original_reader"}
  set_property USED_IN_SYNTHESIS false $original_reader
  set_property USED_IN_SIMULATION false $original_reader
  set candidate_reader [file join $root vendor_vdma axi_vdma_v6_3_rfs.vhd]
  add_files -norecurse $candidate_reader
  set_property LIBRARY axi_vdma_v6_3_5 [get_files $candidate_reader]

  reorder_files -fileset sources_1 -front $own
  set vdmaxdc [get_files -all -quiet *base_axi_vdma_0.xdc]
  set rgbxdc [get_files -all -quiet *rgb2dvi_clocks.xdc]
  if {[llength $vdmaxdc]!=1 || [llength $rgbxdc]!=1} {error "Unexpected scoped exception files"}
  foreach f [concat $vdmaxdc $rgbxdc] {
   set_property USED_IN_SYNTHESIS false $f
   set_property USED_IN_IMPLEMENTATION false $f
  }
  set xf [open [file join $reportdir vendor_exception_selection.tsv] w]
  foreach f [concat $vdmaxdc $rgbxdc] {puts $xf "$f\t[get_property USED_IN_SYNTHESIS $f]\t[get_property USED_IN_IMPLEMENTATION $f]"}
  close $xf
  report_compile_order -used_in synthesis -file [file join $reportdir compile_order.rpt]
  set_property STEPS.OPT_DESIGN.TCL.PRE [file join $root tcl unified2_constraints.tcl] [get_runs impl_1]
  set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED false [get_runs impl_1]
  mark PROJECT_CREATED
  source $root/../scripts/verify_bd.tcl
  close_project
  mark PREPARE_ONLY_COMPLETE_NO_SYNTH_NO_HANDOFF
  return

}

if {[catch {build} result options]} {
 mark BUILD_FAILED
 puts stderr [dict get $options -errorinfo]
 close $status
 exit 1
}
close $status
exit 0

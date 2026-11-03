# The untouched IP ships cdc_tig and cdc_from/to cuts for its asynchronous
# configuration. All enabled clocks of THIS MM2S-only core are now one clock.
# Restore ordinary timing on these local paths; leaving the old cuts active
# would undermine the new synchronous read-word coherency proof.
set local_capture [get_cells -quiet -hier -filter {NAME =~ *axi_vdma/U0/*cdc_tig* && is_sequential}]
if {![llength $local_capture]} {error "Expected original synchronous capture banks"}
foreach c $local_capture {
 set clock [get_clocks -quiet -of_objects [get_pins -quiet -of_objects $c -filter {REF_PIN_NAME == C}]]
 if {[llength $clock]!=1 || abs([get_property PERIOD $clock]-7.0)>0.01} {error "Local core capture not in MM2S domain: $c"}
}
reset_path -to [get_pins -quiet -of_objects $local_capture -filter {REF_PIN_NAME == D}]
set local_from [get_cells -quiet -hier -filter {NAME =~ *axi_vdma/U0/*cdc_from* && is_sequential}]
set local_to [get_cells -quiet -hier -filter {NAME =~ *axi_vdma/U0/*cdc_to* && is_sequential}]
if {[llength $local_from] && [llength $local_to]} {reset_path -from $local_from -to $local_to}
puts "BRIDGE_RESTORED_LOCAL_SYNCHRONOUS_TIMING [llength $local_capture] capture FFs"
# Bounded bundled-data crossings; no false paths, no waivers. At least two
# destination clock periods elapse after payload creation before consumption.
# 5ns is below either clock period (7ns / 10ns), including reset epoch drain.
foreach {src dst} {
  *bridge/read_address_hold_reg* *bridge/m_axi_araddr_reg*
  *bridge/write_address_hold_reg* *bridge/m_axi_awaddr_reg*
  *bridge/write_data_hold_reg* *bridge/m_axi_wdata_reg*
  *bridge/read_snapshot_reg* *bridge/s_axi_rdata_reg*
  *bridge/read_snapshot_reg* *bridge/s_axi_rresp_reg*
  *bridge/write_snapshot_reg* *bridge/s_axi_bresp_reg*
} {
 set a [get_cells -quiet -hier -filter "NAME =~ $src"]
 set b [get_cells -quiet -hier -filter "NAME =~ $dst"]
 if {![llength $b] && ([string match {*rresp*} $dst] || [string match {*bresp*} $dst])} {
   puts "BRIDGE_CONSTANT_RESP_PRUNED $dst"; continue
 }
 if {![llength $a] || ![llength $b]} {error "Missing bridge bundled endpoint: $src -> $dst"}
 set_max_delay -datapath_only 5.000 -from $a -to $b
}
# The peripheral IRQ is a latched level (status & enables), not a pulse.
set irq0 {}
foreach c [get_cells -quiet -hier -filter {NAME =~ *axi_vdma/irq_level_reg*}] {
 if {[regexp {\[0\]$} $c]} {lappend irq0 $c}
}
set irqn [get_nets -quiet -hier -filter {NAME =~ *axi_vdma/core_irq}]
if {[llength $irq0]!=1 || ![llength $irqn]} {error "IRQ synchronizer endpoints missing"}
set irqd [get_pins -quiet -leaf -of_objects [get_nets -segments -of_objects $irqn] -filter {DIRECTION == OUT}]
if {![llength $irqd]} {error "IRQ level source missing"}
set_max_delay -datapath_only 5.000 -from $irqd -to $irq0
# Control synchronizers also have bounded source-to-first-stage routing rather
# than broad false paths. Inter-stage timing remains normally constrained.
foreach {src dst} {
 *bridge/r_req_reg *bridge/r_req_sync_reg*
 *bridge/r_ack_reg *bridge/r_ack_sync_reg*
 *bridge/w_req_reg *bridge/w_req_sync_reg*
 *bridge/w_ack_reg *bridge/w_ack_sync_reg*
} {
 set a [get_cells -quiet -hier -filter "NAME =~ $src"]
 set b {}
 foreach c [get_cells -quiet -hier -filter "NAME =~ $dst"] {
   if {[regexp {\[0\]$} $c]} {lappend b $c}
 }
 if {![llength $a] || ![llength $b]} {error "Missing bridge control endpoint: $src -> $dst"}
 set_max_delay -datapath_only 5.000 -from $a -to $b
}

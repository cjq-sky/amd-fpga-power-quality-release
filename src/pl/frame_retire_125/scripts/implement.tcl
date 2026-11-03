# Reproduction wrapper derived from the approved 125 MHz synthesis/place,
# one default phys_opt, one default route and bit-generation command order.
# Historical evidence gates are not forged or imported as new-build results.
set root [file normalize [file join [file dirname [info script]] ..]]
set out [file join $root output]
set_param general.maxThreads 4

proc clocks_125 {} {
  foreach {name period} {clk_fpga_0 10.0 clk_fpga_1 8.0 clk_125mhz 8.0} {
    set c [get_clocks -quiet $name]
    if {[llength $c] != 1 || abs([get_property PERIOD $c]-$period)>0.001} {
      error "Clock mismatch: $name"
    }
  }
}
proc timing_reports {out phase point final} {
  global root
  set dir [file join $out reports $phase $point]
  file mkdir $dir
  if {$point eq "startup"} {
    source $root/candidate/xdc/hdmi_startup_clock_audit.xdc
  } else {
    source $root/candidate/xdc/hdmi_external_serial_clock.xdc
  }
  clocks_125
  report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file $dir/timing_summary.rpt
  report_clocks -file $dir/clocks.rpt
  report_clock_interaction -delay_type min_max -file $dir/clock_interaction.rpt
  report_cdc -details -file $dir/cdc.rpt
  report_drc -file $dir/drc.rpt
  report_exceptions -file $dir/exceptions.rpt
  set f [open $dir/worst_slacks.tsv w]
  puts $f "delay\tslack\tstartpoint\tendpoint"
  foreach delay {max min} {
    set p [get_timing_paths -delay_type $delay -max_paths 1 -nworst 1]
    if {[llength $p] != 1} {error "No $delay timing path"}
    set slack [get_property SLACK $p]
    puts $f "$delay\t$slack\t[get_property STARTPOINT_PIN $p]\t[get_property ENDPOINT_PIN $p]"
    if {$final && (![string is double -strict $slack] || $slack < 0)} {
      close $f
      error "Routed timing failed: $point $delay $slack; preserve results, no automatic retry"
    }
  }
  close $f
}

if {[catch {
  if {[version -short] ne "2018.2"} {error "Vivado 2018.2 required"}
  open_project $root/candidate/p/u2/lab07_lab08_unified_2.xpr
  set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED false [get_runs impl_1]
  if {[get_property STATUS [get_runs synth_1]] ne "Not started"} {error "Refuse to reuse synthesis"}
  set f [open $out/reports/actual_sources.txt w]
  foreach p [get_files -compile_order sources -used_in synthesis] {puts $f [get_property NAME $p]}
  close $f
  set f [open $out/reports/actual_constraints.tsv w]
  foreach p [get_files -all -filter {FILE_TYPE == XDC}] {
    puts $f "[get_property NAME $p]\t[get_property USED_IN_SYNTHESIS $p]\t[get_property USED_IN_IMPLEMENTATION $p]"
  }
  close $f
  launch_runs synth_1 -jobs 4
  wait_on_run synth_1
  if {![string match "*Complete*" [get_property STATUS [get_runs synth_1]]]} {error "Synthesis failed"}
  open_run synth_1
  write_checkpoint $out/checkpoints/synth_context.dcp
  report_utilization -hierarchical -file $out/reports/utilization_synth.rpt
  close_design
  launch_runs impl_1 -to_step place_design -jobs 4
  wait_on_run impl_1
  set placed $root/candidate/p/u2/lab07_lab08_unified_2.runs/impl_1/unified_top_placed.dcp
  if {![file isfile $placed]} {error "Place failed"}
  open_checkpoint $placed
  write_checkpoint $out/checkpoints/placed_context.dcp
  source $root/candidate/xdc/hdmi_startup_clock_audit.xdc
  clocks_125
  puts "REPRODUCTION_PHYS_OPT_ONCE_DEFAULT"
  phys_opt_design
  write_checkpoint $out/checkpoints/physopt_once.dcp
  # The historical report-only model switch is retained before native restore.
  timing_reports $out physopt startup 0
  timing_reports $out physopt operating 0
  source $root/candidate/xdc/hdmi_startup_clock_audit.xdc
  puts "REPRODUCTION_ROUTE_ONCE_DEFAULT"
  route_design
  write_checkpoint $out/checkpoints/routed_startup.dcp
  report_route_status -file $out/reports/route_status.rpt
  report_utilization -hierarchical -file $out/reports/utilization_routed.rpt
  report_design_analysis -congestion -file $out/reports/congestion_routed.rpt
  timing_reports $out routed startup 1
  timing_reports $out routed operating 1
  source $root/candidate/xdc/hdmi_startup_clock_audit.xdc
  foreach {name period} {axi_dynclk_0_PXL_CLK_O 10.0 I 2.0} {
    set c [get_clocks -quiet $name]
    if {[llength $c]!=1 || abs([get_property PERIOD $c]-$period)>0.001} {error "HDMI startup clock mismatch"}
  }
  set f [open $out/reports/route_status.rpt r]; set status [read $f]; close $f
  if {![regexp -nocase {nets with routing errors\.*\s*[:|]\s*0\y} $status]} {error "Route status not confirmed"}
  if {![regexp -nocase {# of routable nets\.*\s*[:|]\s*([0-9]+)} $status unused routable]
      || ![regexp -nocase {# of fully routed nets\.*\s*[:|]\s*([0-9]+)} $status unused routed]
      || $routable != $routed || $routable == 0} {
    error "Not all routable nets are fully routed"
  }
  report_drc -ruledeck bitstream_checks -file $out/reports/bitstream_checks.rpt
  set bad [get_drc_violations -quiet -filter {SEVERITY == "Error" || SEVERITY == "Critical Warning"}]
  if {[llength $bad]} {error "Bitstream DRC failed; warnings are preserved in reports"}
  write_bitstream $out/artifacts/rebuilt_frame_retire_fclk1_125.bit
  close_design
  close_project
} message options]} {
  set f [open $out/first_error.txt w]; puts $f [dict get $options -errorinfo]; close $f
  puts stderr [dict get $options -errorinfo]
  exit 1
}
exit 0

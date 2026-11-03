set ev $root/../reports/preparation
file mkdir $ev
set pf [open $ev/PS7_ACTUAL_CONFIG.tsv w]
foreach k {PCW_FPGA0_PERIPHERAL_FREQMHZ PCW_FPGA1_PERIPHERAL_FREQMHZ PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ PCW_ACT_FPGA1_PERIPHERAL_FREQMHZ PCW_FCLK0_PERIPHERAL_CLKSRC PCW_FCLK1_PERIPHERAL_CLKSRC PCW_FCLK0_PERIPHERAL_DIVISOR0 PCW_FCLK0_PERIPHERAL_DIVISOR1 PCW_FCLK1_PERIPHERAL_DIVISOR0 PCW_FCLK1_PERIPHERAL_DIVISOR1 PCW_S_AXI_HP0_FREQMHZ PCW_S_AXI_HP0_DATA_WIDTH} {puts $pf "$k\t[get_property CONFIG.$k [get_bd_cells /ps7_0]]"}
close $pf
set hz [expr {[get_property CONFIG.PCW_ACT_FPGA1_PERIPHERAL_FREQMHZ [get_bd_cells /ps7_0]]*1e6}]
if {abs($hz-125000000)>100} {error "Actual PS7 FCLK1 not 125MHz: $hz"}
if {abs([get_property CONFIG.PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ [get_bd_cells /ps7_0]]-100)>0.001} {error "FCLK0 changed"}
set f [open $ev/BD_CONNECTIONS_AND_CONFIG.tsv w]
foreach c [get_bd_cells -hier] {
 puts $f "CELL\t$c\t[get_property VLNV $c]"
 foreach k [list_property $c] {if {[string match CONFIG.* $k]} {puts $f "CONFIG\t$c\t$k\t[get_property $k $c]"}}
}
foreach p [get_bd_pins -hier] {
 set n [get_bd_nets -quiet -of_objects $p]
 puts $f "PIN\t$p\t[get_property DIR $p]\t$n"
 foreach k {CONFIG.FREQ_HZ CONFIG.ASSOCIATED_RESET CONFIG.ASSOCIATED_BUSIF} {if {[lsearch -exact [list_property $p] $k]>=0} {puts $f "PINPROP\t$p\t$k\t[get_property $k $p]"}}
}
foreach p [get_bd_intf_pins -hier] {puts $f "INTERFACE\t$p\t[get_bd_intf_nets -quiet -of_objects $p]"}
close $f
puts BD_REAL_125_CONFIG_PASS
